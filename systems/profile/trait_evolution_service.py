"""
Trait Evolution Service

Микросервис для отслеживания эволюции психологических черт:
- Анализ изменений черт во времени
- Обнаружение паттернов развития
- Prediction будущих изменений
- История всех изменений в trait_history

Architecture:
    TraitEvolutionService (BaseSystem)
    ↓
    ├── TraitHistoryManager (CRUD для trait_history)
    ├── EvolutionAnalyzer (анализ паттернов изменений)
    └── Event Handlers (trait.extracted → track evolution)

Events consumed:
- trait.extracted (from Analysis System)

Events published:
- trait.evolution.detected (when significant change detected)
- trait.pattern.identified (when pattern emerges)
"""

import asyncio
import asyncpg
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from systems.base import BaseSystem
from core.event_bus import EventBus
from core.outbox_pattern import OutboxPublisher

logger = logging.getLogger(__name__)


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class TraitChange:
    """Представляет изменение черты"""
    trait_category: str
    trait_name: str
    old_value: Optional[float]
    new_value: float
    confidence: float
    trigger: Optional[str]
    timestamp: datetime


@dataclass
class EvolutionPattern:
    """Представляет обнаруженный паттерн эволюции"""
    trait_category: str
    trait_name: str
    pattern_type: str  # "increasing", "decreasing", "oscillating", "stable"
    strength: float  # 0-1 насколько сильный паттерн
    duration_days: int
    confidence: float


# ============================================================================
# TRAIT HISTORY MANAGER
# ============================================================================

class TraitHistoryManager:
    """
    Управление историей изменений черт в PostgreSQL

    Features:
    - Запись всех изменений черт
    - Получение истории по пользователю/черте
    - Анализ тренда изменений
    """

    def __init__(self, db_pool: asyncpg.Pool):
        """
        Args:
            db_pool: PostgreSQL connection pool
        """
        self.db_pool = db_pool

    async def record_change(
        self,
        user_id: int,
        trait_category: str,
        trait_name: str,
        old_value: Optional[float],
        new_value: float,
        confidence: float,
        trigger: Optional[str] = None
    ) -> int:
        """
        Записывает изменение черты в историю

        Args:
            user_id: ID пользователя
            trait_category: Категория черты (big_five, core_dynamics, etc.)
            trait_name: Название черты
            old_value: Старое значение (None для первого)
            new_value: Новое значение
            confidence: Уверенность в изменении
            trigger: Что вызвало изменение

        Returns:
            ID записи в trait_history
        """
        async with self.db_pool.acquire() as conn:
            history_id = await conn.fetchval(
                """
                INSERT INTO selfology.trait_history
                    (user_id, trait_category, trait_name, old_value, new_value, confidence, trigger)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
                """,
                user_id,
                trait_category,
                trait_name,
                old_value,
                new_value,
                confidence,
                trigger
            )

        logger.info(
            f"Recorded trait change for user {user_id}: "
            f"{trait_category}.{trait_name} {old_value} → {new_value}"
        )

        return history_id

    async def get_trait_history(
        self,
        user_id: int,
        trait_category: Optional[str] = None,
        trait_name: Optional[str] = None,
        limit: int = 100
    ) -> List[TraitChange]:
        """
        Получает историю изменений черты

        Args:
            user_id: ID пользователя
            trait_category: Фильтр по категории (optional)
            trait_name: Фильтр по названию (optional)
            limit: Максимум записей

        Returns:
            Список изменений черты
        """
        query = """
            SELECT trait_category, trait_name, old_value, new_value,
                   confidence, trigger, timestamp
            FROM selfology.trait_history
            WHERE user_id = $1
        """
        params = [user_id]

        if trait_category:
            query += " AND trait_category = $2"
            params.append(trait_category)

        if trait_name:
            query += f" AND trait_name = ${len(params) + 1}"
            params.append(trait_name)

        query += f" ORDER BY timestamp DESC LIMIT ${len(params) + 1}"
        params.append(limit)

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [
            TraitChange(
                trait_category=row["trait_category"],
                trait_name=row["trait_name"],
                old_value=row["old_value"],
                new_value=row["new_value"],
                confidence=row["confidence"],
                trigger=row["trigger"],
                timestamp=row["timestamp"]
            )
            for row in rows
        ]

    async def get_latest_values(
        self,
        user_id: int,
        trait_category: str
    ) -> Dict[str, float]:
        """
        Получает последние значения всех черт в категории

        Args:
            user_id: ID пользователя
            trait_category: Категория черт

        Returns:
            Словарь {trait_name: latest_value}
        """
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT DISTINCT ON (trait_name)
                    trait_name, new_value
                FROM selfology.trait_history
                WHERE user_id = $1 AND trait_category = $2
                ORDER BY trait_name, timestamp DESC
                """,
                user_id,
                trait_category
            )

        return {row["trait_name"]: row["new_value"] for row in rows}


# ============================================================================
# EVOLUTION ANALYZER
# ============================================================================

class EvolutionAnalyzer:
    """
    Анализатор эволюции черт

    Features:
    - Обнаружение трендов (increasing/decreasing/stable)
    - Выявление паттернов (oscillating, linear, exponential)
    - Prediction будущих значений
    """

    def __init__(self, history_manager: TraitHistoryManager):
        """
        Args:
            history_manager: TraitHistoryManager instance
        """
        self.history_manager = history_manager

    async def analyze_evolution(
        self,
        user_id: int,
        trait_category: str,
        trait_name: str,
        lookback_days: int = 30
    ) -> Optional[EvolutionPattern]:
        """
        Анализирует эволюцию конкретной черты

        Args:
            user_id: ID пользователя
            trait_category: Категория черты
            trait_name: Название черты
            lookback_days: Сколько дней назад анализировать

        Returns:
            EvolutionPattern если найден, иначе None
        """
        # Get history for trait
        history = await self.history_manager.get_trait_history(
            user_id=user_id,
            trait_category=trait_category,
            trait_name=trait_name,
            limit=100
        )

        if len(history) < 2:
            return None  # Недостаточно данных

        # Filter by lookback period
        cutoff_date = datetime.now() - timedelta(days=lookback_days)
        recent_history = [
            change for change in history
            if change.timestamp >= cutoff_date
        ]

        if len(recent_history) < 2:
            return None

        # Analyze pattern
        pattern_type, strength = self._detect_pattern(recent_history)

        # Calculate average confidence
        avg_confidence = sum(c.confidence for c in recent_history) / len(recent_history)

        return EvolutionPattern(
            trait_category=trait_category,
            trait_name=trait_name,
            pattern_type=pattern_type,
            strength=strength,
            duration_days=lookback_days,
            confidence=avg_confidence
        )

    def _detect_pattern(
        self,
        history: List[TraitChange]
    ) -> Tuple[str, float]:
        """
        Обнаруживает тип паттерна в истории изменений

        Args:
            history: Список изменений (sorted by timestamp DESC)

        Returns:
            (pattern_type, strength)
        """
        if len(history) < 2:
            return "stable", 0.0

        # Reverse для хронологического порядка
        history = list(reversed(history))

        values = [change.new_value for change in history]
        n = len(values)

        # Calculate trend
        first_half_avg = sum(values[:n//2]) / (n//2)
        second_half_avg = sum(values[n//2:]) / (n - n//2)
        trend = second_half_avg - first_half_avg

        # Calculate variation
        avg_value = sum(values) / n
        variance = sum((v - avg_value) ** 2 for v in values) / n
        std_dev = variance ** 0.5

        # Determine pattern type
        if abs(trend) < 0.05:
            # Stable - малые изменения
            return "stable", 1.0 - std_dev
        elif trend > 0.15:
            # Increasing - заметный рост
            return "increasing", min(trend, 1.0)
        elif trend < -0.15:
            # Decreasing - заметное снижение
            return "decreasing", min(abs(trend), 1.0)
        elif std_dev > 0.15:
            # Oscillating - колебания
            return "oscillating", std_dev
        else:
            # Stable with slight trend
            return "stable", 0.5

    async def detect_significant_changes(
        self,
        user_id: int,
        threshold: float = 0.2
    ) -> List[Dict[str, Any]]:
        """
        Обнаруживает значительные изменения в чертах пользователя

        Args:
            user_id: ID пользователя
            threshold: Минимальное изменение для "значительного"

        Returns:
            Список значительных изменений
        """
        significant_changes = []

        # Check all recent changes (last 7 days)
        cutoff = datetime.now() - timedelta(days=7)

        async with self.history_manager.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT trait_category, trait_name, old_value, new_value,
                       confidence, timestamp
                FROM selfology.trait_history
                WHERE user_id = $1
                  AND timestamp >= $2
                  AND old_value IS NOT NULL
                ORDER BY timestamp DESC
                """,
                user_id,
                cutoff
            )

        for row in rows:
            change = abs(row["new_value"] - row["old_value"])
            if change >= threshold:
                significant_changes.append({
                    "trait_category": row["trait_category"],
                    "trait_name": row["trait_name"],
                    "old_value": row["old_value"],
                    "new_value": row["new_value"],
                    "change": change,
                    "confidence": row["confidence"],
                    "timestamp": row["timestamp"]
                })

        return significant_changes


# ============================================================================
# TRAIT EVOLUTION SERVICE
# ============================================================================

class TraitEvolutionService(BaseSystem):
    """
    Trait Evolution Service - отслеживание эволюции черт

    Features:
    - Запись истории изменений черт
    - Анализ паттернов эволюции
    - Обнаружение значительных изменений
    - Event-driven обработка trait.extracted
    """

    def __init__(
        self,
        event_bus: EventBus,
        db_pool: asyncpg.Pool
    ):
        """
        Args:
            event_bus: Event Bus instance
            db_pool: PostgreSQL connection pool
        """
        super().__init__(
            name="trait_evolution_service",
            event_bus=event_bus
        )

        self.db_pool = db_pool
        self.history_manager = TraitHistoryManager(db_pool)
        self.analyzer = EvolutionAnalyzer(self.history_manager)

        # Metrics
        self.metrics = {
            "changes_recorded": 0,
            "patterns_detected": 0,
            "significant_changes": 0
        }

    async def start(self):
        """Запускает сервис"""
        await super().start()

        # Subscribe to trait.extracted events
        await self.event_bus.subscribe(
            event_type="trait.extracted",
            consumer_group="trait_evolution",
            handler=self._handle_trait_extracted
        )

        logger.info(f"✅ {self.name} started and subscribed to events")

    async def _handle_trait_extracted(self, event: Dict[str, Any]):
        """
        Обрабатывает событие trait.extracted из Analysis System

        Event payload:
        {
            "user_id": int,
            "traits": {
                "big_five": {"openness": 0.75, ...},
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

            # Get previous values for comparison
            changes_recorded = []

            for trait_category, category_traits in traits.items():
                # Get latest values
                latest_values = await self.history_manager.get_latest_values(
                    user_id=user_id,
                    trait_category=trait_category
                )

                # Record changes for each trait
                for trait_name, new_value in category_traits.items():
                    old_value = latest_values.get(trait_name)

                    # Only record if value changed or first time
                    if old_value is None or abs(new_value - old_value) > 0.01:
                        history_id = await self.history_manager.record_change(
                            user_id=user_id,
                            trait_category=trait_category,
                            trait_name=trait_name,
                            old_value=old_value,
                            new_value=new_value,
                            confidence=confidence,
                            trigger=event.get("source", "analysis")
                        )

                        changes_recorded.append({
                            "history_id": history_id,
                            "trait_category": trait_category,
                            "trait_name": trait_name,
                            "change": new_value - old_value if old_value else new_value
                        })

                        self.metrics["changes_recorded"] += 1

            # Analyze for patterns and significant changes
            if changes_recorded:
                await self._analyze_and_publish(user_id, changes_recorded, event)

            logger.info(f"✅ Recorded {len(changes_recorded)} trait changes for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to handle trait.extracted: {e}", exc_info=True)
            raise

    async def _analyze_and_publish(
        self,
        user_id: int,
        changes: List[Dict[str, Any]],
        original_event: Dict[str, Any]
    ):
        """
        Анализирует изменения и публикует события если найдены паттерны

        Args:
            user_id: ID пользователя
            changes: Список записанных изменений
            original_event: Оригинальное событие trait.extracted
        """
        # Check for significant changes
        significant = [c for c in changes if abs(c["change"]) >= 0.2]

        if significant:
            self.metrics["significant_changes"] += len(significant)

            # Publish trait.evolution.detected
            async with self.db_pool.acquire() as conn:
                async with conn.transaction():
                    outbox_publisher = OutboxPublisher(schema="selfology")
                    await outbox_publisher.publish(
                        conn,
                        "trait.evolution.detected",
                        {
                            "user_id": user_id,
                            "significant_changes": significant,
                            "timestamp": datetime.now().isoformat()
                        },
                        trace_id=original_event.get("trace_id")
                    )

            logger.info(f"🔔 Detected {len(significant)} significant trait changes for user {user_id}")

        # Analyze patterns (for first change in each category)
        patterns_found = []
        for change in changes:
            pattern = await self.analyzer.analyze_evolution(
                user_id=user_id,
                trait_category=change["trait_category"],
                trait_name=change["trait_name"],
                lookback_days=30
            )

            if pattern and pattern.strength > 0.5:
                patterns_found.append({
                    "trait_category": pattern.trait_category,
                    "trait_name": pattern.trait_name,
                    "pattern_type": pattern.pattern_type,
                    "strength": pattern.strength,
                    "confidence": pattern.confidence
                })

        if patterns_found:
            self.metrics["patterns_detected"] += len(patterns_found)

            # Publish trait.pattern.identified
            async with self.db_pool.acquire() as conn:
                async with conn.transaction():
                    outbox_publisher = OutboxPublisher(schema="selfology")
                    await outbox_publisher.publish(
                        conn,
                        "trait.pattern.identified",
                        {
                            "user_id": user_id,
                            "patterns": patterns_found,
                            "timestamp": datetime.now().isoformat()
                        },
                        trace_id=original_event.get("trace_id")
                    )

            logger.info(f"📊 Identified {len(patterns_found)} trait patterns for user {user_id}")

    async def health_check(self) -> Dict[str, Any]:
        """
        Проверяет здоровье сервиса

        Returns:
            Health status с метриками
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

        health.update({
            "database": "healthy" if db_healthy else "unhealthy",
            "metrics": self.metrics
        })

        if not db_healthy:
            health["status"] = "unhealthy"

        return health

    def get_metrics(self) -> Dict[str, Any]:
        """Возвращает метрики сервиса"""
        return self.metrics.copy()


# ============================================================================
# FACTORY
# ============================================================================

def create_trait_evolution_service(
    event_bus: EventBus,
    db_pool: asyncpg.Pool
) -> TraitEvolutionService:
    """
    Factory для создания Trait Evolution Service

    Args:
        event_bus: Event Bus instance
        db_pool: PostgreSQL connection pool

    Returns:
        Configured TraitEvolutionService instance
    """
    return TraitEvolutionService(
        event_bus=event_bus,
        db_pool=db_pool
    )
