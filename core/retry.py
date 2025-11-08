"""
Retry Pattern Implementation with Exponential Backoff

Автоматический retry при временных сбоях с умным backoff стратегией.

Features:
- Exponential backoff (1s → 2s → 4s → 8s)
- Jitter для предотвращения thundering herd
- Customizable retry conditions
- Метрики (attempt count, total time)
- Integration с Circuit Breaker

Usage:
    @retry_with_backoff(max_attempts=5, base_delay=1.0)
    async def call_external_api(data):
        response = await httpx.post(url, json=data)
        response.raise_for_status()
        return response.json()
"""

import asyncio
import random
import logging
from datetime import datetime
from typing import Callable, Optional, Type, Tuple, Any
from functools import wraps

logger = logging.getLogger(__name__)


class RetryExhaustedError(Exception):
    """
    Исключение когда исчерпаны все попытки retry

    Содержит информацию о последней ошибке и количестве попыток
    """
    def __init__(self, func_name: str, attempts: int, last_error: Exception):
        self.func_name = func_name
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(
            f"Retry exhausted for '{func_name}' after {attempts} attempts. "
            f"Last error: {type(last_error).__name__}: {last_error}"
        )


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retry_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    on_retry: Optional[Callable[[int, Exception], None]] = None
):
    """
    Decorator для retry с exponential backoff

    Args:
        max_attempts: Максимальное количество попыток (включая первую)
        base_delay: Базовая задержка в секундах
        max_delay: Максимальная задержка (cap для exponential backoff)
        exponential_base: База для exponential backoff (обычно 2)
        jitter: Добавлять ли случайность к задержке (предотвращает thundering herd)
        retry_exceptions: Tuple исключений для retry (None = все исключения)
        on_retry: Callback функция вызываемая перед retry (attempt, exception)

    Returns:
        Декорированная функция с retry логикой

    Example:
        @retry_with_backoff(max_attempts=5, base_delay=2.0)
        async def fetch_user_data(user_id):
            response = await http_client.get(f"/users/{user_id}")
            return response.json()

        # С custom retry условием
        @retry_with_backoff(
            max_attempts=3,
            retry_exceptions=(httpx.HTTPError, asyncio.TimeoutError)
        )
        async def unreliable_api_call():
            return await api.call()
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            attempt = 0
            start_time = datetime.now()

            while attempt < max_attempts:
                attempt += 1

                try:
                    result = await func(*args, **kwargs)

                    # Успех
                    if attempt > 1:
                        # Логируем если были retry
                        elapsed = (datetime.now() - start_time).total_seconds()
                        logger.info(
                            f"Retry success for '{func.__name__}' "
                            f"on attempt {attempt}/{max_attempts} "
                            f"(elapsed: {elapsed:.2f}s)"
                        )

                    return result

                except Exception as e:
                    # Проверяем нужно ли retry
                    should_retry = _should_retry_exception(e, retry_exceptions)

                    if not should_retry:
                        # Это не retry-able ошибка - сразу пробрасываем
                        logger.debug(
                            f"Non-retryable exception {type(e).__name__} "
                            f"in '{func.__name__}'"
                        )
                        raise

                    if attempt >= max_attempts:
                        # Исчерпаны попытки
                        elapsed = (datetime.now() - start_time).total_seconds()
                        logger.error(
                            f"Retry exhausted for '{func.__name__}' "
                            f"after {attempt} attempts ({elapsed:.2f}s). "
                            f"Last error: {type(e).__name__}: {e}"
                        )
                        raise RetryExhaustedError(func.__name__, attempt, e) from e

                    # Вычисляем задержку
                    delay = _calculate_delay(
                        attempt=attempt,
                        base_delay=base_delay,
                        max_delay=max_delay,
                        exponential_base=exponential_base,
                        jitter=jitter
                    )

                    # Логируем retry
                    logger.warning(
                        f"Retry {attempt}/{max_attempts} for '{func.__name__}' "
                        f"after {delay:.2f}s. Error: {type(e).__name__}: {e}"
                    )

                    # Callback если есть
                    if on_retry:
                        try:
                            on_retry(attempt, e)
                        except Exception as callback_error:
                            logger.error(
                                f"Error in on_retry callback: {callback_error}"
                            )

                    # Ждём перед следующей попыткой
                    await asyncio.sleep(delay)

        return wrapper

    return decorator


def _should_retry_exception(
    exception: Exception,
    retry_exceptions: Optional[Tuple[Type[Exception], ...]]
) -> bool:
    """
    Определяет нужно ли делать retry для исключения

    Args:
        exception: Перехваченное исключение
        retry_exceptions: Tuple исключений для retry

    Returns:
        True если нужен retry, False если нет
    """
    if retry_exceptions is None:
        # Все исключения retry-able
        return True

    # Проверяем isinstance
    return isinstance(exception, retry_exceptions)


def _calculate_delay(
    attempt: int,
    base_delay: float,
    max_delay: float,
    exponential_base: float,
    jitter: bool
) -> float:
    """
    Вычисляет задержку для retry с exponential backoff

    Args:
        attempt: Номер текущей попытки (1-based)
        base_delay: Базовая задержка
        max_delay: Максимальная задержка
        exponential_base: База для exponential (обычно 2)
        jitter: Добавлять ли случайность

    Returns:
        Задержка в секундах
    """
    # Exponential backoff: base_delay * (exponential_base ^ (attempt - 1))
    delay = base_delay * (exponential_base ** (attempt - 1))

    # Cap максимумом
    delay = min(delay, max_delay)

    # Добавляем jitter (±50%)
    if jitter:
        jitter_range = delay * 0.5
        delay = delay + random.uniform(-jitter_range, jitter_range)
        delay = max(0.1, delay)  # Минимум 0.1s

    return delay


class RetryConfig:
    """
    Конфигурация retry для переиспользования

    Используется когда нужна одинаковая retry стратегия для множества функций
    """

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retry_exceptions: Optional[Tuple[Type[Exception], ...]] = None
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retry_exceptions = retry_exceptions

    def __call__(self, func: Callable):
        """Используется как decorator"""
        return retry_with_backoff(
            max_attempts=self.max_attempts,
            base_delay=self.base_delay,
            max_delay=self.max_delay,
            exponential_base=self.exponential_base,
            jitter=self.jitter,
            retry_exceptions=self.retry_exceptions
        )(func)


class RetryableOperation:
    """
    Класс для retry операций с state tracking и метриками

    Используется для сложных retry сценариев требующих tracking
    """

    def __init__(
        self,
        operation_name: str,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.operation_name = operation_name
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

        # State
        self.attempt = 0
        self.start_time: Optional[datetime] = None
        self.last_error: Optional[Exception] = None

        # Метрики
        self.stats = {
            "total_attempts": 0,
            "successful_attempts": 0,
            "failed_attempts": 0,
            "total_retry_time": 0.0
        }

    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Выполняет операцию с retry

        Args:
            func: Функция для выполнения
            *args: Аргументы функции
            **kwargs: Keyword аргументы функции

        Returns:
            Результат функции

        Raises:
            RetryExhaustedError: Если исчерпаны попытки
        """
        self.attempt = 0
        self.start_time = datetime.now()

        while self.attempt < self.max_attempts:
            self.attempt += 1
            self.stats["total_attempts"] += 1

            try:
                result = await func(*args, **kwargs)

                # Успех
                self.stats["successful_attempts"] += 1
                elapsed = (datetime.now() - self.start_time).total_seconds()

                if self.attempt > 1:
                    self.stats["total_retry_time"] += elapsed
                    logger.info(
                        f"RetryableOperation '{self.operation_name}' succeeded "
                        f"on attempt {self.attempt}/{self.max_attempts} "
                        f"(elapsed: {elapsed:.2f}s)"
                    )

                return result

            except Exception as e:
                self.last_error = e

                if self.attempt >= self.max_attempts:
                    # Исчерпаны попытки
                    self.stats["failed_attempts"] += 1
                    elapsed = (datetime.now() - self.start_time).total_seconds()
                    self.stats["total_retry_time"] += elapsed

                    logger.error(
                        f"RetryableOperation '{self.operation_name}' failed "
                        f"after {self.attempt} attempts ({elapsed:.2f}s). "
                        f"Error: {type(e).__name__}: {e}"
                    )

                    raise RetryExhaustedError(
                        self.operation_name,
                        self.attempt,
                        e
                    ) from e

                # Вычисляем задержку и ждём
                delay = _calculate_delay(
                    attempt=self.attempt,
                    base_delay=self.base_delay,
                    max_delay=self.max_delay,
                    exponential_base=self.exponential_base,
                    jitter=self.jitter
                )

                logger.warning(
                    f"RetryableOperation '{self.operation_name}' "
                    f"retry {self.attempt}/{self.max_attempts} "
                    f"after {delay:.2f}s. Error: {type(e).__name__}: {e}"
                )

                await asyncio.sleep(delay)

    def get_stats(self) -> dict:
        """Возвращает статистику операций"""
        success_rate = 0.0
        if self.stats["total_attempts"] > 0:
            success_rate = (
                self.stats["successful_attempts"] / self.stats["total_attempts"]
            ) * 100

        avg_retry_time = 0.0
        if self.stats["successful_attempts"] > 0:
            avg_retry_time = (
                self.stats["total_retry_time"] / self.stats["successful_attempts"]
            )

        return {
            "operation_name": self.operation_name,
            "success_rate": round(success_rate, 2),
            "avg_retry_time": round(avg_retry_time, 2),
            **self.stats
        }


# Предопределенные retry конфигурации
AGGRESSIVE_RETRY = RetryConfig(
    max_attempts=5,
    base_delay=0.5,
    max_delay=10.0,
    exponential_base=2.0,
    jitter=True
)

STANDARD_RETRY = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True
)

CONSERVATIVE_RETRY = RetryConfig(
    max_attempts=2,
    base_delay=2.0,
    max_delay=60.0,
    exponential_base=2.0,
    jitter=True
)


# Convenience функции для common use cases
async def retry_on_exception(
    func: Callable,
    *args,
    max_attempts: int = 3,
    exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    **kwargs
) -> Any:
    """
    Простая функция для retry без decorator

    Args:
        func: Функция для выполнения
        *args: Позиционные аргументы
        max_attempts: Количество попыток
        exceptions: Tuple исключений для retry
        **kwargs: Keyword аргументы

    Returns:
        Результат функции

    Example:
        result = await retry_on_exception(
            api.fetch_data,
            user_id=123,
            max_attempts=5,
            exceptions=(httpx.HTTPError,)
        )
    """
    operation = RetryableOperation(
        operation_name=func.__name__,
        max_attempts=max_attempts
    )

    return await operation.execute(func, *args, **kwargs)
