"""
Selfology Bot Controller - упрощенный координатор

SPRINT 1 Refactoring (Nov 2025):
Разбили монолитный selfology_controller.py (1572 строки) на модульную архитектуру.

Этот controller - только координация и композиция, без бизнес-логики.

Архитектура:
- lifecycle: Управление жизненным циклом бота
- handlers: Обработчики команд и сообщений
- middleware: Промежуточные слои
- utilities: Вспомогательные функции
"""

import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage

from selfology_bot.messages import get_message_service
from selfology_bot.database import DatabaseService, UserDAO, OnboardingDAO
from selfology_bot.services.onboarding import OnboardingOrchestrator
from services.chat_coach import ChatCoachService

from .config import (
    BOT_TOKEN,
    DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, DB_SCHEMA,
    REDIS_FSM_HOST, REDIS_FSM_PORT, REDIS_FSM_DB,
    BOT_INSTANCE_LOCK_KEY, BOT_INSTANCE_LOCK_TTL,
    DEBUG_MESSAGES
)
from .lifecycle import BotInstanceLock, BotLifecycle
from .handler_registry import HandlerRegistry

logger = logging.getLogger(__name__)


class SelfologyController:
    """
    Упрощенный контроллер Selfology бота
    
    Ответственность:
    - Композиция всех компонентов
    - Инициализация Bot и Dispatcher
    - Регистрация handlers через HandlerRegistry
    - Запуск через BotLifecycle
    
    НЕ содержит:
    - Бизнес-логику
    - Обработчики команд
    - Утилиты
    - Прямое управление lifecycle
    """

    def __init__(self):
        """
        Инициализация контроллера
        
        Создает все необходимые компоненты через композицию.
        """
        logger.info("🤖 Initializing Selfology Controller...")

        # 1. Create Bot and Dispatcher
        self.bot = Bot(token=BOT_TOKEN)
        
        # Redis FSM Storage для персистентности
        redis_storage = RedisStorage.from_url(
            f"redis://{REDIS_FSM_HOST}:{REDIS_FSM_PORT}/{REDIS_FSM_DB}"
        )
        self.dp = Dispatcher(storage=redis_storage)
        logger.info(f"✅ Bot and Dispatcher created (Redis FSM: DB {REDIS_FSM_DB})")

        # 2. Create Message Service
        self.messages = get_message_service(debug_mode=DEBUG_MESSAGES)
        logger.info("✅ MessageService initialized")

        # 3. Create Instance Lock
        self.instance_lock = BotInstanceLock(
            redis_host=REDIS_FSM_HOST,
            redis_port=REDIS_FSM_PORT,
            redis_db=REDIS_FSM_DB,
            lock_key=BOT_INSTANCE_LOCK_KEY,
            lock_ttl=BOT_INSTANCE_LOCK_TTL
        )
        logger.info("✅ BotInstanceLock created")

        # 4. Prepare database config
        self.db_config = {
            "host": DB_HOST,
            "port": DB_PORT,
            "user": DB_USER,
            "password": DB_PASSWORD,
            "database": DB_NAME,
            "schema": DB_SCHEMA
        }

        # 5. Prepare Redis config
        self.redis_config = {
            "host": REDIS_FSM_HOST,
            "port": REDIS_FSM_PORT,
            "db": REDIS_FSM_DB
        }

        # 6. Create BotLifecycle (will initialize services on start)
        self.lifecycle = BotLifecycle(
            bot=self.bot,
            dispatcher=self.dp,
            instance_lock=self.instance_lock,
            db_config=self.db_config,
            redis_config=self.redis_config,
            bot_token=BOT_TOKEN
        )
        logger.info("✅ BotLifecycle created")

        # Services will be initialized by lifecycle.initialize_services()
        # We'll register handlers after services are initialized
        self.handler_registry = None

        logger.info("🎉 Selfology Controller initialized successfully")

    async def start(self):
        """
        Запуск бота
        
        Делегирует всю работу BotLifecycle, который:
        1. Проверяет instance lock
        2. Инициализирует сервисы
        3. Регистрирует handlers
        4. Запускает polling
        5. Обрабатывает graceful shutdown
        """
        logger.info("🚀 Starting Selfology Bot...")

        # Modify lifecycle to register handlers after service initialization
        original_initialize = self.lifecycle.initialize_services

        async def initialize_with_handlers():
            """Initialize services and register handlers"""
            # Initialize services
            success = await original_initialize()
            if not success:
                return False

            # Now register handlers with initialized services
            self.handler_registry = HandlerRegistry(
                dp=self.dp,
                user_dao=self.lifecycle.user_dao,
                onboarding_dao=self.lifecycle.onboarding_dao,
                orchestrator=self.lifecycle.onboarding_orchestrator,
                chat_coach=self.lifecycle.chat_coach,
                messages=self.messages
            )
            self.handler_registry.register_all()

            return True

        # Replace initialize_services with our version
        self.lifecycle.initialize_services = initialize_with_handlers

        # Start polling (lifecycle handles everything)
        await self.lifecycle.start_polling()

    async def stop(self):
        """
        Остановка бота
        
        Делегирует lifecycle.stop() который обрабатывает:
        - Остановку background tasks
        - Освобождение instance lock
        - Закрытие соединений
        """
        logger.info("🛑 Stopping Selfology Bot...")
        await self.lifecycle.stop()


async def main():
    """
    Точка входа для запуска бота
    
    Использование:
        python -m telegram_interface.controller
    """
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create and start controller
    controller = SelfologyController()
    await controller.start()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
