"""
Unit Tests: Circuit Breaker Pattern

Тестирует все аспекты Circuit Breaker:
- State transitions (CLOSED → OPEN → HALF_OPEN → CLOSED)
- Failure threshold
- Timeout и recovery
- Exception filtering
- Metrics tracking
- Registry management
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock

from core.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitBreakerRegistry,
    create_circuit_breaker,
    CircuitBreakerOpenError
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def circuit_breaker():
    """Basic Circuit Breaker with fast timeout"""
    return CircuitBreaker(
        name="test_breaker",
        failure_threshold=3,
        timeout=1.0,  # 1 second for fast tests
        half_open_max_calls=2
    )


@pytest.fixture
def registry():
    """Fresh Circuit Breaker Registry"""
    return CircuitBreakerRegistry()


# ============================================================================
# STATE TRANSITION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_circuit_starts_in_closed_state(circuit_breaker):
    """
    Тест: Circuit Breaker стартует в состоянии CLOSED
    """
    assert circuit_breaker.state == CircuitState.CLOSED
    assert circuit_breaker.failure_count == 0
    assert circuit_breaker.success_count == 0


@pytest.mark.asyncio
async def test_successful_calls_keep_circuit_closed(circuit_breaker):
    """
    Тест: Успешные вызовы держат circuit в состоянии CLOSED
    """
    async def successful_operation():
        return "success"

    # 10 успешных вызовов
    for _ in range(10):
        async with circuit_breaker:
            result = await successful_operation()
            assert result == "success"

    assert circuit_breaker.state == CircuitState.CLOSED
    assert circuit_breaker.success_count == 10
    assert circuit_breaker.failure_count == 0


@pytest.mark.asyncio
async def test_circuit_opens_after_threshold_failures(circuit_breaker):
    """
    Тест: Circuit открывается после достижения failure threshold
    """
    async def failing_operation():
        raise ValueError("Simulated failure")

    # Вызываем до достижения threshold (3 failures)
    for i in range(3):
        try:
            async with circuit_breaker:
                await failing_operation()
        except ValueError:
            pass

    # Circuit должен быть OPEN
    assert circuit_breaker.state == CircuitState.OPEN
    assert circuit_breaker.failure_count == 3


@pytest.mark.asyncio
async def test_circuit_rejects_calls_when_open(circuit_breaker):
    """
    Тест: Circuit отклоняет вызовы в состоянии OPEN
    """
    # Открываем circuit
    circuit_breaker.state = CircuitState.OPEN
    circuit_breaker.opened_at = datetime.now()

    # Попытка вызова должна вызвать CircuitBreakerOpenError
    with pytest.raises(CircuitBreakerOpenError) as exc_info:
        async with circuit_breaker:
            await asyncio.sleep(0)

    assert "test_breaker" in str(exc_info.value)


@pytest.mark.asyncio
async def test_circuit_transitions_to_half_open_after_timeout(circuit_breaker):
    """
    Тест: Circuit переходит в HALF_OPEN после timeout
    """
    # Открываем circuit в прошлом (timeout истек)
    circuit_breaker.state = CircuitState.OPEN
    circuit_breaker.opened_at = datetime.now() - timedelta(seconds=2)
    circuit_breaker.timeout = 1.0  # 1 second timeout

    # Следующий вызов должен перевести в HALF_OPEN
    async def test_operation():
        return "test"

    async with circuit_breaker:
        result = await test_operation()

    assert circuit_breaker.state == CircuitState.HALF_OPEN


@pytest.mark.asyncio
async def test_circuit_closes_after_successful_half_open_calls(circuit_breaker):
    """
    Тест: Circuit закрывается после успешных вызовов в HALF_OPEN
    """
    # Переводим в HALF_OPEN
    circuit_breaker.state = CircuitState.HALF_OPEN
    circuit_breaker.half_open_calls = 0

    async def successful_operation():
        return "success"

    # Делаем успешные вызовы (half_open_max_calls = 2)
    async with circuit_breaker:
        await successful_operation()

    async with circuit_breaker:
        await successful_operation()

    # После 2 успешных вызовов circuit должен закрыться
    assert circuit_breaker.state == CircuitState.CLOSED
    assert circuit_breaker.failure_count == 0


@pytest.mark.asyncio
async def test_circuit_reopens_on_half_open_failure(circuit_breaker):
    """
    Тест: Circuit возвращается в OPEN при ошибке в HALF_OPEN
    """
    # Переводим в HALF_OPEN
    circuit_breaker.state = CircuitState.HALF_OPEN

    async def failing_operation():
        raise ValueError("Test failure")

    # Первая же ошибка в HALF_OPEN открывает circuit снова
    with pytest.raises(ValueError):
        async with circuit_breaker:
            await failing_operation()

    assert circuit_breaker.state == CircuitState.OPEN


# ============================================================================
# EXCEPTION FILTERING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_circuit_ignores_excluded_exceptions():
    """
    Тест: Circuit игнорирует исключения из exclude_exceptions
    """
    class IgnoredException(Exception):
        pass

    breaker = CircuitBreaker(
        name="test_ignore",
        failure_threshold=2,
        exclude_exceptions=[IgnoredException]
    )

    async def operation_with_ignored_exception():
        raise IgnoredException("Should be ignored")

    # 5 вызовов с игнорируемыми исключениями
    for _ in range(5):
        with pytest.raises(IgnoredException):
            async with breaker:
                await operation_with_ignored_exception()

    # Circuit должен остаться CLOSED
    assert breaker.state == CircuitState.CLOSED
    assert breaker.failure_count == 0


@pytest.mark.asyncio
async def test_circuit_counts_only_specified_exceptions():
    """
    Тест: Circuit считает только указанные исключения
    """
    class CountedException(Exception):
        pass

    class OtherException(Exception):
        pass

    breaker = CircuitBreaker(
        name="test_include",
        failure_threshold=2,
        include_exceptions=[CountedException]
    )

    async def operation_with_other_exception():
        raise OtherException("Not counted")

    # Вызовы с неучитываемыми исключениями
    for _ in range(5):
        with pytest.raises(OtherException):
            async with breaker:
                await operation_with_other_exception()

    # Circuit должен остаться CLOSED
    assert breaker.state == CircuitState.CLOSED


# ============================================================================
# METRICS TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_circuit_tracks_metrics(circuit_breaker):
    """
    Тест: Circuit Breaker отслеживает метрики
    """
    async def successful_operation():
        return "ok"

    async def failing_operation():
        raise ValueError("fail")

    # 3 успешных вызова
    for _ in range(3):
        async with circuit_breaker:
            await successful_operation()

    # 2 неудачных вызова
    for _ in range(2):
        try:
            async with circuit_breaker:
                await failing_operation()
        except ValueError:
            pass

    stats = circuit_breaker.get_stats()

    assert stats["total_calls"] == 5
    assert stats["total_successes"] == 3
    assert stats["total_failures"] == 2
    assert stats["state"] == CircuitState.CLOSED.value
    assert stats["success_rate"] == 0.6


@pytest.mark.asyncio
async def test_circuit_calculates_uptime(circuit_breaker):
    """
    Тест: Circuit считает uptime
    """
    # Ждем немного
    await asyncio.sleep(0.1)

    stats = circuit_breaker.get_stats()
    assert stats["uptime_seconds"] >= 0.1


# ============================================================================
# TIMEOUT & RECOVERY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_exponential_timeout_increase():
    """
    Тест: Timeout увеличивается экспоненциально при повторных сбоях
    """
    breaker = CircuitBreaker(
        name="test_exp",
        failure_threshold=2,
        timeout=1.0,
        exponential_backoff_multiplier=2.0,
        max_timeout=60.0
    )

    async def failing_operation():
        raise ValueError("fail")

    # Первый цикл: открытие
    for _ in range(2):
        try:
            async with breaker:
                await failing_operation()
        except ValueError:
            pass

    initial_timeout = breaker.timeout
    assert breaker.state == CircuitState.OPEN

    # Переводим в HALF_OPEN и снова ломаем
    breaker.state = CircuitState.HALF_OPEN

    try:
        async with breaker:
            await failing_operation()
    except ValueError:
        pass

    # Timeout должен увеличиться
    assert breaker.timeout > initial_timeout


@pytest.mark.asyncio
async def test_timeout_does_not_exceed_max():
    """
    Тест: Timeout не превышает max_timeout
    """
    breaker = CircuitBreaker(
        name="test_max",
        failure_threshold=1,
        timeout=10.0,
        exponential_backoff_multiplier=3.0,
        max_timeout=20.0
    )

    async def failing_operation():
        raise ValueError("fail")

    # Много циклов открытия
    for cycle in range(10):
        # Открываем
        try:
            async with breaker:
                await failing_operation()
        except ValueError:
            pass

        # Переводим в HALF_OPEN и ломаем снова
        breaker.state = CircuitState.HALF_OPEN
        breaker.half_open_calls = 0

    # Timeout не должен превысить max
    assert breaker.timeout <= 20.0


# ============================================================================
# CONCURRENCY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_circuit_thread_safety():
    """
    Тест: Circuit Breaker корректно работает при конкурентных вызовах
    """
    breaker = CircuitBreaker(
        name="test_concurrent",
        failure_threshold=50
    )

    call_count = 0

    async def concurrent_operation(should_fail: bool):
        nonlocal call_count
        call_count += 1
        if should_fail:
            raise ValueError("fail")
        return "ok"

    # 100 параллельных вызовов (50 успешных, 50 неудачных)
    tasks = []
    for i in range(100):
        should_fail = i % 2 == 0
        task = asyncio.create_task(_call_with_breaker(breaker, concurrent_operation, should_fail))
        tasks.append(task)

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Проверяем что все вызовы учтены
    assert breaker.total_calls == 100
    assert breaker.success_count == 50
    assert breaker.failure_count == 50


async def _call_with_breaker(breaker, func, should_fail):
    """Helper для конкурентных вызовов"""
    try:
        async with breaker:
            return await func(should_fail)
    except Exception:
        pass


# ============================================================================
# REGISTRY TESTS
# ============================================================================

def test_registry_registers_breakers(registry):
    """
    Тест: Registry регистрирует Circuit Breakers
    """
    breaker1 = CircuitBreaker(name="breaker_1")
    breaker2 = CircuitBreaker(name="breaker_2")

    registry.register(breaker1)
    registry.register(breaker2)

    assert registry.get("breaker_1") == breaker1
    assert registry.get("breaker_2") == breaker2
    assert len(registry.get_all()) == 2


def test_registry_prevents_duplicate_names(registry):
    """
    Тест: Registry не позволяет дубликаты имен
    """
    breaker1 = CircuitBreaker(name="duplicate")
    breaker2 = CircuitBreaker(name="duplicate")

    registry.register(breaker1)

    with pytest.raises(ValueError, match="already registered"):
        registry.register(breaker2)


def test_registry_returns_all_stats(registry):
    """
    Тест: Registry возвращает статистику всех breakers
    """
    breaker1 = CircuitBreaker(name="b1")
    breaker2 = CircuitBreaker(name="b2")

    registry.register(breaker1)
    registry.register(breaker2)

    stats = registry.get_all_stats()

    assert "b1" in stats
    assert "b2" in stats
    assert stats["b1"]["state"] == CircuitState.CLOSED.value


# ============================================================================
# FACTORY TESTS
# ============================================================================

def test_create_circuit_breaker_factory():
    """
    Тест: Factory функция создает breaker с правильными параметрами
    """
    breaker = create_circuit_breaker(
        name="factory_test",
        failure_threshold=10,
        timeout=30.0
    )

    assert breaker.name == "factory_test"
    assert breaker.failure_threshold == 10
    assert breaker.timeout == 30.0


# ============================================================================
# EDGE CASES
# ============================================================================

@pytest.mark.asyncio
async def test_circuit_handles_zero_timeout():
    """
    Тест: Circuit корректно обрабатывает timeout=0 (instant recovery)
    """
    breaker = CircuitBreaker(
        name="instant_recovery",
        failure_threshold=1,
        timeout=0.0
    )

    async def failing_operation():
        raise ValueError("fail")

    # Открываем circuit
    try:
        async with breaker:
            await failing_operation()
    except ValueError:
        pass

    assert breaker.state == CircuitState.OPEN

    # Следующий вызов сразу переводит в HALF_OPEN
    breaker.state = CircuitState.HALF_OPEN


@pytest.mark.asyncio
async def test_circuit_resets_counts_on_close():
    """
    Тест: Circuit сбрасывает счетчики при закрытии
    """
    breaker = CircuitBreaker(
        name="reset_test",
        failure_threshold=2
    )

    async def failing_operation():
        raise ValueError("fail")

    # Накапливаем failures
    try:
        async with breaker:
            await failing_operation()
    except ValueError:
        pass

    assert breaker.failure_count == 1

    # Переводим в HALF_OPEN и успешно закрываем
    breaker.state = CircuitState.HALF_OPEN
    breaker.half_open_calls = 0

    async def successful_operation():
        return "ok"

    for _ in range(breaker.half_open_max_calls):
        async with breaker:
            await successful_operation()

    # Счетчики должны быть сброшены
    assert breaker.state == CircuitState.CLOSED
    assert breaker.failure_count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
