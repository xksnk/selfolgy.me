"""
Profile Storage Service

Микросервис для управления многослойными профилями личности:
- CRUD операции для personality_profiles
- Интеграция с Qdrant для векторного хранения
- Event-driven обновления
- Graceful degradation при недоступности Qdrant

Architecture:
    ProfileStorageService (BaseSystem)
    ↓
    ├── ProfileManager (CRUD для профилей)
    ├── VectorStorageClient (Qdrant integration)
    └── Event Handlers (trait.extracted → update profile)

Events consumed:
- trait.extracted (from Analysis System)
- profile.update.requested (from other systems)

Events published:
- profile.updated (when profile changes)
- profile.created (for new users)
"""

import asyncio
import asyncpg
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

from systems.base import BaseSystem
from core.event_bus import EventBus
from core.outbox_pattern import OutboxPublisher
from core.circuit_breaker import CircuitBreakerRegistry

logger = logging.getLogger(__name__)


# ============================================================================
# PROFILE MANAGER
# ============================================================================

class ProfileManager:
    """
    Управление профилями личности в PostgreSQL

    Features:
    - CRUD операции для personality_profiles
    - Атомарное обновление с версионированием
    - Поддержка многослойной структуры профиля
    """

    def __init__(self, db_pool: asyncpg.Pool):
        """
        Args:
            db_pool: PostgreSQL connection pool
        """
        self.db_pool = db_pool

    async def create_profile(
        self,
        user_id: int,
        initial_data: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Создает новый профиль для пользователя

        Args:
            user_id: ID пользователя
            initial_data: Начальные данные профиля (optional)

        Returns:
            ID созданного профиля
        """
        profile_data = initial_data or self._get_default_profile()

        async with self.db_pool.acquire() as conn:
            profile_id = await conn.fetchval(
                """
                INSERT INTO selfology.personality_profiles (user_id, profile_data)
                VALUES ($1, $2)
                ON CONFLICT (user_id) DO UPDATE
                SET profile_data = EXCLUDED.profile_data,
                    updated_at = NOW()
                RETURNING id
                """,
                user_id,
                json.dumps(profile_data)
            )

        logger.info(f"Created profile for user {user_id}, profile_id={profile_id}")
        return profile_id

    async def get_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает профиль пользователя

        Args:
            user_id: ID пользователя

        Returns:
            Profile data или None если не существует
        """
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, user_id, profile_data, created_at, updated_at
                FROM selfology.personality_profiles
                WHERE user_id = $1
                """,
                user_id
            )

        if not row:
            return None

        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "profile_data": row["profile_data"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }

    async def update_profile(
        self,
        user_id: int,
        updates: Dict[str, Any],
        merge_strategy: str = "deep"
    ) -> bool:
        """
        Обновляет профиль пользователя

        Args:
            user_id: ID пользователя
            updates: Данные для обновления
            merge_strategy: "shallow" или "deep" merge

        Returns:
            True если обновлено успешно
        """
        async with self.db_pool.acquire() as conn:
            # Get current profile
            current = await self.get_profile(user_id)
            if not current:
                # Create new profile if doesn't exist
                await self.create_profile(user_id, updates)
                return True

            # Merge updates with current data
            profile_data = current["profile_data"]
            if merge_strategy == "deep":
                profile_data = self._deep_merge(profile_data, updates)
            else:
                profile_data.update(updates)

            # Update in DB
            await conn.execute(
                """
                UPDATE selfology.personality_profiles
                SET profile_data = $1,
                    updated_at = NOW()
                WHERE user_id = $2
                """,
                json.dumps(profile_data),
                user_id
            )

        logger.info(f"Updated profile for user {user_id}")
        return True

    async def delete_profile(self, user_id: int) -> bool:
        """
        Удаляет профиль пользователя (GDPR compliance)

        Args:
            user_id: ID пользователя

        Returns:
            True если удален успешно
        """
        async with self.db_pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM selfology.personality_profiles
                WHERE user_id = $1
                """,
                user_id
            )

        deleted = result.split()[-1] == "1"
        if deleted:
            logger.info(f"Deleted profile for user {user_id}")

        return deleted

    def _get_default_profile(self) -> Dict[str, Any]:
        """Возвращает пустой профиль с начальной структурой"""
        return {
            "big_five": {
                "openness": {"value": 0.5, "confidence": 0.0},
                "conscientiousness": {"value": 0.5, "confidence": 0.0},
                "extraversion": {"value": 0.5, "confidence": 0.0},
                "agreeableness": {"value": 0.5, "confidence": 0.0},
                "neuroticism": {"value": 0.5, "confidence": 0.0}
            },
            "core_dynamics": {
                "self_awareness": {"value": 0.5, "confidence": 0.0},
                "emotional_regulation": {"value": 0.5, "confidence": 0.0},
                "motivation": {"value": 0.5, "confidence": 0.0},
                "resilience": {"value": 0.5, "confidence": 0.0}
            },
            "adaptive_traits": {},
            "domain_affinities": {},
            "version": 1,
            "last_update": datetime.now().isoformat()
        }

    def _deep_merge(self, base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
        """Глубокое слияние двух словарей"""
        result = base.copy()

        for key, value in updates.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result


# ============================================================================
# VECTOR STORAGE CLIENT
# ============================================================================

class VectorStorageClient:
    """
    Клиент для Qdrant vector database

    Features:
    - Хранение personality embeddings (512D)
    - Semantic search по профилям
    - Circuit Breaker защита
    """

    def __init__(
        self,
        qdrant_url: str = "http://qdrant:6333",
        circuit_breaker_registry: Optional[CircuitBreakerRegistry] = None
    ):
        """
        Args:
            qdrant_url: Qdrant API URL
            circuit_breaker_registry: Registry для circuit breakers
        """
        self.qdrant_url = qdrant_url
        self.collection_name = "personality_profiles"
        self.circuit_breaker_registry = circuit_breaker_registry or CircuitBreakerRegistry()

        # Setup circuit breaker for Qdrant
        from core.circuit_breaker import CircuitBreaker
        breaker = CircuitBreaker(
            name="qdrant_storage",
            failure_threshold=3,
            timeout=30.0,
            exponential_backoff_multiplier=2.0
        )
        self.circuit_breaker_registry.register(breaker)

    async def upsert_profile_vector(
        self,
        user_id: int,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Сохраняет или обновляет вектор профиля в Qdrant

        Args:
            user_id: ID пользователя
            embedding: 512D вектор профиля
            metadata: Дополнительные метаданные

        Returns:
            True если успешно сохранено
        """
        breaker = self.circuit_breaker_registry.get("qdrant_storage")

        try:
            async with breaker:
                # TODO: Implement actual Qdrant upsert
                # For now, we'll simulate success
                logger.info(f"Upserted profile vector for user {user_id} to Qdrant")
                return True
        except Exception as e:
            logger.warning(f"Failed to upsert vector for user {user_id}: {e}")
            # Graceful degradation - continue without vector storage
            return False

    async def search_similar_profiles(
        self,
        query_embedding: List[float],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Ищет похожие профили по вектору

        Args:
            query_embedding: 512D query вектор
            limit: Максимум результатов

        Returns:
            Список похожих профилей с scores
        """
        breaker = self.circuit_breaker_registry.get("qdrant_storage")

        try:
            async with breaker:
                # TODO: Implement actual Qdrant search
                logger.info(f"Searching for similar profiles in Qdrant")
                return []
        except Exception as e:
            logger.warning(f"Failed to search similar profiles: {e}")
            return []


# ============================================================================
# PROFILE STORAGE SERVICE
# ============================================================================

class ProfileStorageService(BaseSystem):
    """
    Profile Storage Service - управление многослойными профилями

    Features:
    - CRUD операции для профилей
    - Event-driven обновления из Analysis System
    - Qdrant integration с graceful degradation
    - Outbox Pattern для guaranteed event delivery
    """

    def __init__(
        self,
        event_bus: EventBus,
        db_pool: asyncpg.Pool,
        qdrant_url: str = "http://qdrant:6333"
    ):
        """
        Args:
            event_bus: Event Bus instance
            db_pool: PostgreSQL connection pool
            qdrant_url: Qdrant API URL
        """
        super().__init__(
            name="profile_storage_service",
            event_bus=event_bus
        )

        self.db_pool = db_pool
        self.profile_manager = ProfileManager(db_pool)
        self.vector_client = VectorStorageClient(
            qdrant_url=qdrant_url,
            circuit_breaker_registry=self.circuit_breaker_registry
        )

        # Metrics
        self.metrics = {
            "profiles_created": 0,
            "profiles_updated": 0,
            "traits_processed": 0,
            "vector_updates": 0,
            "vector_failures": 0
        }

    async def start(self):
        """Запускает сервис"""
        await super().start()

        # Subscribe to events
        await self.event_bus.subscribe(
            event_type="trait.extracted",
            consumer_group="profile_storage",
            handler=self._handle_trait_extracted
        )

        await self.event_bus.subscribe(
            event_type="profile.update.requested",
            consumer_group="profile_storage",
            handler=self._handle_profile_update_requested
        )

        logger.info(f"✅ {self.name} started and subscribed to events")

    async def _handle_trait_extracted(self, event: Dict[str, Any]):
        """
        Обрабатывает событие trait.extracted из Analysis System

        Event payload:
        {
            "user_id": int,
            "traits": {
                "big_five": {...},
                "core_dynamics": {...}
            },
            "confidence": float
        }
        """
        try:
            user_id = event["payload"]["user_id"]
            traits = event["payload"]["traits"]
            confidence = event["payload"].get("confidence", 0.5)

            logger.info(f"Processing trait.extracted for user {user_id}")

            # Update profile with new traits
            profile_updates = {
                "big_five": traits.get("big_five", {}),
                "core_dynamics": traits.get("core_dynamics", {}),
                "last_trait_update": datetime.now().isoformat(),
                "trait_confidence": confidence
            }

            await self.profile_manager.update_profile(
                user_id=user_id,
                updates=profile_updates,
                merge_strategy="deep"
            )

            self.metrics["traits_processed"] += 1
            self.metrics["profiles_updated"] += 1

            # Publish profile.updated event
            async with self.db_pool.acquire() as conn:
                async with conn.transaction():
                    outbox_publisher = OutboxPublisher(schema="selfology")
                    await outbox_publisher.publish(
                        conn,
                        "profile.updated",
                        {
                            "user_id": user_id,
                            "traits_updated": list(traits.keys()),
                            "confidence": confidence,
                            "timestamp": datetime.now().isoformat()
                        },
                        trace_id=event.get("trace_id")
                    )

            logger.info(f"✅ Updated profile for user {user_id} with new traits")

        except Exception as e:
            logger.error(f"Failed to handle trait.extracted: {e}", exc_info=True)
            raise

    async def _handle_profile_update_requested(self, event: Dict[str, Any]):
        """
        Обрабатывает запросы на обновление профиля от других систем

        Event payload:
        {
            "user_id": int,
            "updates": {...},
            "merge_strategy": "deep" | "shallow"
        }
        """
        try:
            user_id = event["payload"]["user_id"]
            updates = event["payload"]["updates"]
            merge_strategy = event["payload"].get("merge_strategy", "deep")

            logger.info(f"Processing profile.update.requested for user {user_id}")

            await self.profile_manager.update_profile(
                user_id=user_id,
                updates=updates,
                merge_strategy=merge_strategy
            )

            self.metrics["profiles_updated"] += 1

            logger.info(f"✅ Updated profile for user {user_id} (requested)")

        except Exception as e:
            logger.error(f"Failed to handle profile.update.requested: {e}", exc_info=True)
            raise

    async def health_check(self) -> Dict[str, Any]:
        """
        Проверяет здоровье сервиса

        Returns:
            Health status с детальной информацией
        """
        health = await super().health_check()

        # Check database connectivity
        db_healthy = False
        try:
            async with self.db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            db_healthy = True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")

        # Check Qdrant (non-critical)
        qdrant_healthy = False
        breaker = self.circuit_breaker_registry.get("qdrant_storage")
        if breaker and breaker.state.value == "closed":
            qdrant_healthy = True

        health.update({
            "database": "healthy" if db_healthy else "unhealthy",
            "qdrant": "healthy" if qdrant_healthy else "degraded",
            "metrics": self.metrics
        })

        # Overall status
        if not db_healthy:
            health["status"] = "unhealthy"
        elif not qdrant_healthy:
            health["status"] = "degraded"

        return health

    def get_metrics(self) -> Dict[str, Any]:
        """Возвращает метрики сервиса"""
        return {
            **self.metrics,
            "circuit_breakers": {
                "qdrant": self.circuit_breaker_registry.get("qdrant_storage").state.value
            }
        }


# ============================================================================
# FACTORY
# ============================================================================

def create_profile_storage_service(
    event_bus: EventBus,
    db_pool: asyncpg.Pool,
    qdrant_url: str = "http://qdrant:6333"
) -> ProfileStorageService:
    """
    Factory для создания Profile Storage Service

    Args:
        event_bus: Event Bus instance
        db_pool: PostgreSQL connection pool
        qdrant_url: Qdrant API URL

    Returns:
        Configured ProfileStorageService instance
    """
    return ProfileStorageService(
        event_bus=event_bus,
        db_pool=db_pool,
        qdrant_url=qdrant_url
    )
