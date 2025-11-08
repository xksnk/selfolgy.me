"""
Session Management Service - Microservice для управления сессиями онбординга

Управляет lifecycle сессий онбординга:
- Создание/завершение сессий
- Tracking прогресса
- State management (в БД + Redis для performance)
- Session timeout handling
- Analytics и метрики

Features:
- Event-driven architecture
- State persistence в PostgreSQL
- Cache в Redis для hot data
- Automatic timeout detection
- Comprehensive metrics

Architecture:
    user.onboarding.initiated → SessionManagementService → session.created

Events Consumed:
    - user.onboarding.initiated
    - question.selected
    - user.answer.submitted
    - session.completed

Events Published:
    - session.created
    - session.updated
    - session.timed_out
    - session.analytics.updated

Database Schema: selfology.session_management
"""

import asyncio
import asyncpg
import redis.asyncio as redis
import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum

from systems.base import BaseSystem, HealthStatus
from core.event_bus import EventBus
from core.outbox_pattern import OutboxPublisher
from core.domain_events import EventPriority

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS
# ============================================================================

class SessionStatus(str, Enum):
    """Статусы сессии"""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    TIMED_OUT = "timed_out"
    ABANDONED = "abandoned"


# ============================================================================
# SESSION MANAGER
# ============================================================================

class SessionManager:
    """
    Управление lifecycle сессий

    Features:
    - Session CRUD
    - Progress tracking
    - Timeout detection
    - Cache в Redis
    """

    def __init__(
        self,
        db_pool: asyncpg.Pool,
        redis_client: redis.Redis
    ):
        self.db_pool = db_pool
        self.redis = redis_client
        self.session_timeout_minutes = 30

    async def create_session(
        self,
        user_id: int,
        session_type: str = "onboarding"
    ) -> int:
        """
        Создает новую сессию

        Args:
            user_id: ID пользователя
            session_type: Тип сессии

        Returns:
            session_id
        """
        async with self.db_pool.acquire() as conn:
            session_id = await conn.fetchval(
                """
                INSERT INTO selfology.onboarding_sessions
                (user_id, session_type, status, started_at, last_activity_at)
                VALUES ($1, $2, $3, NOW(), NOW())
                RETURNING id
                """,
                user_id,
                session_type,
                SessionStatus.ACTIVE.value
            )

            # Cache в Redis
            await self._cache_session(session_id, {
                "user_id": user_id,
                "session_type": session_type,
                "status": SessionStatus.ACTIVE.value,
                "questions_answered": 0,
                "started_at": datetime.now().isoformat()
            })

            logger.info(f"Session created: {session_id} for user {user_id}")
            return session_id

    async def get_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает сессию (из cache или БД)

        Args:
            session_id: ID сессии

        Returns:
            Session data или None
        """
        # Try cache first
        cached = await self._get_cached_session(session_id)
        if cached:
            return cached

        # Fallback to database
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    id,
                    user_id,
                    session_type,
                    status,
                    started_at,
                    completed_at,
                    last_activity_at
                FROM selfology.onboarding_sessions
                WHERE id = $1
                """,
                session_id
            )

            if row:
                session_data = dict(row)

                # Cache it
                await self._cache_session(session_id, session_data)

                return session_data

            return None

    async def update_session_activity(
        self,
        session_id: int,
        activity_data: Dict[str, Any]
    ):
        """
        Обновляет активность сессии

        Args:
            session_id: ID сессии
            activity_data: Данные активности
        """
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE selfology.onboarding_sessions
                SET last_activity_at = NOW()
                WHERE id = $1
                """,
                session_id
            )

            # Update cache
            session = await self.get_session(session_id)
            if session:
                session["last_activity_at"] = datetime.now().isoformat()
                await self._cache_session(session_id, session)

    async def complete_session(self, session_id: int):
        """Завершает сессию"""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE selfology.onboarding_sessions
                SET status = $1, completed_at = NOW()
                WHERE id = $2
                """,
                SessionStatus.COMPLETED.value,
                session_id
            )

            # Update cache
            session = await self.get_session(session_id)
            if session:
                session["status"] = SessionStatus.COMPLETED.value
                session["completed_at"] = datetime.now().isoformat()
                await self._cache_session(session_id, session)

            logger.info(f"Session completed: {session_id}")

    async def check_timeouts(self) -> List[int]:
        """
        Проверяет и обрабатывает timeout сессий

        Returns:
            List of timed out session IDs
        """
        timeout_threshold = datetime.now() - timedelta(
            minutes=self.session_timeout_minutes
        )

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id FROM selfology.onboarding_sessions
                WHERE status = $1
                  AND last_activity_at < $2
                """,
                SessionStatus.ACTIVE.value,
                timeout_threshold
            )

            timed_out_ids = []

            for row in rows:
                session_id = row["id"]

                # Update status
                await conn.execute(
                    """
                    UPDATE selfology.onboarding_sessions
                    SET status = $1
                    WHERE id = $2
                    """,
                    SessionStatus.TIMED_OUT.value,
                    session_id
                )

                timed_out_ids.append(session_id)

                # Clear cache
                await self._clear_cache(session_id)

            if timed_out_ids:
                logger.info(f"Sessions timed out: {timed_out_ids}")

            return timed_out_ids

    async def get_session_analytics(self, session_id: int) -> Dict[str, Any]:
        """
        Возвращает аналитику по сессии

        Returns:
            {
                "total_questions": int,
                "average_answer_length": float,
                "duration_seconds": int,
                "completion_rate": float
            }
        """
        async with self.db_pool.acquire() as conn:
            # Get session info
            session = await conn.fetchrow(
                """
                SELECT * FROM selfology.onboarding_sessions
                WHERE id = $1
                """,
                session_id
            )

            if not session:
                return {}

            # Get answers count
            answers_count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM selfology.user_answers_new
                WHERE session_id = $1
                """,
                session_id
            )

            # Calculate duration
            started_at = session["started_at"]
            ended_at = session["completed_at"] or session["last_activity_at"]
            duration_seconds = (ended_at - started_at).total_seconds()

            # Completion rate (предположим 15 вопросов в полной сессии)
            completion_rate = min(answers_count / 15.0, 1.0)

            return {
                "total_questions": answers_count,
                "duration_seconds": int(duration_seconds),
                "completion_rate": completion_rate,
                "status": session["status"]
            }

    # ========================================================================
    # REDIS CACHE
    # ========================================================================

    async def _cache_session(self, session_id: int, session_data: Dict[str, Any]):
        """Кэширует сессию в Redis"""
        key = f"session:{session_id}"
        await self.redis.setex(
            key,
            1800,  # 30 minutes TTL
            json.dumps(session_data, default=str)
        )

    async def _get_cached_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Получает сессию из cache"""
        key = f"session:{session_id}"
        data = await self.redis.get(key)

        if data:
            return json.loads(data)

        return None

    async def _clear_cache(self, session_id: int):
        """Очищает cache сессии"""
        key = f"session:{session_id}"
        await self.redis.delete(key)


# ============================================================================
# SESSION MANAGEMENT SERVICE
# ============================================================================

class SessionManagementService(BaseSystem):
    """
    Session Management Service

    Микросервис для управления сессиями онбординга.
    """

    def __init__(
        self,
        event_bus: EventBus,
        db_pool: asyncpg.Pool,
        redis_client: redis.Redis
    ):
        super().__init__(name="session_management_service", event_bus=event_bus)

        self.db_pool = db_pool
        self.redis = redis_client
        self.outbox_publisher = OutboxPublisher(schema="selfology")
        self.session_manager = SessionManager(db_pool, redis_client)

        # Background tasks
        self._timeout_checker_task: Optional[asyncio.Task] = None

    async def start(self):
        """Запускает Session Management Service"""
        logger.info("Starting Session Management Service...")

        # Event Consumers
        await self.add_event_consumer(
            event_types=["user.onboarding.initiated"],
            handler=self.handle_onboarding_initiated,
            consumer_name="session_creator_worker"
        )

        await self.add_event_consumer(
            event_types=["user.answer.submitted"],
            handler=self.handle_answer_submitted,
            consumer_name="session_updater_worker"
        )

        await self.add_event_consumer(
            event_types=["session.completed"],
            handler=self.handle_session_completed,
            consumer_name="session_completer_worker"
        )

        # Background task для проверки timeouts
        self._timeout_checker_task = asyncio.create_task(
            self._timeout_checker_loop()
        )

        self.state = self.state.RUNNING
        logger.info("✅ Session Management Service started")

    async def stop(self):
        """Graceful shutdown"""
        logger.info("Stopping Session Management Service...")

        # Stop consumers
        await self.stop_all_consumers()

        # Stop background tasks
        if self._timeout_checker_task:
            self._timeout_checker_task.cancel()
            try:
                await self._timeout_checker_task
            except asyncio.CancelledError:
                pass

        logger.info("✅ Session Management Service stopped")

    async def health_check(self) -> Dict[str, Any]:
        """Health check"""
        checks = {}

        # Database
        try:
            async with self.db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            checks["database"] = "healthy"
        except Exception:
            checks["database"] = "unhealthy"

        # Redis
        try:
            await self.redis.ping()
            checks["redis"] = "healthy"
        except Exception:
            checks["redis"] = "unhealthy"

        # Event Bus
        try:
            await self.event_bus.redis.ping()
            checks["event_bus"] = "healthy"
        except Exception:
            checks["event_bus"] = "unhealthy"

        status = HealthStatus.HEALTHY if all(
            v == "healthy" for v in checks.values()
        ) else HealthStatus.UNHEALTHY

        return {
            "status": status.value,
            "checks": checks,
            "metrics": self.get_metrics()
        }

    # ========================================================================
    # EVENT HANDLERS
    # ========================================================================

    async def handle_onboarding_initiated(
        self,
        event_type: str,
        payload: Dict[str, Any]
    ):
        """
        Обрабатывает начало онбординга

        Создает сессию и публикует session.created
        """
        user_id = payload["user_id"]

        # Создаем сессию
        session_id = await self.session_manager.create_session(user_id)

        # Публикуем событие session.created через Outbox
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                await self.outbox_publisher.publish(
                    conn,
                    "session.created",
                    {
                        "user_id": user_id,
                        "session_id": session_id,
                        "created_at": datetime.now().isoformat()
                    },
                    trace_id=payload.get("trace_id")
                )

        # Также публикуем user.session.started для Question Selection
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                await self.outbox_publisher.publish(
                    conn,
                    "user.session.started",
                    {
                        "user_id": user_id,
                        "session_id": session_id
                    },
                    trace_id=payload.get("trace_id")
                )

        self.increment_metric("sessions_created")

    async def handle_answer_submitted(
        self,
        event_type: str,
        payload: Dict[str, Any]
    ):
        """
        Обрабатывает ответ пользователя

        Обновляет last_activity_at сессии
        """
        session_id = payload.get("session_id")

        if session_id:
            await self.session_manager.update_session_activity(
                session_id,
                {"question_id": payload["question_id"]}
            )

        self.increment_metric("session_activities")

    async def handle_session_completed(
        self,
        event_type: str,
        payload: Dict[str, Any]
    ):
        """Обрабатывает завершение сессии"""
        session_id = payload["session_id"]

        # Завершаем сессию
        await self.session_manager.complete_session(session_id)

        # Публикуем аналитику
        analytics = await self.session_manager.get_session_analytics(session_id)

        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                await self.outbox_publisher.publish(
                    conn,
                    "session.analytics.updated",
                    {
                        "session_id": session_id,
                        "analytics": analytics
                    },
                    trace_id=payload.get("trace_id")
                )

        self.increment_metric("sessions_completed")

    # ========================================================================
    # BACKGROUND TASKS
    # ========================================================================

    async def _timeout_checker_loop(self):
        """Фоновая проверка timeout сессий"""
        while True:
            try:
                await asyncio.sleep(300)  # Каждые 5 минут

                timed_out_ids = await self.session_manager.check_timeouts()

                # Публикуем события о timeout
                for session_id in timed_out_ids:
                    session = await self.session_manager.get_session(session_id)

                    if session:
                        async with self.db_pool.acquire() as conn:
                            async with conn.transaction():
                                await self.outbox_publisher.publish(
                                    conn,
                                    "session.timed_out",
                                    {
                                        "session_id": session_id,
                                        "user_id": session["user_id"]
                                    }
                                )

                self.set_metric("timed_out_sessions", len(timed_out_ids))

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Timeout checker error: {e}", exc_info=True)


# ============================================================================
# FACTORY
# ============================================================================

async def create_session_management_service(
    event_bus: EventBus,
    db_config: Dict[str, Any],
    redis_url: str = "redis://n8n-redis:6379"
) -> SessionManagementService:
    """
    Factory для создания Session Management Service

    Args:
        event_bus: Event Bus instance
        db_config: Database configuration
        redis_url: Redis URL

    Returns:
        SessionManagementService instance
    """
    # Create database pool
    db_pool = await asyncpg.create_pool(
        host=db_config.get("host", "n8n-postgres"),
        port=db_config.get("port", 5432),
        user=db_config.get("user", "n8n"),
        password=db_config["password"],
        database=db_config.get("database", "n8n"),
        min_size=2,
        max_size=10
    )

    # Create Redis client
    redis_client = await redis.from_url(redis_url, decode_responses=True)

    # Create service
    service = SessionManagementService(
        event_bus=event_bus,
        db_pool=db_pool,
        redis_client=redis_client
    )

    return service
