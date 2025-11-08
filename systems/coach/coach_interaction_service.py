"""
Coach Interaction Service

Персонализированный AI коучинг с контекстом из профиля:
- Загрузка контекста пользователя из Qdrant
- Адаптивный стиль общения на основе профиля
- Сохранение истории диалогов
- Integration с AI Router для cost optimization

Architecture:
    CoachInteractionService (BaseSystem)
    ↓
    ├── ContextLoader (загрузка профиля + history из Qdrant)
    ├── StyleAdapter (адаптация стиля под личность)
    ├── ConversationManager (управление диалогами)
    └── AI Router (smart model selection)

Events consumed:
- user.message.received (chat mode)
- profile.updated (для адаптации стиля)

Events published:
- coach.message.ready (для отправки пользователю)
- insight.generated (если AI создал инсайт)
- conversation.started/ended
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
from systems.analysis.ai_router import AIRouter, AIModel, TaskComplexity

logger = logging.getLogger(__name__)


# ============================================================================
# CONTEXT LOADER
# ============================================================================

class ContextLoader:
    """
    Загрузчик контекста пользователя для персонализации

    Features:
    - Загрузка профиля из БД
    - Получение recent conversation history
    - Формирование context prompt для AI
    """

    def __init__(self, db_pool: asyncpg.Pool):
        """
        Args:
            db_pool: PostgreSQL connection pool
        """
        self.db_pool = db_pool

    async def load_user_context(
        self,
        user_id: int,
        include_history: bool = True,
        history_limit: int = 10
    ) -> Dict[str, Any]:
        """
        Загружает полный контекст пользователя

        Args:
            user_id: ID пользователя
            include_history: Загружать ли историю диалогов
            history_limit: Сколько последних сообщений включить

        Returns:
            Контекст для AI: profile + history + metadata
        """
        context = {
            "user_id": user_id,
            "profile": None,
            "conversation_history": [],
            "loaded_at": datetime.now().isoformat()
        }

        # Load profile
        async with self.db_pool.acquire() as conn:
            profile_row = await conn.fetchrow(
                """
                SELECT profile_data, updated_at
                FROM selfology.personality_profiles
                WHERE user_id = $1
                """,
                user_id
            )

            if profile_row:
                context["profile"] = {
                    "data": profile_row["profile_data"],
                    "updated_at": profile_row["updated_at"].isoformat()
                }

            # Load conversation history if requested
            if include_history:
                history_rows = await conn.fetch(
                    """
                    SELECT role, content, created_at
                    FROM selfology.conversations
                    WHERE user_id = $1
                    ORDER BY created_at DESC
                    LIMIT $2
                    """,
                    user_id,
                    history_limit
                )

                context["conversation_history"] = [
                    {
                        "role": row["role"],
                        "content": row["content"],
                        "timestamp": row["created_at"].isoformat()
                    }
                    for row in reversed(history_rows)  # Chronological order
                ]

        return context

    def build_system_prompt(self, context: Dict[str, Any]) -> str:
        """
        Формирует system prompt для AI на основе контекста

        Args:
            context: User context from load_user_context

        Returns:
            System prompt для AI
        """
        profile_data = context.get("profile", {}).get("data", {})
        big_five = profile_data.get("big_five", {})

        # Extract key traits
        openness = big_five.get("openness", {}).get("value", 0.5)
        conscientiousness = big_five.get("conscientiousness", {}).get("value", 0.5)
        extraversion = big_five.get("extraversion", {}).get("value", 0.5)

        # Build personalized prompt
        prompt = f"""Ты - персональный психологический коуч пользователя в приложении Selfology.

ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ:
- Открытость опыту: {openness:.2f} (0-1)
- Добросовестность: {conscientiousness:.2f} (0-1)
- Экстраверсия: {extraversion:.2f} (0-1)

СТИЛЬ ОБЩЕНИЯ:
"""

        # Adapt style based on traits
        if openness > 0.6:
            prompt += "- Пользователь открыт новым идеям - используй креативные метафоры и нестандартные подходы\n"
        else:
            prompt += "- Пользователь предпочитает практичность - фокусируйся на конкретных действиях\n"

        if conscientiousness > 0.6:
            prompt += "- Пользователь организован - предлагай структурированные планы\n"
        else:
            prompt += "- Пользователь спонтанен - оставь место для гибкости\n"

        if extraversion > 0.6:
            prompt += "- Пользователь энергичен - используй живой, вдохновляющий тон\n"
        else:
            prompt += "- Пользователь интроверт - говори спокойно, давай время на размышление\n"

        prompt += """
ТВОЯ ЗАДАЧА:
- Слушай внимательно и задавай глубокие вопросы
- Помогай осознать паттерны поведения
- Поддерживай рост и развитие
- Будь эмпатичным и безоценочным

ФОРМАТ ОТВЕТА:
- Короткие параграфы (2-3 предложения)
- Используй эмодзи умеренно
- Один главный вопрос в конце (если уместно)
"""

        return prompt


# ============================================================================
# STYLE ADAPTER
# ============================================================================

class StyleAdapter:
    """
    Адаптер стиля общения на основе профиля

    Features:
    - Динамическая адаптация tone/formality
    - Vocabulary complexity adjustment
    - Emoji usage personalization
    """

    def __init__(self):
        pass

    def adapt_response(
        self,
        ai_response: str,
        profile_data: Dict[str, Any]
    ) -> str:
        """
        Адаптирует AI ответ под стиль пользователя

        Args:
            ai_response: Оригинальный ответ от AI
            profile_data: Профиль пользователя

        Returns:
            Адаптированный ответ
        """
        # For now, return as-is (AI Router уже учитывает контекст)
        # В будущем: post-processing для дополнительной персонализации
        return ai_response


# ============================================================================
# CONVERSATION MANAGER
# ============================================================================

class ConversationManager:
    """
    Управление диалогами и их сохранение

    Features:
    - Сохранение истории в БД
    - Tracking conversation metrics
    - Session management
    """

    def __init__(self, db_pool: asyncpg.Pool):
        """
        Args:
            db_pool: PostgreSQL connection pool
        """
        self.db_pool = db_pool

    async def save_message(
        self,
        user_id: int,
        role: str,
        content: str
    ) -> int:
        """
        Сохраняет сообщение в историю диалогов

        Args:
            user_id: ID пользователя
            role: "user" или "assistant"
            content: Текст сообщения

        Returns:
            ID сохраненного сообщения
        """
        async with self.db_pool.acquire() as conn:
            message_id = await conn.fetchval(
                """
                INSERT INTO selfology.conversations (user_id, role, content)
                VALUES ($1, $2, $3)
                RETURNING id
                """,
                user_id,
                role,
                content
            )

        logger.info(f"Saved {role} message for user {user_id}")
        return message_id

    async def get_conversation_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Получает статистику диалогов пользователя

        Args:
            user_id: ID пользователя

        Returns:
            Статистика: total_messages, avg_length, etc.
        """
        async with self.db_pool.acquire() as conn:
            stats = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) as total_messages,
                    AVG(LENGTH(content)) as avg_message_length,
                    MAX(created_at) as last_interaction
                FROM selfology.conversations
                WHERE user_id = $1
                """,
                user_id
            )

        return {
            "total_messages": stats["total_messages"],
            "avg_message_length": int(stats["avg_message_length"]) if stats["avg_message_length"] else 0,
            "last_interaction": stats["last_interaction"].isoformat() if stats["last_interaction"] else None
        }


# ============================================================================
# COACH INTERACTION SERVICE
# ============================================================================

class CoachInteractionService(BaseSystem):
    """
    Coach Interaction Service - персонализированный AI коучинг

    Features:
    - Загрузка контекста из профиля
    - Адаптивный стиль общения
    - Сохранение истории диалогов
    - Smart AI routing для cost optimization
    """

    def __init__(
        self,
        event_bus: EventBus,
        db_pool: asyncpg.Pool,
        ai_router: AIRouter
    ):
        """
        Args:
            event_bus: Event Bus instance
            db_pool: PostgreSQL connection pool
            ai_router: AI Router для вызовов AI
        """
        super().__init__(
            name="coach_interaction_service",
            event_bus=event_bus
        )

        self.db_pool = db_pool
        self.ai_router = ai_router

        # Components
        self.context_loader = ContextLoader(db_pool)
        self.style_adapter = StyleAdapter()
        self.conversation_manager = ConversationManager(db_pool)

        # Metrics
        self.metrics = {
            "conversations_handled": 0,
            "messages_processed": 0,
            "ai_calls": 0,
            "insights_generated": 0,
            "errors": 0
        }

    async def start(self):
        """Запускает сервис"""
        await super().start()

        # Subscribe to events
        await self.event_bus.subscribe(
            event_type="user.message.received",
            consumer_group="coach_interaction",
            handler=self._handle_user_message
        )

        await self.event_bus.subscribe(
            event_type="profile.updated",
            consumer_group="coach_interaction",
            handler=self._handle_profile_updated
        )

        logger.info(f"✅ {self.name} started and subscribed to events")

    async def _handle_user_message(self, event: Dict[str, Any]):
        """
        Обрабатывает сообщение пользователя в режиме чата

        Event payload:
        {
            "user_id": int,
            "message_text": str,
            "current_state": str
        }
        """
        try:
            payload = event["payload"]
            user_id = payload["user_id"]
            message_text = payload["message_text"]
            current_state = payload.get("current_state")

            # Only process in chat mode
            if current_state not in ["chat_active", "onboarding_complete"]:
                logger.debug(f"Skipping message from user {user_id} in state {current_state}")
                return

            logger.info(f"Processing chat message from user {user_id}")

            # Save user message
            await self.conversation_manager.save_message(
                user_id=user_id,
                role="user",
                content=message_text
            )

            # Load user context
            context = await self.context_loader.load_user_context(
                user_id=user_id,
                include_history=True,
                history_limit=10
            )

            # Build system prompt
            system_prompt = self.context_loader.build_system_prompt(context)

            # Prepare messages for AI
            messages = [
                {"role": "system", "content": system_prompt}
            ]

            # Add conversation history
            for msg in context["conversation_history"]:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

            # Add current user message
            messages.append({
                "role": "user",
                "content": message_text
            })

            # Call AI (using GPT-4o for coaching - medium complexity)
            self.metrics["ai_calls"] += 1
            ai_result = await self.ai_router.call_ai(
                model=AIModel.GPT4O,
                messages=messages,
                max_tokens=500,
                temperature=0.8,  # More creative for coaching
                allow_fallback=True
            )

            coach_response = ai_result["content"]

            # Adapt style (future enhancement)
            adapted_response = self.style_adapter.adapt_response(
                coach_response,
                context.get("profile", {}).get("data", {})
            )

            # Save assistant message
            await self.conversation_manager.save_message(
                user_id=user_id,
                role="assistant",
                content=adapted_response
            )

            self.metrics["messages_processed"] += 1
            self.metrics["conversations_handled"] += 1

            # Publish response event
            async with self.db_pool.acquire() as conn:
                async with conn.transaction():
                    outbox_publisher = OutboxPublisher(schema="selfology")
                    await outbox_publisher.publish(
                        conn,
                        "coach.message.ready",
                        {
                            "user_id": user_id,
                            "message_text": adapted_response,
                            "model_used": ai_result["model"],
                            "tokens_used": ai_result["tokens_used"],
                            "cost_usd": ai_result["cost_usd"],
                            "timestamp": datetime.now().isoformat()
                        },
                        trace_id=event.get("trace_id")
                    )

            logger.info(f"✅ Sent coach response to user {user_id} (model: {ai_result['model']})")

        except Exception as e:
            logger.error(f"Failed to handle user message: {e}", exc_info=True)
            self.metrics["errors"] += 1
            raise

    async def _handle_profile_updated(self, event: Dict[str, Any]):
        """
        Обрабатывает обновление профиля для адаптации стиля

        Event payload:
        {
            "user_id": int,
            "traits_updated": list
        }
        """
        try:
            payload = event["payload"]
            user_id = payload["user_id"]

            logger.info(f"Profile updated for user {user_id}, style will adapt on next interaction")

            # No immediate action needed - context будет загружен на следующем сообщении

        except Exception as e:
            logger.error(f"Failed to handle profile update: {e}", exc_info=True)

    async def health_check(self) -> Dict[str, Any]:
        """Проверяет здоровье сервиса"""
        health = await super().health_check()

        # Check database
        db_healthy = False
        try:
            async with self.db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            db_healthy = True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")

        # Check AI Router
        ai_router_health = self.ai_router.get_health_status()

        health.update({
            "database": "healthy" if db_healthy else "unhealthy",
            "ai_router": ai_router_health,
            "metrics": self.metrics
        })

        if not db_healthy or ai_router_health == "unhealthy":
            health["status"] = "unhealthy"
        elif ai_router_health == "degraded":
            health["status"] = "degraded"

        return health

    def get_metrics(self) -> Dict[str, Any]:
        """Возвращает метрики сервиса"""
        ai_router_metrics = self.ai_router.get_metrics()

        return {
            **self.metrics,
            "ai_router_metrics": ai_router_metrics
        }


# ============================================================================
# FACTORY
# ============================================================================

def create_coach_interaction_service(
    event_bus: EventBus,
    db_pool: asyncpg.Pool,
    ai_router: AIRouter
) -> CoachInteractionService:
    """
    Factory для создания Coach Interaction Service

    Args:
        event_bus: Event Bus instance
        db_pool: PostgreSQL connection pool
        ai_router: AI Router instance

    Returns:
        Configured CoachInteractionService instance
    """
    return CoachInteractionService(
        event_bus=event_bus,
        db_pool=db_pool,
        ai_router=ai_router
    )
