"""
Bot Lifecycle Manager - управление жизненным циклом бота

Отвечает за:
- Инициализацию всех сервисов (Database, DAOs, Monitoring, Chat Coach)
- Запуск polling с graceful shutdown
- Обработку сигналов (SIGINT, SIGTERM)
- Корректное освобождение ресурсов

АРХИТЕКТУРНЫЕ УЛУЧШЕНИЯ (October 2025):
- Graceful shutdown с ожиданием background tasks
- Proper integration с OnboardingOrchestrator shutdown
- Observability для мониторинга системы
"""

import asyncio
import logging
import os
import signal
from typing import Optional

from aiogram import Bot, Dispatcher
from selfology_bot.database import DatabaseService, UserDAO, OnboardingDAO
from selfology_bot.services.onboarding import OnboardingOrchestrator
from selfology_bot.monitoring import initialize_onboarding_monitoring
from services.chat_coach import ChatCoachService

logger = logging.getLogger(__name__)


class BotLifecycle:
    """
    Управление жизненным циклом Telegram бота

    Координирует инициализацию, запуск и остановку всех компонентов системы.
    """

    def __init__(
        self,
        bot: Bot,
        dispatcher: Dispatcher,
        instance_lock,
        db_config: dict,
        redis_config: dict,
        bot_token: str
    ):
        """
        Args:
            bot: Aiogram Bot instance
            dispatcher: Aiogram Dispatcher instance
            instance_lock: BotInstanceLock для предотвращения дублей
            db_config: Конфигурация базы данных
            redis_config: Конфигурация Redis
            bot_token: Telegram bot token
        """
        self.bot = bot
        self.dp = dispatcher
        self.instance_lock = instance_lock
        self.db_config = db_config
        self.redis_config = redis_config
        self.bot_token = bot_token

        # Сервисы - инициализируются при старте
        self.db_service: Optional[DatabaseService] = None
        self.user_dao: Optional[UserDAO] = None
        self.onboarding_dao: Optional[OnboardingDAO] = None
        self.onboarding_orchestrator: Optional[OnboardingOrchestrator] = None
        self.chat_coach: Optional[ChatCoachService] = None
        self.monitoring_system = None
        self.monitoring_task: Optional[asyncio.Task] = None

        # Shutdown event для graceful shutdown
        self._shutdown_event = asyncio.Event()

    async def setup_signal_handlers(self):
        """
        Настроить обработчики сигналов для graceful shutdown
        """
        loop = asyncio.get_event_loop()

        def signal_handler(sig):
            logger.info(f"🛑 Received signal {sig}, initiating graceful shutdown...")
            self._shutdown_event.set()

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))

        logger.info("📡 Signal handlers configured (SIGINT, SIGTERM)")

    async def initialize_services(self) -> bool:
        """
        Инициализировать все сервисы бота

        Returns:
            True если инициализация успешна, False иначе
        """
        try:
            # 🗄 Инициализация базы данных
            self.db_service = DatabaseService(
                host=self.db_config["host"],
                port=self.db_config["port"],
                user=self.db_config["user"],
                password=self.db_config["password"],
                database=self.db_config["database"],
                schema=self.db_config["schema"]
            )
            db_initialized = await self.db_service.initialize()

            if not db_initialized:
                logger.error("❌ Failed to initialize database")
                return False

            logger.info(f"✅ Database connected to schema: {self.db_config['schema']}")

            # Создаем DAO объекты
            self.user_dao = UserDAO(self.db_service)
            self.onboarding_dao = OnboardingDAO(self.db_service)
            logger.info("✅ DAOs initialized")

            # Создаем таблицы онбординга
            await self.onboarding_dao.create_onboarding_tables()
            logger.info("✅ Onboarding tables created/verified")

            # Инициализируем OnboardingOrchestrator
            self.onboarding_orchestrator = OnboardingOrchestrator()
            logger.info("✅ OnboardingOrchestrator initialized")

            # 🔥 PHASE 2-3 ACTIVE! Инициализируем Chat Coach Service
            self.chat_coach = ChatCoachService(self.db_service.pool)
            logger.info("🔥 ChatCoachService ACTIVE with all 6 Phase 2-3 components!")

            # 🆕 Инициализируем Monitoring System
            monitoring_enabled = os.getenv("MONITORING_ENABLED", "true").lower() == "true"
            if monitoring_enabled:
                admin_ids_str = os.getenv("MONITORING_ADMIN_IDS", "98005572")
                admin_ids = [int(id.strip()) for id in admin_ids_str.split(",") if id.strip()]

                self.monitoring_system = await initialize_onboarding_monitoring(
                    db_config=self.db_config,
                    bot_token=self.bot_token,
                    admin_chat_ids=admin_ids,
                    enable_alerting=os.getenv("TELEGRAM_ALERTS_ENABLED", "true").lower() == "true",
                    enable_auto_retry=os.getenv("AUTO_RETRY_ENABLED", "true").lower() == "true"
                )
                logger.info("📊 Onboarding Monitoring System initialized")
            else:
                logger.info("📊 Monitoring System disabled (MONITORING_ENABLED=false)")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to initialize services: {e}", exc_info=True)
            return False

    async def start_polling(self):
        """
        Запуск бота с проверкой на дублирующие экземпляры и graceful shutdown
        """
        try:
            # 🔒 КРИТИЧНО: Проверяем что нет других экземпляров
            lock_acquired = await self.instance_lock.acquire()
            if not lock_acquired:
                logger.error("🚫 Aborting startup - another instance is running")
                return

            # 🔄 Запускаем обновление блокировки
            await self.instance_lock.start_refresh()

            # 📡 Настраиваем signal handlers для graceful shutdown
            await self.setup_signal_handlers()

            # 🚀 Инициализируем все сервисы
            services_initialized = await self.initialize_services()
            if not services_initialized:
                logger.error("❌ Failed to initialize services, aborting")
                await self.instance_lock.release()
                return

            # Выводим startup banner
            self._print_startup_banner()

            logger.info("Starting Selfology Bot polling...")

            # 🆕 Запускаем Monitoring System как background task
            if self.monitoring_system:
                self.monitoring_task = asyncio.create_task(self.monitoring_system.start())
                logger.info("📊 Monitoring System started")

            # Запускаем polling с graceful shutdown через shutdown_event
            polling_task = asyncio.create_task(self.dp.start_polling(self.bot))

            # Ждем сигнала shutdown
            await self._shutdown_event.wait()

            # Graceful shutdown
            logger.info("🛑 Initiating graceful shutdown...")
            polling_task.cancel()

            try:
                await polling_task
            except asyncio.CancelledError:
                logger.info("✅ Polling task cancelled")

        except KeyboardInterrupt:
            logger.info("Bot stopped by user (Ctrl+C)")
        except Exception as e:
            logger.error(f"Bot error: {e}", exc_info=True)
            raise
        finally:
            # Всегда освобождаем ресурсы
            await self.stop()

    async def stop(self):
        """
        Graceful остановка бота с освобождением всех ресурсов

        АРХИТЕКТУРНЫЕ УЛУЧШЕНИЯ (October 2025):
        - Ждем завершения background tasks в OnboardingOrchestrator
        - Proper shutdown sequence с таймаутами
        - Observability статистики shutdown
        """
        logger.info("🛑 Stopping bot gracefully...")

        try:
            # ✅ 1. Останавливаем OnboardingOrchestrator background tasks
            if self.onboarding_orchestrator:
                logger.info("🔬 Shutting down OnboardingOrchestrator background tasks...")
                shutdown_stats = await self.onboarding_orchestrator.shutdown(timeout=30.0)

                logger.info(
                    f"📊 Orchestrator shutdown stats: "
                    f"status={shutdown_stats['status']}, "
                    f"completed={shutdown_stats['tasks_completed']}, "
                    f"cancelled={shutdown_stats['tasks_cancelled']}, "
                    f"time={shutdown_stats['shutdown_time']:.2f}s"
                )

            # ✅ 2. Останавливаем Monitoring System
            if self.monitoring_task and not self.monitoring_task.done():
                logger.info("📊 Shutting down Monitoring System...")
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
                logger.info("✅ Monitoring System stopped")

            # 3. Освобождаем instance lock (также останавливает refresh task)
            await self.instance_lock.release()

            # 4. Закрываем Telegram bot session
            await self.bot.session.close()
            logger.info("✅ Bot session closed")

            # 5. Закрываем database service
            if self.db_service:
                await self.db_service.close()
                logger.info("✅ Database connection closed")

            logger.info("🎉 Bot stopped successfully")

        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}", exc_info=True)

    def _print_startup_banner(self):
        """Вывести красивый banner при старте бота"""
        from selfology_bot.messages import get_message_service

        messages = get_message_service(debug_mode=False)
        available_locales = messages.get_available_locales()
        available_categories = messages.get_available_categories('ru')

        print("🚀 Selfology Bot Controller")
        print("=" * 40)
        print("✅ Simple architecture")
        print("✅ MessageService integrated")
        print(f"✅ Database connected to schema: {self.db_config['schema']}")
        print(f"✅ Redis FSM Storage: {self.redis_config['host']}:{self.redis_config['port']}/{self.redis_config['db']}")
        print(f"✅ Instance lock: Active (PID: {os.getpid()})")
        print(f"✅ Available locales: {available_locales}")
        print(f"✅ Available categories: {available_categories}")
        print("🎨 Beautiful messages system active")
        print("🗄 Database operations ready")
        print("🔗 Ready for users!")
        print("=" * 40)
