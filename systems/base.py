"""
Base System Interface for All Microservices

Определяет единый интерфейс для всех систем в event-driven архитектуре.

Каждый микросервис должен наследоваться от BaseSystem и реализовать:
- start() - запуск сервиса
- stop() - graceful shutdown
- health_check() - проверка здоровья
- get_stats() - метрики

Systems:
1. Telegram Gateway Service
2. Question Selection Service
3. Session Management Service
4. Analysis Worker Service
5. Profile Storage Service
6. Trait Evolution Service
7. Coach Interaction Service

Usage:
    class AnalysisSystem(BaseSystem):
        async def start(self):
            # Setup database, event consumers, etc.
            pass

        async def health_check(self):
            # Check dependencies
            return {"status": "healthy"}
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum

from core.event_bus import EventBus, EventConsumer
from core.circuit_breaker import CircuitBreaker, create_circuit_breaker

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Статус здоровья системы"""
    HEALTHY = "healthy"      # Все в порядке
    DEGRADED = "degraded"    # Работает с ограничениями
    UNHEALTHY = "unhealthy"  # Критические проблемы


class SystemState(str, Enum):
    """Состояние системы"""
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class BaseSystem(ABC):
    """
    Базовый интерфейс для всех микросервисов

    Обеспечивает:
    - Lifecycle management (start/stop)
    - Health checks
    - Metrics tracking
    - Event Bus integration
    - Circuit Breaker integration
    - Graceful shutdown
    """

    def __init__(
        self,
        name: str,
        event_bus: Optional[EventBus] = None
    ):
        """
        Args:
            name: Имя системы (например "analysis_system")
            event_bus: Event Bus instance (опционально)
        """
        self.name = name
        self.event_bus = event_bus
        self.state = SystemState.STOPPED
        self.started_at: Optional[datetime] = None
        self.stopped_at: Optional[datetime] = None

        # Event consumers
        self._consumers: List[EventConsumer] = []

        # Circuit breakers для внешних зависимостей
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}

        # Metrics
        self._metrics = {
            "total_events_processed": 0,
            "total_events_failed": 0,
            "total_requests": 0,
            "total_errors": 0,
            "uptime_seconds": 0.0
        }

    # ========================================================================
    # LIFECYCLE METHODS (must implement)
    # ========================================================================

    @abstractmethod
    async def start(self):
        """
        Запускает систему

        Должен выполнить:
        - Подключение к БД
        - Создание event consumers
        - Регистрация circuit breakers
        - Запуск фоновых tasks

        Example:
            async def start(self):
                # Connect to database
                await self.db_pool.connect()

                # Register circuit breaker
                self.register_circuit_breaker("openai_api", threshold=5)

                # Create event consumer
                await self.add_event_consumer(
                    event_types=["user.answer.submitted"],
                    handler=self.handle_answer
                )

                # Mark as running
                self.state = SystemState.RUNNING
        """
        pass

    @abstractmethod
    async def stop(self):
        """
        Graceful shutdown системы

        Должен выполнить:
        - Остановить event consumers
        - Завершить pending tasks
        - Закрыть соединения с БД
        - Освободить ресурсы

        Example:
            async def stop(self):
                # Stop consumers
                await self.stop_all_consumers()

                # Close database
                await self.db_pool.close()

                # Mark as stopped
                self.state = SystemState.STOPPED
        """
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Проверка здоровья системы

        Returns:
            Dictionary с результатами проверок:
            {
                "status": "healthy|degraded|unhealthy",
                "checks": {
                    "database": "healthy",
                    "redis": "degraded",
                    "external_api": "unhealthy"
                },
                "metrics": {
                    "uptime_seconds": 3600,
                    "events_processed": 1500
                }
            }

        Example:
            async def health_check(self):
                checks = {}

                # Check database
                try:
                    await self.db.fetchval("SELECT 1")
                    checks["database"] = "healthy"
                except Exception:
                    checks["database"] = "unhealthy"

                # Overall status
                if all(v == "healthy" for v in checks.values()):
                    status = HealthStatus.HEALTHY
                elif any(v == "unhealthy" for v in checks.values()):
                    status = HealthStatus.UNHEALTHY
                else:
                    status = HealthStatus.DEGRADED

                return {
                    "status": status.value,
                    "checks": checks,
                    "metrics": self.get_metrics()
                }
        """
        pass

    # ========================================================================
    # EVENT BUS INTEGRATION
    # ========================================================================

    async def add_event_consumer(
        self,
        event_types: List[str],
        handler: callable,
        consumer_name: Optional[str] = None
    ) -> EventConsumer:
        """
        Создает event consumer для обработки событий

        Args:
            event_types: Типы событий для обработки
            handler: Async функция обработки (event_type, payload)
            consumer_name: Имя consumer (default: system_name)

        Returns:
            Created EventConsumer

        Example:
            async def handle_answer(self, event_type, payload):
                user_id = payload["user_id"]
                answer = payload["answer_text"]
                await self.analyze_answer(user_id, answer)

            await self.add_event_consumer(
                event_types=["user.answer.submitted"],
                handler=self.handle_answer
            )
        """
        if not self.event_bus:
            raise RuntimeError(f"Event Bus not configured for {self.name}")

        consumer = EventConsumer(
            event_bus=self.event_bus,
            consumer_group=self.name,
            consumer_name=consumer_name or f"{self.name}_worker",
            event_types=event_types,
            handler=handler
        )

        await consumer.start()
        self._consumers.append(consumer)

        logger.info(
            f"Event consumer added to {self.name}: "
            f"{event_types} → {handler.__name__}"
        )

        return consumer

    async def stop_all_consumers(self):
        """Останавливает все event consumers"""
        for consumer in self._consumers:
            await consumer.stop()

        logger.info(f"All consumers stopped for {self.name}")

    async def publish_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        **kwargs
    ):
        """
        Публикует событие в Event Bus

        Args:
            event_type: Тип события
            payload: Данные события
            **kwargs: Дополнительные параметры (priority, trace_id)
        """
        if not self.event_bus:
            raise RuntimeError(f"Event Bus not configured for {self.name}")

        await self.event_bus.publish(event_type, payload, **kwargs)

    # ========================================================================
    # CIRCUIT BREAKER INTEGRATION
    # ========================================================================

    def register_circuit_breaker(
        self,
        name: str,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        **kwargs
    ) -> CircuitBreaker:
        """
        Регистрирует Circuit Breaker для внешней зависимости

        Args:
            name: Имя зависимости (например "openai_api")
            failure_threshold: Порог ошибок
            timeout: Timeout в секундах
            **kwargs: Дополнительные параметры CircuitBreaker

        Returns:
            Circuit Breaker instance

        Example:
            # Register
            self.openai_breaker = self.register_circuit_breaker(
                "openai_api",
                failure_threshold=3,
                timeout=30.0
            )

            # Use
            async with self.openai_breaker:
                result = await self.call_openai_api(prompt)
        """
        full_name = f"{self.name}:{name}"

        breaker = create_circuit_breaker(
            name=full_name,
            failure_threshold=failure_threshold,
            timeout=timeout,
            **kwargs
        )

        self._circuit_breakers[name] = breaker

        logger.info(f"Circuit breaker registered: {full_name}")

        return breaker

    def get_circuit_breaker(self, name: str) -> Optional[CircuitBreaker]:
        """Возвращает Circuit Breaker по имени"""
        return self._circuit_breakers.get(name)

    # ========================================================================
    # METRICS & MONITORING
    # ========================================================================

    def get_metrics(self) -> Dict[str, Any]:
        """
        Возвращает метрики системы

        Returns:
            Dictionary с метриками
        """
        # Обновляем uptime
        if self.started_at:
            self._metrics["uptime_seconds"] = (
                datetime.now() - self.started_at
            ).total_seconds()

        return {
            **self._metrics,
            "state": self.state.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
        }

    def increment_metric(self, metric_name: str, value: float = 1.0):
        """Увеличивает метрику"""
        if metric_name in self._metrics:
            self._metrics[metric_name] += value
        else:
            self._metrics[metric_name] = value

    def set_metric(self, metric_name: str, value: Any):
        """Устанавливает значение метрики"""
        self._metrics[metric_name] = value

    def get_stats(self) -> Dict[str, Any]:
        """
        Возвращает полную статистику системы

        Включает:
        - Общие метрики
        - Статистику consumers
        - Статистику circuit breakers
        """
        stats = {
            "system_name": self.name,
            "state": self.state.value,
            "metrics": self.get_metrics(),
        }

        # Consumer stats
        if self._consumers:
            stats["consumers"] = [
                consumer.get_stats()
                for consumer in self._consumers
            ]

        # Circuit breaker stats
        if self._circuit_breakers:
            stats["circuit_breakers"] = {
                name: breaker.get_stats()
                for name, breaker in self._circuit_breakers.items()
            }

        return stats

    # ========================================================================
    # LIFECYCLE HELPERS
    # ========================================================================

    async def _start_safe(self):
        """Safe wrapper для start() с error handling"""
        try:
            self.state = SystemState.STARTING
            self.started_at = datetime.now()

            await self.start()

            self.state = SystemState.RUNNING
            logger.info(f"System started: {self.name}")

        except Exception as e:
            self.state = SystemState.ERROR
            logger.error(f"Failed to start {self.name}: {e}", exc_info=True)
            raise

    async def _stop_safe(self):
        """Safe wrapper для stop() с error handling"""
        try:
            self.state = SystemState.STOPPING

            # Stop consumers first
            await self.stop_all_consumers()

            # Custom stop logic
            await self.stop()

            self.state = SystemState.STOPPED
            self.stopped_at = datetime.now()

            logger.info(f"System stopped: {self.name}")

        except Exception as e:
            self.state = SystemState.ERROR
            logger.error(f"Failed to stop {self.name}: {e}", exc_info=True)
            raise

    # ========================================================================
    # CONTEXT MANAGER SUPPORT
    # ========================================================================

    async def __aenter__(self):
        """Context manager entry"""
        await self._start_safe()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self._stop_safe()


# ============================================================================
# SYSTEM REGISTRY
# ============================================================================

class SystemRegistry:
    """
    Реестр всех систем в приложении

    Используется для:
    - Централизованного управления
    - Health checks всех систем
    - Graceful shutdown
    """

    def __init__(self):
        self._systems: Dict[str, BaseSystem] = {}

    def register(self, system: BaseSystem):
        """Регистрирует систему"""
        self._systems[system.name] = system
        logger.info(f"System registered: {system.name}")

    def get(self, name: str) -> Optional[BaseSystem]:
        """Возвращает систему по имени"""
        return self._systems.get(name)

    def get_all(self) -> List[BaseSystem]:
        """Возвращает все системы"""
        return list(self._systems.values())

    async def start_all(self):
        """Запускает все системы"""
        for system in self._systems.values():
            await system._start_safe()

    async def stop_all(self):
        """Останавливает все системы"""
        for system in self._systems.values():
            await system._stop_safe()

    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """Health check всех систем"""
        results = {}

        for name, system in self._systems.items():
            try:
                results[name] = await system.health_check()
            except Exception as e:
                results[name] = {
                    "status": HealthStatus.UNHEALTHY.value,
                    "error": str(e)
                }

        return results

    def get_stats_all(self) -> Dict[str, Dict[str, Any]]:
        """Статистика всех систем"""
        return {
            name: system.get_stats()
            for name, system in self._systems.items()
        }


# Singleton instance
_registry: Optional[SystemRegistry] = None


def get_system_registry() -> SystemRegistry:
    """Возвращает singleton instance реестра"""
    global _registry
    if _registry is None:
        _registry = SystemRegistry()
    return _registry
