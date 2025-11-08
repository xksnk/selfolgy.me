"""
Circuit Breaker Pattern Implementation

Защищает систему от каскадных отказов при падении внешних сервисов.

Паттерн Circuit Breaker работает как электрический предохранитель:
- CLOSED (нормальная работа) - запросы проходят
- OPEN (сервис недоступен) - запросы блокируются немедленно
- HALF_OPEN (тестирование) - разрешен один пробный запрос

Состояния:
    CLOSED → (failures >= threshold) → OPEN
    OPEN → (timeout expired) → HALF_OPEN
    HALF_OPEN → (success) → CLOSED
    HALF_OPEN → (failure) → OPEN

Usage:
    breaker = CircuitBreaker(
        name="openai_api",
        failure_threshold=5,
        timeout=60,
        expected_exceptions=(httpx.HTTPError,)
    )

    async with breaker:
        result = await call_openai_api(prompt)
"""

import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Callable, Any, Type, Tuple
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Состояния Circuit Breaker"""
    CLOSED = "closed"        # Нормальная работа - запросы проходят
    OPEN = "open"            # Сервис недоступен - запросы блокируются
    HALF_OPEN = "half_open"  # Тестирование - разрешен пробный запрос


class CircuitBreakerOpenError(Exception):
    """
    Исключение при попытке вызова через открытый Circuit Breaker

    Выбрасывается когда Circuit в состоянии OPEN и не истек timeout
    """
    def __init__(self, circuit_name: str, retry_after: float):
        self.circuit_name = circuit_name
        self.retry_after = retry_after
        super().__init__(
            f"Circuit breaker '{circuit_name}' is OPEN. "
            f"Retry after {retry_after:.1f} seconds"
        )


class CircuitBreaker:
    """
    Circuit Breaker для защиты от каскадных отказов

    Features:
    - Автоматическое открытие при превышении порога ошибок
    - Exponential backoff для timeout
    - Метрики (failure rate, call count)
    - Graceful recovery через HALF_OPEN состояние
    - Customizable failure detection
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        expected_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
        success_threshold: int = 1,
        timeout_multiplier: float = 2.0,
        max_timeout: float = 300.0
    ):
        """
        Args:
            name: Имя Circuit Breaker (для логирования и мониторинга)
            failure_threshold: Количество ошибок подряд для открытия
            timeout: Время в секундах до перехода в HALF_OPEN
            expected_exceptions: Tuple исключений которые считаются failure
                                 (если None - все исключения)
            success_threshold: Количество успешных вызовов для закрытия в HALF_OPEN
            timeout_multiplier: Множитель для увеличения timeout
            max_timeout: Максимальный timeout (cap для exponential backoff)
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.base_timeout = timeout
        self.current_timeout = timeout
        self.expected_exceptions = expected_exceptions
        self.success_threshold = success_threshold
        self.timeout_multiplier = timeout_multiplier
        self.max_timeout = max_timeout

        # Состояние
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.opened_at: Optional[datetime] = None

        # Метрики
        self.stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "rejected_calls": 0,
            "state_changes": 0,
            "last_state_change": None
        }

        # Lock для thread-safety при изменении состояния
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def __call__(self):
        """
        Context manager для использования Circuit Breaker

        Usage:
            async with circuit_breaker:
                result = await external_call()
        """
        # Проверяем можно ли выполнять запрос
        await self._before_call()

        try:
            yield self
            # Успех
            await self._on_success()

        except Exception as e:
            # Ошибка
            should_count = self._should_count_failure(e)
            await self._on_failure(e, count_failure=should_count)
            raise

    async def _before_call(self):
        """Проверка перед вызовом - можно ли выполнить запрос"""
        async with self._lock:
            self.stats["total_calls"] += 1

            if self.state == CircuitState.CLOSED:
                # Нормальная работа - пропускаем
                return

            elif self.state == CircuitState.OPEN:
                # Проверяем истек ли timeout
                if self._should_attempt_reset():
                    # Переходим в HALF_OPEN для проверки
                    await self._transition_to_half_open()
                    return
                else:
                    # Timeout не истек - блокируем запрос
                    self.stats["rejected_calls"] += 1
                    retry_after = self._get_retry_after()
                    raise CircuitBreakerOpenError(self.name, retry_after)

            elif self.state == CircuitState.HALF_OPEN:
                # В HALF_OPEN разрешаем запросы (для тестирования)
                return

    async def _on_success(self):
        """Обработка успешного вызова"""
        async with self._lock:
            self.stats["successful_calls"] += 1

            if self.state == CircuitState.CLOSED:
                # Нормальная работа - сбрасываем счетчик ошибок
                self.failure_count = 0

            elif self.state == CircuitState.HALF_OPEN:
                # В HALF_OPEN - считаем успехи
                self.success_count += 1

                if self.success_count >= self.success_threshold:
                    # Достаточно успехов - закрываем circuit
                    await self._transition_to_closed()

    async def _on_failure(self, exception: Exception, count_failure: bool = True):
        """Обработка неудачного вызова"""
        async with self._lock:
            self.stats["failed_calls"] += 1
            self.last_failure_time = datetime.now()

            if not count_failure:
                # Исключение не считается failure (например validation error)
                logger.debug(
                    f"Circuit '{self.name}': exception {type(exception).__name__} "
                    f"not counted as failure"
                )
                return

            if self.state == CircuitState.CLOSED:
                # Увеличиваем счетчик ошибок
                self.failure_count += 1

                if self.failure_count >= self.failure_threshold:
                    # Превышен порог - открываем circuit
                    await self._transition_to_open()

            elif self.state == CircuitState.HALF_OPEN:
                # В HALF_OPEN любая ошибка открывает circuit
                await self._transition_to_open()

    def _should_count_failure(self, exception: Exception) -> bool:
        """
        Определяет должно ли исключение считаться failure

        Args:
            exception: Перехваченное исключение

        Returns:
            True если это failure, False если нет
        """
        if self.expected_exceptions is None:
            # Все исключения считаются failure
            return True

        # Проверяем isinstance для всех expected_exceptions
        return isinstance(exception, self.expected_exceptions)

    def _should_attempt_reset(self) -> bool:
        """Проверяет истек ли timeout для перехода в HALF_OPEN"""
        if self.opened_at is None:
            return False

        elapsed = (datetime.now() - self.opened_at).total_seconds()
        return elapsed >= self.current_timeout

    def _get_retry_after(self) -> float:
        """Возвращает сколько секунд осталось до retry"""
        if self.opened_at is None:
            return 0.0

        elapsed = (datetime.now() - self.opened_at).total_seconds()
        remaining = self.current_timeout - elapsed
        return max(0.0, remaining)

    async def _transition_to_closed(self):
        """Переход в CLOSED (нормальная работа)"""
        logger.info(f"Circuit '{self.name}' transition: {self.state.value} → CLOSED")

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.opened_at = None
        self.current_timeout = self.base_timeout  # Сбрасываем timeout

        self._record_state_change()

    async def _transition_to_open(self):
        """Переход в OPEN (блокировка запросов)"""
        logger.error(
            f"Circuit '{self.name}' transition: {self.state.value} → OPEN "
            f"(failures={self.failure_count}, timeout={self.current_timeout}s)"
        )

        self.state = CircuitState.OPEN
        self.opened_at = datetime.now()
        self.failure_count = 0
        self.success_count = 0

        # Exponential backoff для timeout
        self.current_timeout = min(
            self.current_timeout * self.timeout_multiplier,
            self.max_timeout
        )

        self._record_state_change()

    async def _transition_to_half_open(self):
        """Переход в HALF_OPEN (тестирование восстановления)"""
        logger.info(
            f"Circuit '{self.name}' transition: {self.state.value} → HALF_OPEN "
            f"(testing recovery)"
        )

        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        self.failure_count = 0

        self._record_state_change()

    def _record_state_change(self):
        """Записывает метрику изменения состояния"""
        self.stats["state_changes"] += 1
        self.stats["last_state_change"] = datetime.now().isoformat()

    def get_state(self) -> CircuitState:
        """Возвращает текущее состояние"""
        return self.state

    def get_stats(self) -> dict:
        """Возвращает статистику Circuit Breaker"""
        failure_rate = 0.0
        if self.stats["total_calls"] > 0:
            failure_rate = (
                self.stats["failed_calls"] / self.stats["total_calls"]
            ) * 100

        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "current_timeout": self.current_timeout,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            "failure_rate": round(failure_rate, 2),
            **self.stats
        }

    async def reset(self):
        """
        Принудительный reset Circuit Breaker

        Используется для ручного восстановления или в тестах
        """
        async with self._lock:
            logger.warning(f"Circuit '{self.name}' manual reset")
            await self._transition_to_closed()


class CircuitBreakerRegistry:
    """
    Реестр всех Circuit Breakers в системе

    Используется для централизованного мониторинга и управления
    """

    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}

    def register(self, breaker: CircuitBreaker):
        """Регистрирует Circuit Breaker"""
        self._breakers[breaker.name] = breaker
        logger.debug(f"Circuit breaker '{breaker.name}' registered")

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Получает Circuit Breaker по имени"""
        return self._breakers.get(name)

    def get_all_stats(self) -> dict[str, dict]:
        """Возвращает статистику всех Circuit Breakers"""
        return {
            name: breaker.get_stats()
            for name, breaker in self._breakers.items()
        }

    def get_open_circuits(self) -> list[str]:
        """Возвращает список открытых Circuit Breakers"""
        return [
            name
            for name, breaker in self._breakers.items()
            if breaker.get_state() == CircuitState.OPEN
        ]

    async def reset_all(self):
        """Принудительный reset всех Circuit Breakers"""
        for breaker in self._breakers.values():
            await breaker.reset()


# Singleton instance для глобального реестра
_registry: Optional[CircuitBreakerRegistry] = None


def get_circuit_breaker_registry() -> CircuitBreakerRegistry:
    """Возвращает singleton instance реестра"""
    global _registry
    if _registry is None:
        _registry = CircuitBreakerRegistry()
    return _registry


def create_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    timeout: float = 60.0,
    **kwargs
) -> CircuitBreaker:
    """
    Фабричная функция для создания и регистрации Circuit Breaker

    Args:
        name: Имя Circuit Breaker
        failure_threshold: Порог ошибок
        timeout: Timeout в секундах
        **kwargs: Дополнительные параметры CircuitBreaker

    Returns:
        Созданный и зарегистрированный Circuit Breaker
    """
    breaker = CircuitBreaker(
        name=name,
        failure_threshold=failure_threshold,
        timeout=timeout,
        **kwargs
    )

    registry = get_circuit_breaker_registry()
    registry.register(breaker)

    return breaker
