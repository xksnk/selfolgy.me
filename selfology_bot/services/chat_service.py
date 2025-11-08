"""
Simple Chat Service - AI Coach conversation handler
Integrates with existing Selfology infrastructure + Qdrant vector search
"""
import logging
import time
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
from datetime import datetime

from selfology_bot.ai.router import AIRouter, TaskComplexity
from selfology_bot.ai.clients import AIClientManager
from selfology_bot.database import DatabaseService
from selfology_bot.services.personality_service import PersonalityService
import openai
import os

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Enable DEBUG logging for this module


@dataclass
class ChatResponse:
    """Response from chat service"""
    success: bool
    message: str
    response_text: Optional[str] = None
    ai_model_used: Optional[str] = None
    processing_time: Optional[float] = None
    insights_detected: Optional[List[str]] = None
    personality_updates: Optional[Dict[str, float]] = None


class SimpleChatService:
    """
    AI Chat Service with Vector Search

    Features:
    - Uses digital personality from database for personalization
    - Stores conversation in selfology.conversations table
    - Uses AI Router for model selection
    - Detects insights from conversations
    - 🆕 Qdrant vector search for semantic context
    - 🆕 Loads personality vector for deep personalization
    """

    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
        self.ai_router = AIRouter()
        self.ai_client = AIClientManager()

        # 🆕 PersonalityService - unified access to Qdrant personality data
        self.personality_service = PersonalityService(
            qdrant_host="localhost",
            qdrant_port=6333
        )

        # OpenAI для создания embeddings из сообщений (если нужно)
        openai.api_key = os.getenv("OPENAI_API_KEY")

        logger.info("💬 Chat Service initialized with PersonalityService")

    async def start_chat_session(self, user_id: str) -> ChatResponse:
        """Start new chat session for user"""

        start_time = time.time()
        logger.info(f"💬 Starting chat session for user {user_id}")

        try:
            # Загружаем digital personality пользователя
            async with self.db_service.get_connection() as conn:
                personality = await conn.fetchrow("""
                    SELECT user_id, total_answers_analyzed, completeness_score
                    FROM selfology.digital_personality
                    WHERE user_id = $1
                """, int(user_id))

            # Формируем приветственное сообщение
            if personality and personality['total_answers_analyzed'] > 5:
                completeness = personality['completeness_score']
                welcome_text = f"""💬 <b>Добро пожаловать в AI-коуч чат!</b>

Я уже знаю вас благодаря анализу {personality['total_answers_analyzed']} ответов (профиль заполнен на {completeness:.0%}).

Можете делиться мыслями, задавать вопросы, обсуждать цели - я здесь чтобы помочь! 💚

<i>Что вас волнует сегодня?</i>"""
            else:
                welcome_text = """💬 <b>Добро пожаловать в AI-коуч чат!</b>

Я ваш персональный AI-коуч. Могу помочь:
• Разобраться в себе и своих целях
• Проработать эмоциональные состояния
• Найти решения сложных ситуаций
• Поддержать в трудные моменты

<i>О чем хотите поговорить?</i>"""

            # Сохраняем приветствие в базу
            await self._save_message(int(user_id), welcome_text, "assistant", "template")

            processing_time = time.time() - start_time

            return ChatResponse(
                success=True,
                message="Chat session started",
                response_text=welcome_text,
                ai_model_used="template",
                processing_time=processing_time
            )

        except Exception as e:
            logger.error(f"Error starting chat for user {user_id}: {e}", exc_info=True)
            return ChatResponse(
                success=False,
                message=f"Failed to start chat: {str(e)}"
            )

    async def process_message(self, user_id: str, message: str) -> ChatResponse:
        """Process user message and generate AI response"""

        start_time = time.time()
        logger.info(f"💬 Processing message from user {user_id}: {message[:50]}...")

        try:
            # Сохраняем сообщение пользователя
            await self._save_message(int(user_id), message, "user")

            # 🆕 Загружаем полный контекст через PersonalityService
            context = await self._load_full_context(int(user_id))

            # Определяем сложность задачи и выбираем модель
            router_result = self.ai_router.route_request(
                task_description="AI coaching conversation",
                message_content=message[:100]
            )

            logger.info(f"🤖 Using {router_result.model.value} for response (complexity: {router_result.complexity.value})")

            # Формируем промпт для AI
            system_prompt = self._build_system_prompt(context)
            logger.debug(f"📝 System prompt length: {len(system_prompt)} chars")
            logger.debug(f"📝 System prompt preview:\n{system_prompt[:500]}...")

            # Получаем ответ от AI
            ai_response = await self.ai_client.generate_response(
                model=router_result.model,
                messages=[{"role": "user", "content": message}],
                system_prompt=system_prompt,
                temperature=0.7,
                max_tokens=500
            )

            # Сохраняем ответ AI
            await self._save_message(
                int(user_id),
                ai_response,
                "assistant",
                router_result.model.value
            )

            # Анализируем на инсайты (простая эвристика)
            insights = self._detect_insights(message)

            processing_time = time.time() - start_time

            logger.info(f"✅ Chat response generated in {processing_time:.2f}s")

            return ChatResponse(
                success=True,
                message="Message processed",
                response_text=ai_response,
                ai_model_used=router_result.model.value,
                processing_time=processing_time,
                insights_detected=insights
            )

        except Exception as e:
            logger.error(f"Error processing message for user {user_id}: {e}", exc_info=True)
            return ChatResponse(
                success=False,
                message=f"Failed to process message: {str(e)}"
            )

    async def _load_full_context(self, user_id: int) -> Dict[str, Any]:
        """
        Load complete user context from PersonalityService + recent messages

        🆕 Clean architecture: One method, one source of truth (Qdrant)
        """

        # Load personality from Qdrant via PersonalityService
        personality_data = await self.personality_service.get_personality_for_chat(user_id)

        # Load recent conversation messages from PostgreSQL
        async with self.db_service.get_connection() as conn:
            messages = await conn.fetch("""
                SELECT content, role, created_at
                FROM selfology.conversations
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT 5
            """, user_id)

        return {
            "personality": personality_data,  # Full personality from Qdrant
            "recent_messages": [dict(m) for m in messages] if messages else []
        }

    def _build_system_prompt(self, context: Dict[str, Any]) -> str:
        """Build personalized system prompt from Qdrant personality data"""

        base_prompt = """Ты опытный AI-коуч по психологии и личностному развитию.

Твоя роль:
• Помогать людям разобраться в себе и своих целях
• Задавать проникновенные вопросы
• Давать конкретные, применимые советы
• Быть эмпатичным и поддерживающим
• Использовать научный подход к психологии

Стиль общения:
• Тёплый, человечный, неформальный
• Без излишней позитивности - будь реалистичен
• Короткие ответы (3-5 предложений)
• Используй эмодзи умеренно
"""

        # 🆕 Добавляем информацию из PersonalityService (Qdrant)
        personality = context.get("personality", {})
        if personality:
            base_prompt += "\n\n🧬 **Глубокий профиль личности пользователя:**"

            # Interests, goals, values, skills, barriers
            # Extract 'activity' field from dicts (Qdrant stores as {'status': ..., 'activity': ..., 'context': ...})
            # ВАЖНО: Учитываем status='active'/'inactive' и добавляем context для точности

            if personality.get("interests"):
                # Только активные интересы
                active_interests = [
                    item for item in personality['interests']
                    if isinstance(item, dict) and item.get('status') == 'active'
                ]
                if active_interests:
                    activities = [
                        f"{item['activity']} ({item['context']})" if item.get('context') else item['activity']
                        for item in active_interests
                    ]
                    base_prompt += f"\n• Интересы (активные): {', '.join(activities)}"

                # Прошлые интересы (inactive) - отдельно
                inactive_interests = [
                    item for item in personality['interests']
                    if isinstance(item, dict) and item.get('status') == 'inactive'
                ]
                if inactive_interests:
                    past_activities = [
                        f"{item['activity']} ({item['context']})" if item.get('context') else item['activity']
                        for item in inactive_interests
                    ]
                    base_prompt += f"\n• Интересы (в прошлом): {', '.join(past_activities)}"

            if personality.get("goals"):
                # Только активные цели
                active_goals = [
                    item for item in personality['goals']
                    if isinstance(item, dict) and item.get('status') == 'active'
                ]
                if active_goals:
                    goals = [
                        f"{item['activity']} ({item['context']})" if item.get('context') else item['activity']
                        for item in active_goals
                    ]
                    base_prompt += f"\n• Цели: {', '.join(goals)}"

            if personality.get("values"):
                values = [
                    item.get('activity', str(item)) if isinstance(item, dict) else str(item)
                    for item in personality['values']
                ]
                base_prompt += f"\n• Ценности: {', '.join(values)}"

            if personality.get("skills"):
                skills = [
                    item.get('activity', str(item)) if isinstance(item, dict) else str(item)
                    for item in personality['skills'][:5]
                ]
                base_prompt += f"\n• Навыки: {', '.join(skills)}"

            if personality.get("barriers"):
                barriers = [
                    item.get('activity', str(item)) if isinstance(item, dict) else str(item)
                    for item in personality['barriers']
                ]
                base_prompt += f"\n• Барьеры/вызовы: {', '.join(barriers)}"

            # Big Five traits
            big_five = personality.get("big_five", {})
            if big_five:
                base_prompt += "\n\n📊 **Big Five личностные черты:**"
                base_prompt += f"\n• Открытость опыту: {big_five.get('openness', 0):.0%}"
                base_prompt += f"\n• Добросовестность: {big_five.get('conscientiousness', 0):.0%}"
                base_prompt += f"\n• Экстраверсия: {big_five.get('extraversion', 0):.0%}"
                base_prompt += f"\n• Доброжелательность: {big_five.get('agreeableness', 0):.0%}"
                base_prompt += f"\n• Нейротизм: {big_five.get('neuroticism', 0):.0%}"

            # Narrative - история пользователя
            if personality.get("narrative"):
                narrative = personality["narrative"]
                # Ограничиваем длину
                if len(narrative) > 500:
                    narrative = narrative[:500] + "..."
                base_prompt += f"\n\n📖 **История пользователя:**\n{narrative}"

            # Breakthrough moments
            breakthrough_moments = personality.get("breakthrough_moments", [])
            if breakthrough_moments:
                base_prompt += "\n\n🌟 **Моменты прорыва в развитии:**"
                for moment in breakthrough_moments[:2]:
                    breakthrough = moment.get("breakthrough_info", {})
                    changes = breakthrough.get("significant_changes", [])
                    if changes:
                        base_prompt += f"\n• {', '.join(changes[:2])}"

            # Подсказка AI как использовать информацию
            base_prompt += "\n\n💡 **ВАЖНО:**"
            base_prompt += "\n• Ты ЗНАЕШЬ этого пользователя - используй всю информацию выше"
            base_prompt += "\n• Отвечай персонализированно, учитывая его интересы, цели, черты личности"
            base_prompt += "\n• Когда он просит рассказать о себе - дай конкретный анализ на основе данных выше"
            base_prompt += "\n• Не говори 'я не знаю о тебе' - ты ЗНАЕШЬ! Используй профиль личности!"

        return base_prompt

    def _detect_insights(self, message: str) -> List[str]:
        """Simple insight detection from user message"""

        insights = []
        message_lower = message.lower()

        # Паттерны инсайтов
        insight_patterns = [
            ("я понял", "realization"),
            ("оказывается", "discovery"),
            ("понимаю что", "understanding"),
            ("осознаю", "awareness")
        ]

        for pattern, insight_type in insight_patterns:
            if pattern in message_lower:
                insights.append(f"{insight_type}: {message[:100]}")

        return insights

    async def _save_message(
        self,
        user_id: int,
        content: str,
        role: str,
        model: str = None
    ):
        """Save message to conversations table"""

        try:
            async with self.db_service.get_connection() as conn:
                await conn.execute("""
                    INSERT INTO selfology.conversations
                    (user_id, content, role, ai_model, created_at)
                    VALUES ($1, $2, $3, $4, NOW())
                """, user_id, content, role, model)

            logger.debug(f"💾 Saved {role} message for user {user_id}")

        except Exception as e:
            logger.error(f"Error saving message: {e}")
            # Не падаем если сохранение не удалось

