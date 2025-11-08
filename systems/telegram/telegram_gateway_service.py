"""
Telegram Gateway Service

Чистый gateway для Telegram бота без бизнес-логики:
- Принимает команды и сообщения от пользователя
- Публикует события в Event Bus
- Отправляет ответы пользователю
- FSM state management в Redis с fallback

Architecture:
    TelegramGatewayService (BaseSystem)
    ↓
    ├── MessageHandler (routing входящих сообщений)
    ├── StateManager (FSM в Redis + fallback)
    ├── RateLimiter (защита от DoS)
    └── Event Publishers (user.message.received, command.executed)

Events consumed:
- message.send.requested (from other systems)
- keyboard.show.requested
- state.change.requested

Events published:
- user.message.received
- command.executed (для /start, /onboarding, etc.)
- user.interaction (для analytics)

NO BUSINESS LOGIC:
- Вся бизнес-логика в других микросервисах
- Gateway только routing и state management
"""

import asyncio
import asyncpg
import redis.asyncio as redis
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.redis import RedisStorage

from systems.base import BaseSystem
from core.event_bus import EventBus
from core.outbox_pattern import OutboxPublisher
from core.circuit_breaker import CircuitBreakerRegistry, CircuitBreaker

logger = logging.getLogger(__name__)


# ============================================================================
# FSM STATES
# ============================================================================

class UserStates(StatesGroup):
    """FSM состояния пользователя"""
    # Initial
    new_user = State()
    gdpr_pending = State()

    # Onboarding
    onboarding_active = State()
    waiting_for_answer = State()
    processing_answer = State()
    onboarding_paused = State()
    onboarding_complete = State()

    # Chat
    chat_active = State()
    chat_paused = State()


# ============================================================================
# RATE LIMITER
# ============================================================================

class RateLimiter:
    """
    Rate limiter для защиты от DoS атак

    Features:
    - Sliding window algorithm
    - Per-user limits
    - Configurable thresholds
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        max_requests: int = 30,
        window_seconds: int = 60
    ):
        """
        Args:
            redis_client: Redis client
            max_requests: Максимум запросов в окне
            window_seconds: Размер окна в секундах
        """
        self.redis_client = redis_client
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def is_allowed(self, user_id: int) -> bool:
        """
        Проверяет можно ли обработать запрос пользователя

        Args:
            user_id: ID пользователя

        Returns:
            True если запрос разрешен
        """
        key = f"rate_limit:user:{user_id}"
        now = datetime.now().timestamp()

        try:
            # Add current request with timestamp as score
            await self.redis_client.zadd(key, {str(now): now})

            # Remove old requests outside window
            cutoff = now - self.window_seconds
            await self.redis_client.zremrangebyscore(key, 0, cutoff)

            # Count requests in window
            count = await self.redis_client.zcard(key)

            # Set expiration
            await self.redis_client.expire(key, self.window_seconds)

            allowed = count <= self.max_requests

            if not allowed:
                logger.warning(f"Rate limit exceeded for user {user_id}: {count}/{self.max_requests}")

            return allowed

        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            # Fail open - allow request on error
            return True


# ============================================================================
# STATE MANAGER
# ============================================================================

class StateManager:
    """
    FSM state management в Redis с fallback

    Features:
    - Primary storage: Redis
    - Fallback: in-memory dict
    - Graceful degradation
    """

    def __init__(self, redis_client: redis.Redis):
        """
        Args:
            redis_client: Redis client
        """
        self.redis_client = redis_client
        self.fallback_storage = {}  # In-memory fallback

    async def get_state(self, user_id: int) -> Optional[str]:
        """
        Получает текущее состояние пользователя

        Args:
            user_id: ID пользователя

        Returns:
            Название состояния или None
        """
        key = f"fsm_state:user:{user_id}"

        try:
            state = await self.redis_client.get(key)
            if state:
                return state.decode() if isinstance(state, bytes) else state
        except Exception as e:
            logger.warning(f"Redis get state failed, using fallback: {e}")

        # Fallback to memory
        return self.fallback_storage.get(user_id)

    async def set_state(self, user_id: int, state: str, ttl: int = 86400):
        """
        Устанавливает состояние пользователя

        Args:
            user_id: ID пользователя
            state: Название состояния
            ttl: Time to live в секундах (default: 24h)
        """
        key = f"fsm_state:user:{user_id}"

        try:
            await self.redis_client.setex(key, ttl, state)
        except Exception as e:
            logger.warning(f"Redis set state failed, using fallback: {e}")

        # Always update fallback
        self.fallback_storage[user_id] = state

    async def get_data(self, user_id: int) -> Dict[str, Any]:
        """
        Получает данные FSM контекста

        Args:
            user_id: ID пользователя

        Returns:
            Словарь с данными
        """
        key = f"fsm_data:user:{user_id}"

        try:
            data = await self.redis_client.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Redis get data failed: {e}")

        return {}

    async def set_data(self, user_id: int, data: Dict[str, Any], ttl: int = 86400):
        """
        Сохраняет данные FSM контекста

        Args:
            user_id: ID пользователя
            data: Данные для сохранения
            ttl: Time to live в секундах
        """
        key = f"fsm_data:user:{user_id}"

        try:
            await self.redis_client.setex(
                key,
                ttl,
                json.dumps(data)
            )
        except Exception as e:
            logger.warning(f"Redis set data failed: {e}")


# ============================================================================
# TELEGRAM GATEWAY SERVICE
# ============================================================================

class TelegramGatewayService(BaseSystem):
    """
    Telegram Gateway Service - чистый gateway без бизнес-логики

    Features:
    - Routing входящих сообщений
    - FSM state management в Redis
    - Rate limiting
    - Event-driven communication с другими системами
    - Circuit Breaker защита
    """

    def __init__(
        self,
        event_bus: EventBus,
        db_pool: asyncpg.Pool,
        redis_client: redis.Redis,
        bot_token: str,
        admin_user_ids: Optional[List[int]] = None
    ):
        """
        Args:
            event_bus: Event Bus instance
            db_pool: PostgreSQL connection pool
            redis_client: Redis client
            bot_token: Telegram Bot API token
            admin_user_ids: List of admin user IDs
        """
        super().__init__(
            name="telegram_gateway_service",
            event_bus=event_bus
        )

        self.db_pool = db_pool
        self.redis_client = redis_client
        self.bot_token = bot_token
        self.admin_user_ids = admin_user_ids or []

        # Aiogram setup
        self.bot = Bot(token=bot_token)
        storage = RedisStorage(redis=redis_client)
        self.dp = Dispatcher(storage=storage)

        # Components
        self.state_manager = StateManager(redis_client)
        self.rate_limiter = RateLimiter(
            redis_client=redis_client,
            max_requests=30,
            window_seconds=60
        )

        # Setup Circuit Breaker for Telegram API
        breaker = CircuitBreaker(
            name="telegram_api",
            failure_threshold=5,
            timeout=60.0,
            exponential_backoff_multiplier=2.0
        )
        self.circuit_breaker_registry.register(breaker)

        # Metrics
        self.metrics = {
            "messages_received": 0,
            "commands_executed": 0,
            "messages_sent": 0,
            "rate_limited": 0,
            "errors": 0
        }

        # Register handlers
        self._register_handlers()

    def _register_handlers(self):
        """Регистрирует Telegram handlers"""

        @self.dp.message(CommandStart())
        async def handle_start(message: Message):
            """Handler для /start"""
            await self._handle_command(message, "start")

        @self.dp.message(Command("onboarding"))
        async def handle_onboarding(message: Message):
            """Handler для /onboarding"""
            await self._handle_command(message, "onboarding")

        @self.dp.message(Command("help"))
        async def handle_help(message: Message):
            """Handler для /help"""
            await self._handle_command(message, "help")

        @self.dp.message(F.text)
        async def handle_text_message(message: Message):
            """Handler для текстовых сообщений"""
            await self._handle_text_message(message)

        @self.dp.callback_query()
        async def handle_callback(callback: CallbackQuery):
            """Handler для callback кнопок"""
            await self._handle_callback(callback)

        logger.info("✅ Telegram handlers registered")

    async def start(self):
        """Запускает сервис"""
        await super().start()

        # Subscribe to events
        await self.event_bus.subscribe(
            event_type="message.send.requested",
            consumer_group="telegram_gateway",
            handler=self._handle_send_message_request
        )

        await self.event_bus.subscribe(
            event_type="state.change.requested",
            consumer_group="telegram_gateway",
            handler=self._handle_state_change_request
        )

        # Start bot polling in background
        asyncio.create_task(self._run_bot())

        logger.info(f"✅ {self.name} started")

    async def _run_bot(self):
        """Запускает Telegram bot polling"""
        try:
            logger.info("🤖 Starting Telegram bot polling...")
            await self.dp.start_polling(self.bot)
        except Exception as e:
            logger.error(f"Bot polling error: {e}", exc_info=True)

    async def _handle_command(self, message: Message, command: str):
        """
        Обрабатывает команду от пользователя

        Args:
            message: Telegram message
            command: Название команды
        """
        user_id = message.from_user.id

        # Rate limiting
        if not await self.rate_limiter.is_allowed(user_id):
            self.metrics["rate_limited"] += 1
            await message.answer("⏳ Слишком много запросов. Подождите немного.")
            return

        self.metrics["commands_executed"] += 1

        # Publish command event
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                outbox_publisher = OutboxPublisher(schema="selfology")
                await outbox_publisher.publish(
                    conn,
                    "command.executed",
                    {
                        "user_id": user_id,
                        "command": command,
                        "timestamp": datetime.now().isoformat(),
                        "chat_id": message.chat.id
                    }
                )

        logger.info(f"Command /{command} from user {user_id}")

    async def _handle_text_message(self, message: Message):
        """
        Обрабатывает текстовое сообщение от пользователя

        Args:
            message: Telegram message
        """
        user_id = message.from_user.id

        # Rate limiting
        if not await self.rate_limiter.is_allowed(user_id):
            self.metrics["rate_limited"] += 1
            return

        self.metrics["messages_received"] += 1

        # Get current state
        state = await self.state_manager.get_state(user_id)

        # Publish message event
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                outbox_publisher = OutboxPublisher(schema="selfology")
                await outbox_publisher.publish(
                    conn,
                    "user.message.received",
                    {
                        "user_id": user_id,
                        "message_text": message.text,
                        "current_state": state,
                        "timestamp": datetime.now().isoformat(),
                        "chat_id": message.chat.id
                    }
                )

        logger.info(f"Message from user {user_id} in state {state}")

    async def _handle_callback(self, callback: CallbackQuery):
        """
        Обрабатывает callback от inline кнопок

        Args:
            callback: Callback query
        """
        user_id = callback.from_user.id

        # Rate limiting
        if not await self.rate_limiter.is_allowed(user_id):
            self.metrics["rate_limited"] += 1
            await callback.answer("⏳ Слишком много запросов")
            return

        # Publish callback event
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                outbox_publisher = OutboxPublisher(schema="selfology")
                await outbox_publisher.publish(
                    conn,
                    "user.callback.received",
                    {
                        "user_id": user_id,
                        "callback_data": callback.data,
                        "timestamp": datetime.now().isoformat(),
                        "chat_id": callback.message.chat.id if callback.message else None
                    }
                )

        await callback.answer()
        logger.info(f"Callback {callback.data} from user {user_id}")

    async def _handle_send_message_request(self, event: Dict[str, Any]):
        """
        Обрабатывает запрос на отправку сообщения пользователю

        Event payload:
        {
            "user_id": int,
            "text": str,
            "keyboard": optional,
            "parse_mode": optional
        }
        """
        try:
            payload = event["payload"]
            user_id = payload["user_id"]
            text = payload["text"]
            keyboard = payload.get("keyboard")
            parse_mode = payload.get("parse_mode", "HTML")

            breaker = self.circuit_breaker_registry.get("telegram_api")

            async with breaker:
                if keyboard:
                    await self.bot.send_message(
                        chat_id=user_id,
                        text=text,
                        reply_markup=keyboard,
                        parse_mode=parse_mode
                    )
                else:
                    await self.bot.send_message(
                        chat_id=user_id,
                        text=text,
                        parse_mode=parse_mode
                    )

            self.metrics["messages_sent"] += 1
            logger.info(f"Sent message to user {user_id}")

        except Exception as e:
            logger.error(f"Failed to send message: {e}", exc_info=True)
            self.metrics["errors"] += 1
            raise

    async def _handle_state_change_request(self, event: Dict[str, Any]):
        """
        Обрабатывает запрос на изменение состояния пользователя

        Event payload:
        {
            "user_id": int,
            "new_state": str
        }
        """
        try:
            payload = event["payload"]
            user_id = payload["user_id"]
            new_state = payload["new_state"]

            await self.state_manager.set_state(user_id, new_state)

            logger.info(f"Changed state for user {user_id} to {new_state}")

        except Exception as e:
            logger.error(f"Failed to change state: {e}", exc_info=True)
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Проверяет здоровье сервиса"""
        health = await super().health_check()

        # Check Telegram API
        telegram_healthy = False
        try:
            breaker = self.circuit_breaker_registry.get("telegram_api")
            if breaker.state.value == "closed":
                telegram_healthy = True
        except Exception:
            pass

        # Check Redis
        redis_healthy = False
        try:
            await self.redis_client.ping()
            redis_healthy = True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")

        # Check DB
        db_healthy = False
        try:
            async with self.db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            db_healthy = True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")

        health.update({
            "telegram_api": "healthy" if telegram_healthy else "unhealthy",
            "redis": "healthy" if redis_healthy else "degraded",
            "database": "healthy" if db_healthy else "unhealthy",
            "metrics": self.metrics
        })

        if not telegram_healthy or not db_healthy:
            health["status"] = "unhealthy"
        elif not redis_healthy:
            health["status"] = "degraded"

        return health

    def get_metrics(self) -> Dict[str, Any]:
        """Возвращает метрики сервиса"""
        return {
            **self.metrics,
            "circuit_breakers": {
                "telegram_api": self.circuit_breaker_registry.get("telegram_api").state.value
            }
        }

    async def stop(self):
        """Останавливает сервис"""
        await super().stop()
        await self.bot.session.close()
        logger.info(f"✅ {self.name} stopped")


# ============================================================================
# FACTORY
# ============================================================================

def create_telegram_gateway_service(
    event_bus: EventBus,
    db_pool: asyncpg.Pool,
    redis_client: redis.Redis,
    bot_token: str,
    admin_user_ids: Optional[List[int]] = None
) -> TelegramGatewayService:
    """
    Factory для создания Telegram Gateway Service

    Args:
        event_bus: Event Bus instance
        db_pool: PostgreSQL connection pool
        redis_client: Redis client
        bot_token: Telegram Bot API token
        admin_user_ids: List of admin user IDs

    Returns:
        Configured TelegramGatewayService instance
    """
    return TelegramGatewayService(
        event_bus=event_bus,
        db_pool=db_pool,
        redis_client=redis_client,
        bot_token=bot_token,
        admin_user_ids=admin_user_ids
    )
