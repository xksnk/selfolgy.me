"""
Insight Generator Service

Фоновая генерация психологических инсайтов:
- Анализ паттернов в профиле и истории
- Периодическая генерация инсайтов (раз в день/неделю)
- Хранение инсайтов для показа пользователю

Architecture:
    InsightGeneratorService (BaseSystem)
    ↓
    ├── PatternAnalyzer (находит паттерны в данных)
    ├── InsightGenerator (создает инсайты через AI)
    └── Background Tasks (scheduled insight generation)

Events consumed:
- trait.evolution.detected (trigger для insights)
- profile.updated (может вызвать новые insights)

Events published:
- insight.generated
- insight.ready_for_user
"""

import asyncio
import asyncpg
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from systems.base import BaseSystem
from core.event_bus import EventBus
from core.outbox_pattern import OutboxPublisher
from systems.analysis.ai_router import AIRouter, AIModel

logger = logging.getLogger(__name__)


class InsightGeneratorService(BaseSystem):
    """
    Insight Generator - фоновая генерация инсайтов

    Features:
    - Pattern-based insights
    - AI-generated insights
    - Periodic generation (background task)
    """

    def __init__(
        self,
        event_bus: EventBus,
        db_pool: asyncpg.Pool,
        ai_router: AIRouter
    ):
        super().__init__(name="insight_generator_service", event_bus=event_bus)
        self.db_pool = db_pool
        self.ai_router = ai_router
        self.metrics = {"insights_generated": 0, "patterns_found": 0, "errors": 0}

    async def start(self):
        await super().start()

        await self.event_bus.subscribe(
            event_type="trait.evolution.detected",
            consumer_group="insight_generator",
            handler=self._handle_trait_evolution
        )

        # Start background task for periodic insights
        asyncio.create_task(self._periodic_insight_generation())

        logger.info(f"✅ {self.name} started")

    async def _handle_trait_evolution(self, event: Dict[str, Any]):
        """Generates insight when significant trait changes detected"""
        try:
            payload = event["payload"]
            user_id = payload["user_id"]
            changes = payload.get("significant_changes", [])

            if not changes:
                return

            # Generate insight about changes
            insight_text = await self._generate_evolution_insight(user_id, changes)

            if insight_text:
                await self._save_insight(user_id, "trait_evolution", insight_text)
                self.metrics["insights_generated"] += 1

                # Publish event
                async with self.db_pool.acquire() as conn:
                    async with conn.transaction():
                        outbox_publisher = OutboxPublisher(schema="selfology")
                        await outbox_publisher.publish(
                            conn,
                            "insight.generated",
                            {
                                "user_id": user_id,
                                "insight_type": "trait_evolution",
                                "insight_text": insight_text,
                                "timestamp": datetime.now().isoformat()
                            },
                            trace_id=event.get("trace_id")
                        )

        except Exception as e:
            logger.error(f"Failed to handle trait evolution: {e}", exc_info=True)
            self.metrics["errors"] += 1

    async def _generate_evolution_insight(
        self,
        user_id: int,
        changes: List[Dict[str, Any]]
    ) -> Optional[str]:
        """Uses AI to generate insight about trait changes"""
        try:
            # Build prompt
            changes_desc = "\n".join([
                f"- {c['trait_name']}: {c['old_value']:.2f} → {c['new_value']:.2f} (change: {c['change']:.2f})"
                for c in changes
            ])

            messages = [
                {
                    "role": "system",
                    "content": "Ты психологический коуч. Создай короткий (2-3 предложения) инсайт о значимых изменениях в личности пользователя."
                },
                {
                    "role": "user",
                    "content": f"Обнаружены изменения:\n{changes_desc}\n\nСоздай позитивный, поддерживающий инсайт."
                }
            ]

            result = await self.ai_router.call_ai(
                model=AIModel.GPT4O_MINI,  # Simple task
                messages=messages,
                max_tokens=200,
                temperature=0.7,
                allow_fallback=True
            )

            return result["content"]

        except Exception as e:
            logger.error(f"Failed to generate insight: {e}")
            return None

    async def _save_insight(
        self,
        user_id: int,
        insight_type: str,
        content: str
    ) -> int:
        """Saves generated insight to database"""
        async with self.db_pool.acquire() as conn:
            insight_id = await conn.fetchval(
                """
                INSERT INTO selfology.insights (user_id, insight_type, content)
                VALUES ($1, $2, $3)
                RETURNING id
                """,
                user_id,
                insight_type,
                content
            )
        return insight_id

    async def _periodic_insight_generation(self):
        """Background task for periodic insights (runs daily)"""
        while True:
            try:
                await asyncio.sleep(86400)  # 24 hours

                # TODO: Generate weekly/monthly insights for all active users
                logger.info("Periodic insight generation (placeholder)")

            except Exception as e:
                logger.error(f"Periodic insight generation error: {e}")
                await asyncio.sleep(3600)  # Retry in 1 hour

    async def health_check(self) -> Dict[str, Any]:
        health = await super().health_check()
        health.update({"metrics": self.metrics})
        return health

    def get_metrics(self) -> Dict[str, Any]:
        return self.metrics.copy()


def create_insight_generator_service(
    event_bus: EventBus,
    db_pool: asyncpg.Pool,
    ai_router: AIRouter
) -> InsightGeneratorService:
    return InsightGeneratorService(event_bus, db_pool, ai_router)
