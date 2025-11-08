"""
Comprehensive Onboarding Monitoring System

Интегрированная система мониторинга онбординга:
- Real-time pipeline tracking
- Telegram alerts
- Auto-retry для failed операций
- Performance metrics
- Health checks

Usage:
    from selfology_bot.monitoring import initialize_onboarding_monitoring, get_monitoring_system

    # Initialize
    monitoring = await initialize_onboarding_monitoring(
        db_config={...},
        bot_token="...",
        admin_chat_ids=[...]
    )

    # Start monitoring
    await monitoring.start()

    # Get metrics
    metrics = await monitoring.get_current_metrics()
"""

from .onboarding_monitor import (
    OnboardingPipelineMonitor,
    OnboardingMetrics,
    PipelineAlert,
    initialize_onboarding_monitor,
    get_onboarding_monitor
)

from .telegram_alerting import (
    TelegramAlerter,
    initialize_telegram_alerter,
    get_telegram_alerter
)

from .auto_retry import (
    AutoRetryManager,
    initialize_auto_retry,
    get_auto_retry_manager
)

import asyncio
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class OnboardingMonitoringSystem:
    """
    Unified monitoring system для онбординга

    Интегрирует все компоненты мониторинга в единую систему.
    """

    def __init__(
        self,
        db_config: Dict[str, Any],
        bot_token: str,
        admin_chat_ids: List[int],
        enable_alerting: bool = True,
        enable_auto_retry: bool = True
    ):
        self.db_config = db_config
        self.bot_token = bot_token
        self.admin_chat_ids = admin_chat_ids
        self.enable_alerting = enable_alerting
        self.enable_auto_retry = enable_auto_retry

        # Components
        self.pipeline_monitor: Optional[OnboardingPipelineMonitor] = None
        self.telegram_alerter: Optional[TelegramAlerter] = None
        self.auto_retry: Optional[AutoRetryManager] = None

        # State
        self.initialized = False
        self.running = False

    async def initialize(self):
        """Инициализация всех компонентов"""
        if self.initialized:
            return

        logger.info("Initializing Onboarding Monitoring System")

        # 1. Initialize pipeline monitor
        self.pipeline_monitor = initialize_onboarding_monitor(self.db_config)
        await self.pipeline_monitor.initialize()
        logger.info("✓ Pipeline monitor initialized")

        # 2. Initialize Telegram alerter
        if self.enable_alerting:
            self.telegram_alerter = initialize_telegram_alerter(
                self.bot_token,
                self.admin_chat_ids
            )
            logger.info("✓ Telegram alerter initialized")

            # Register alert callback
            async def alert_callback(alert: PipelineAlert):
                if self.telegram_alerter:
                    await self.telegram_alerter.send_alert(
                        alert.alert_type,
                        alert.severity,
                        alert.message,
                        alert.details
                    )

            self.pipeline_monitor.register_alert_callback(alert_callback)

        # 3. Initialize auto-retry
        if self.enable_auto_retry:
            self.auto_retry = initialize_auto_retry(self.db_config)
            await self.auto_retry.initialize()
            logger.info("✓ Auto-retry manager initialized")

        self.initialized = True
        logger.info("Onboarding Monitoring System initialized successfully")

    async def start(self):
        """Запустить мониторинг"""
        if not self.initialized:
            await self.initialize()

        if self.running:
            logger.warning("Monitoring system already running")
            return

        logger.info("Starting Onboarding Monitoring System")

        # Start all components
        tasks = []

        # Pipeline monitor
        if self.pipeline_monitor:
            tasks.append(asyncio.create_task(self.pipeline_monitor.start_monitoring()))

        # Auto-retry
        if self.auto_retry:
            tasks.append(asyncio.create_task(self.auto_retry.start()))

        self.running = True
        logger.info("Onboarding Monitoring System started")

        # Wait for tasks (will run until stopped)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def stop(self):
        """Остановить мониторинг"""
        if not self.running:
            return

        logger.info("Stopping Onboarding Monitoring System")

        # Stop all components
        if self.pipeline_monitor:
            await self.pipeline_monitor.stop_monitoring()

        if self.auto_retry:
            await self.auto_retry.stop()

        if self.telegram_alerter:
            await self.telegram_alerter.close()

        self.running = False
        logger.info("Onboarding Monitoring System stopped")

    async def get_current_metrics(self) -> Dict[str, Any]:
        """Получить текущие метрики"""
        if not self.pipeline_monitor:
            return {}

        metrics = await self.pipeline_monitor.collect_current_metrics()
        return metrics.to_dict()

    async def get_pipeline_status(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Получить статус pipeline"""
        if not self.pipeline_monitor:
            return {}

        return await self.pipeline_monitor.get_pipeline_status(user_id)

    async def get_recent_errors(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Получить недавние ошибки"""
        if not self.pipeline_monitor:
            return []

        return await self.pipeline_monitor.get_recent_errors(hours)

    async def get_metrics_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Получить сводку метрик"""
        if not self.pipeline_monitor:
            return {}

        return await self.pipeline_monitor.get_metrics_summary(hours)

    async def get_retry_stats(self) -> Dict[str, Any]:
        """Получить статистику ретраев"""
        if not self.auto_retry:
            return {}

        return self.auto_retry.get_stats()

    async def check_services_health(self) -> Dict[str, Any]:
        """Проверить здоровье всех сервисов"""
        if not self.pipeline_monitor:
            return {}

        return await self.pipeline_monitor.check_services_health()

    async def send_daily_summary(self):
        """Отправить ежедневную сводку"""
        if not self.telegram_alerter:
            return

        # Получаем метрики за 24 часа
        metrics = await self.get_metrics_summary(24)

        # Отправляем
        await self.telegram_alerter.send_daily_summary(metrics)


# Global monitoring system
_monitoring_system: Optional[OnboardingMonitoringSystem] = None


async def initialize_onboarding_monitoring(
    db_config: Dict[str, Any],
    bot_token: str,
    admin_chat_ids: List[int],
    enable_alerting: bool = True,
    enable_auto_retry: bool = True
) -> OnboardingMonitoringSystem:
    """
    Инициализация глобальной системы мониторинга

    Args:
        db_config: Конфигурация подключения к БД
        bot_token: Токен Telegram бота для алертов
        admin_chat_ids: ID чатов админов для алертов
        enable_alerting: Включить Telegram алерты
        enable_auto_retry: Включить автоматические ретраи

    Returns:
        Инициализированная система мониторинга
    """
    global _monitoring_system

    _monitoring_system = OnboardingMonitoringSystem(
        db_config=db_config,
        bot_token=bot_token,
        admin_chat_ids=admin_chat_ids,
        enable_alerting=enable_alerting,
        enable_auto_retry=enable_auto_retry
    )

    await _monitoring_system.initialize()

    return _monitoring_system


def get_monitoring_system() -> Optional[OnboardingMonitoringSystem]:
    """Получить глобальную систему мониторинга"""
    return _monitoring_system


__all__ = [
    # Main system
    'OnboardingMonitoringSystem',
    'initialize_onboarding_monitoring',
    'get_monitoring_system',

    # Components
    'OnboardingPipelineMonitor',
    'TelegramAlerter',
    'AutoRetryManager',

    # Data types
    'OnboardingMetrics',
    'PipelineAlert',

    # Component initializers
    'initialize_onboarding_monitor',
    'get_onboarding_monitor',
    'initialize_telegram_alerter',
    'get_telegram_alerter',
    'initialize_auto_retry',
    'get_auto_retry_manager'
]
