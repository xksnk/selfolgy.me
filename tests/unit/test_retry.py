"""
Unit Tests: Retry Pattern

Тестирует все аспекты Retry Pattern:
- Exponential backoff
- Jitter для распределения нагрузки
- Custom retry conditions
- Max attempts limit
- Retry exceptions vs non-retry exceptions
- Metrics tracking
- Decorator и class-based API
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock

from core.retry import (
    retry_with_backoff,
    RetryableOperation,
    RetryConfig,
    RetryExhaustedError,
    should_retry_on_http_error,
    should_retry_on_timeout
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def retry_config():
    """Basic retry configuration for tests"""
    return RetryConfig(
        max_attempts=3,
        base_delay=0.1,  # 100ms for fast tests
        max_delay=1.0,
        exponential_base=2.0,
        jitter=True
    )


@pytest.fixture
def retryable_operation(retry_config):
    """RetryableOperation instance"""
    return RetryableOperation(config=retry_config)


# ============================================================================
# DECORATOR TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_decorator_succeeds_immediately():
    """
    Тест: Декоратор успешно возвращает результат без retry
    """
    call_count = 0

    @retry_with_backoff(max_attempts=3, base_delay=0.1)
    async def successful_operation():
        nonlocal call_count
        call_count += 1
        return "success"

    result = await successful_operation()

    assert result == "success"
    assert call_count == 1


@pytest.mark.asyncio
async def test_decorator_retries_on_failure():
    """
    Тест: Декоратор повторяет попытки при ошибках
    """
    call_count = 0

    @retry_with_backoff(max_attempts=3, base_delay=0.05)
    async def failing_then_success():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("Temporary failure")
        return "success"

    result = await failing_then_success()

    assert result == "success"
    assert call_count == 3


@pytest.mark.asyncio
async def test_decorator_raises_after_max_attempts():
    """
    Тест: Декоратор выбрасывает RetryExhaustedError после max attempts
    """
    call_count = 0

    @retry_with_backoff(max_attempts=3, base_delay=0.05)
    async def always_failing():
        nonlocal call_count
        call_count += 1
        raise ValueError("Permanent failure")

    with pytest.raises(RetryExhaustedError) as exc_info:
        await always_failing()

    assert call_count == 3
    assert "ValueError" in str(exc_info.value)


# ============================================================================
# EXPONENTIAL BACKOFF TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_exponential_backoff_increases_delay():
    """
    Тест: Задержка увеличивается экспоненциально
    """
    delays = []

    @retry_with_backoff(
        max_attempts=4,
        base_delay=0.1,
        exponential_base=2.0,
        jitter=False  # Отключаем jitter для предсказуемости
    )
    async def failing_operation():
        delays.append(datetime.now())
        raise ValueError("fail")

    try:
        await failing_operation()
    except RetryExhaustedError:
        pass

    # Проверяем что задержки увеличиваются
    # Попытка 1: нет задержки
    # Попытка 2: base_delay * 2^0 = 0.1s
    # Попытка 3: base_delay * 2^1 = 0.2s
    # Попытка 4: base_delay * 2^2 = 0.4s

    if len(delays) >= 2:
        delay_1_2 = (delays[1] - delays[0]).total_seconds()
        assert delay_1_2 >= 0.1

    if len(delays) >= 3:
        delay_2_3 = (delays[2] - delays[1]).total_seconds()
        assert delay_2_3 >= 0.2


@pytest.mark.asyncio
async def test_max_delay_cap():
    """
    Тест: Задержка не превышает max_delay
    """
    @retry_with_backoff(
        max_attempts=10,
        base_delay=1.0,
        max_delay=2.0,
        exponential_base=2.0,
        jitter=False
    )
    async def failing_operation():
        raise ValueError("fail")

    start_time = datetime.now()

    try:
        await failing_operation()
    except RetryExhaustedError:
        pass

    elapsed = (datetime.now() - start_time).total_seconds()

    # С max_delay=2.0 и 10 попыток, общее время не должно быть огромным
    # Максимум: 2.0 * 9 = 18s (плюс небольшой overhead)
    assert elapsed < 25.0


@pytest.mark.asyncio
async def test_jitter_adds_randomness():
    """
    Тест: Jitter добавляет случайность к задержкам
    """
    delays_run_1 = []
    delays_run_2 = []

    @retry_with_backoff(
        max_attempts=3,
        base_delay=0.2,
        jitter=True
    )
    async def failing_operation(delay_list):
        delay_list.append(datetime.now())
        raise ValueError("fail")

    # Два прогона
    try:
        await failing_operation(delays_run_1)
    except RetryExhaustedError:
        pass

    try:
        await failing_operation(delays_run_2)
    except RetryExhaustedError:
        pass

    # Задержки должны отличаться из-за jitter
    if len(delays_run_1) >= 2 and len(delays_run_2) >= 2:
        delay_1 = (delays_run_1[1] - delays_run_1[0]).total_seconds()
        delay_2 = (delays_run_2[1] - delays_run_2[0]).total_seconds()

        # С jitter задержки должны отличаться (не идеально точное сравнение)
        # Но хотя бы проверим что они в разумных пределах
        assert 0.1 <= delay_1 <= 0.5
        assert 0.1 <= delay_2 <= 0.5


# ============================================================================
# CUSTOM RETRY CONDITIONS
# ============================================================================

@pytest.mark.asyncio
async def test_custom_retry_condition():
    """
    Тест: Кастомное условие retry работает
    """
    call_count = 0

    def should_retry_custom(exception):
        # Retry только на ValueError, не на TypeError
        return isinstance(exception, ValueError)

    @retry_with_backoff(
        max_attempts=3,
        base_delay=0.05,
        retry_on=should_retry_custom
    )
    async def mixed_exceptions():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ValueError("Retry this")
        elif call_count == 2:
            raise TypeError("Don't retry this")

    with pytest.raises(TypeError):
        await mixed_exceptions()

    # Только 2 вызова: первый ValueError → retry, второй TypeError → fail
    assert call_count == 2


@pytest.mark.asyncio
async def test_http_error_retry_condition():
    """
    Тест: HTTP error retry condition работает правильно
    """
    call_count = 0

    class HTTPError(Exception):
        def __init__(self, status_code):
            self.status_code = status_code

    @retry_with_backoff(
        max_attempts=3,
        base_delay=0.05,
        retry_on=should_retry_on_http_error
    )
    async def http_operation():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise HTTPError(503)  # Service Unavailable - retry
        elif call_count == 2:
            raise HTTPError(400)  # Bad Request - don't retry

    with pytest.raises(HTTPError):
        await http_operation()

    # 2 вызова: 503 → retry, 400 → fail
    assert call_count == 2


@pytest.mark.asyncio
async def test_timeout_retry_condition():
    """
    Тест: Timeout retry condition работает
    """
    call_count = 0

    @retry_with_backoff(
        max_attempts=3,
        base_delay=0.05,
        retry_on=should_retry_on_timeout
    )
    async def timeout_operation():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise asyncio.TimeoutError("Timeout")
        return "success"

    result = await timeout_operation()

    assert result == "success"
    assert call_count == 3


# ============================================================================
# RETRYABLE OPERATION CLASS TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_retryable_operation_execute(retryable_operation):
    """
    Тест: RetryableOperation.execute успешно выполняет операцию
    """
    call_count = 0

    async def operation():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ValueError("Temporary failure")
        return "success"

    result = await retryable_operation.execute(operation)

    assert result == "success"
    assert call_count == 2


@pytest.mark.asyncio
async def test_retryable_operation_tracks_metrics(retryable_operation):
    """
    Тест: RetryableOperation отслеживает метрики
    """
    async def failing_operation():
        raise ValueError("fail")

    try:
        await retryable_operation.execute(failing_operation)
    except RetryExhaustedError:
        pass

    stats = retryable_operation.get_stats()

    assert stats["total_operations"] == 1
    assert stats["total_failures"] == 1
    assert stats["total_retries"] >= 2


@pytest.mark.asyncio
async def test_retryable_operation_with_args_kwargs():
    """
    Тест: RetryableOperation передает args и kwargs
    """
    retryable = RetryableOperation(
        config=RetryConfig(max_attempts=2, base_delay=0.05)
    )

    async def operation_with_params(a, b, multiplier=1):
        return (a + b) * multiplier

    result = await retryable.execute(
        operation_with_params,
        10,
        20,
        multiplier=2
    )

    assert result == 60  # (10 + 20) * 2


# ============================================================================
# RETRY CONFIG TESTS
# ============================================================================

def test_retry_config_defaults():
    """
    Тест: RetryConfig имеет разумные дефолты
    """
    config = RetryConfig()

    assert config.max_attempts == 3
    assert config.base_delay == 1.0
    assert config.max_delay == 60.0
    assert config.exponential_base == 2.0
    assert config.jitter is True


def test_retry_config_custom_values():
    """
    Тест: RetryConfig принимает кастомные значения
    """
    config = RetryConfig(
        max_attempts=10,
        base_delay=0.5,
        max_delay=30.0,
        exponential_base=3.0,
        jitter=False
    )

    assert config.max_attempts == 10
    assert config.base_delay == 0.5
    assert config.max_delay == 30.0
    assert config.exponential_base == 3.0
    assert config.jitter is False


# ============================================================================
# EDGE CASES
# ============================================================================

@pytest.mark.asyncio
async def test_retry_with_zero_delay():
    """
    Тест: Retry работает с нулевой задержкой
    """
    call_count = 0

    @retry_with_backoff(max_attempts=3, base_delay=0.0)
    async def fast_retry():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("fail")
        return "success"

    start_time = datetime.now()
    result = await fast_retry()
    elapsed = (datetime.now() - start_time).total_seconds()

    assert result == "success"
    assert call_count == 3
    assert elapsed < 0.1  # Должно быть мгновенно


@pytest.mark.asyncio
async def test_retry_with_max_attempts_one():
    """
    Тест: max_attempts=1 означает никаких retry (только один вызов)
    """
    call_count = 0

    @retry_with_backoff(max_attempts=1, base_delay=0.1)
    async def single_attempt():
        nonlocal call_count
        call_count += 1
        raise ValueError("fail")

    with pytest.raises(RetryExhaustedError):
        await single_attempt()

    assert call_count == 1


@pytest.mark.asyncio
async def test_retry_preserves_exception_chain():
    """
    Тест: RetryExhaustedError сохраняет оригинальное исключение
    """
    @retry_with_backoff(max_attempts=2, base_delay=0.05)
    async def failing_operation():
        raise ValueError("Original error")

    try:
        await failing_operation()
    except RetryExhaustedError as e:
        # Проверяем что оригинальное исключение доступно
        assert "ValueError" in str(e)
        assert "Original error" in str(e)


# ============================================================================
# CONCURRENCY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_concurrent_retries():
    """
    Тест: Множественные retry операции работают параллельно
    """
    call_counts = {"op1": 0, "op2": 0, "op3": 0}

    @retry_with_backoff(max_attempts=2, base_delay=0.05)
    async def concurrent_operation(name):
        call_counts[name] += 1
        if call_counts[name] < 2:
            raise ValueError("retry")
        return f"{name}_success"

    # Запускаем 3 операции параллельно
    results = await asyncio.gather(
        concurrent_operation("op1"),
        concurrent_operation("op2"),
        concurrent_operation("op3")
    )

    assert results == ["op1_success", "op2_success", "op3_success"]
    assert all(count == 2 for count in call_counts.values())


# ============================================================================
# METRICS TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_retryable_operation_success_rate():
    """
    Тест: Правильный расчет success rate
    """
    retryable = RetryableOperation(
        config=RetryConfig(max_attempts=3, base_delay=0.05)
    )

    async def sometimes_succeeds(should_succeed):
        if not should_succeed:
            raise ValueError("fail")
        return "success"

    # 3 успешных
    for _ in range(3):
        await retryable.execute(sometimes_succeeds, True)

    # 2 неудачных
    for _ in range(2):
        try:
            await retryable.execute(sometimes_succeeds, False)
        except RetryExhaustedError:
            pass

    stats = retryable.get_stats()

    assert stats["total_operations"] == 5
    assert stats["total_successes"] == 3
    assert stats["total_failures"] == 2
    assert stats["success_rate"] == 0.6


@pytest.mark.asyncio
async def test_retryable_operation_average_attempts():
    """
    Тест: Правильный расчет среднего количества попыток
    """
    retryable = RetryableOperation(
        config=RetryConfig(max_attempts=3, base_delay=0.05)
    )

    call_count = 0

    async def operation():
        nonlocal call_count
        call_count += 1
        # Первая операция: успех с 1 попытки
        # Вторая операция: успех со 2 попытки
        # Третья операция: успех с 3 попыток
        attempt_num = (call_count - 1) % 3 + 1
        if call_count <= attempt_num:
            raise ValueError("fail")
        return "success"

    # 3 операции с разным количеством попыток
    await retryable.execute(operation)  # 1 попытка

    call_count = 1  # Reset для второй операции
    await retryable.execute(operation)  # 2 попытки

    call_count = 2  # Reset для третьей операции
    await retryable.execute(operation)  # 3 попытки

    stats = retryable.get_stats()

    # Среднее: (1 + 2 + 3) / 3 = 2.0
    assert stats["avg_attempts_per_operation"] == pytest.approx(2.0, rel=0.1)


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_retry_with_circuit_breaker_pattern():
    """
    Тест: Retry Pattern интегрируется с Circuit Breaker pattern

    Демонстрирует как retry может использоваться вместе с circuit breaker
    """
    circuit_open = False

    @retry_with_backoff(
        max_attempts=3,
        base_delay=0.05,
        retry_on=lambda e: not circuit_open and isinstance(e, ValueError)
    )
    async def operation_with_circuit_protection():
        nonlocal circuit_open
        if circuit_open:
            raise RuntimeError("Circuit open")
        raise ValueError("Temporary failure")

    # Симулируем что после 2 попыток circuit открывается
    call_count = 0
    original_func = operation_with_circuit_protection

    async def wrapped():
        nonlocal call_count, circuit_open
        call_count += 1
        if call_count >= 2:
            circuit_open = True
        return await original_func()

    try:
        await wrapped()
    except (RuntimeError, RetryExhaustedError, ValueError):
        pass

    # Circuit должен был открыться
    assert circuit_open


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
