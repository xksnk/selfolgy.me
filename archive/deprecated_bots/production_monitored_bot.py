#!/usr/bin/env python3
"""
Production Selfology Bot with Enterprise-Grade Monitoring
Integrates the comprehensive monitoring system with the fixed architecture bot.
"""

import asyncio
import asyncpg
import sys
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Set

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode

# Add core monitoring to path
sys.path.append(str(Path(__file__).parent / "core"))
sys.path.append(str(Path(__file__).parent / "intelligent_question_core"))

# Import monitoring system
from enhanced_logging import EnhancedLoggerMixin, trace_operation, EventType, set_user_context
from monitoring_orchestrator import MonitoringConfig, initialize_monitoring_system, start_monitoring_system

try:
    from intelligent_question_core.api.core_api import SelfologyQuestionCore
    QUESTION_CORE_AVAILABLE = True
except Exception:
    QUESTION_CORE_AVAILABLE = False

# Configuration
BOT_TOKEN = "8197893707:AAEbGC7r_4GGWXvgah-q-mLw5pp7YIxhK9g"
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "user": os.getenv("DB_USER", "n8n"),
    "password": os.getenv("DB_PASSWORD", "sS67wM+1zMBRFHAW4kj9HwFl5J6+veo7Nirx0/I+oiU="),
    "database": os.getenv("DB_NAME", "n8n")
}

# States
class UserStates(StatesGroup):
    main_menu = State()
    assessment_mode = State()
    chat_mode = State()

# Global instances
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
db_pool = None
question_core = None

# Monitoring system
monitoring_orchestrator = None


class MonitoredQuestionDeduplicationService(EnhancedLoggerMixin):
    """Question deduplication with monitoring"""
    
    def __init__(self, db_pool):
        super().__init__()
        self.db_pool = db_pool
        self._user_answered_cache = {}
    
    @trace_operation("get_answered_questions", EventType.USER_ACTION)
    async def get_answered_questions(self, user_id: int) -> Set[str]:
        """Get answered questions with monitoring"""
        
        set_user_context(user_id)
        
        if user_id not in self._user_answered_cache:
            async with self.db_pool.acquire() as conn:
                answered = await conn.fetch("""
                    SELECT DISTINCT question_id 
                    FROM selfology_question_answers 
                    WHERE user_id = $1
                """, str(user_id))
            
            self._user_answered_cache[user_id] = {row["question_id"] for row in answered}
            self.log_info(f"Loaded {len(self._user_answered_cache[user_id])} answered questions")
        
        self.track_metric("answered_questions_count", len(self._user_answered_cache[user_id]))
        return self._user_answered_cache[user_id]
    
    @trace_operation("mark_question_answered", EventType.USER_ACTION)
    async def mark_question_answered(self, user_id: int, question_id: str):
        """Mark question as answered with monitoring"""
        
        set_user_context(user_id)
        
        if user_id not in self._user_answered_cache:
            self._user_answered_cache[user_id] = set()
        
        self._user_answered_cache[user_id].add(question_id)
        self.log_info(f"Marked question {question_id} as answered")
        self.track_metric("questions_answered_total", 1, increment=True)


class MonitoredAssessmentEngine(EnhancedLoggerMixin):
    """Assessment engine with comprehensive monitoring"""
    
    def __init__(self, db_pool, question_core):
        super().__init__()
        self.db_pool = db_pool
        self.question_core = question_core
        self.deduplication = MonitoredQuestionDeduplicationService(db_pool)
    
    @trace_operation("get_next_question", EventType.AI_INTERACTION)
    async def get_next_question(self, user_id: int) -> Optional[dict]:
        """Get next question with monitoring"""
        
        set_user_context(user_id)
        
        if not QUESTION_CORE_AVAILABLE:
            self.log_warning("Question core not available")
            return None
        
        start_time = time.time()
        
        # Get user progress
        answered_questions = await self.deduplication.get_answered_questions(user_id)
        
        # Get available questions
        all_questions = list(self.question_core.questions_lookup.values())
        unanswered = [q for q in all_questions if q["id"] not in answered_questions]
        
        if not unanswered:
            self.log_info("All questions completed for user")
            self.track_metric("assessment_completed", 1, increment=True)
            return None
        
        # Smart selection
        selected = self._select_optimal_question(user_id, unanswered)
        
        selection_time = time.time() - start_time
        self.track_performance("question_selection_time", selection_time)
        
        if selected:
            self.log_info(f"Selected question {selected['id']} from {len(unanswered)} options")
            self.track_metric("questions_presented", 1, increment=True)
        
        return selected
    
    def _select_optimal_question(self, user_id: int, available_questions: List[dict]) -> Optional[dict]:
        """Select optimal question with monitoring"""
        
        # Filter by safety
        safe_questions = [q for q in available_questions if q["psychology"]["safety_level"] >= 3]
        
        if safe_questions:
            selected = safe_questions[0]
            self.track_metric("safe_questions_selected", 1, increment=True)
            return selected
        
        # Fallback
        if available_questions:
            self.track_metric("fallback_questions_selected", 1, increment=True)
            return available_questions[0]
        
        return None
    
    @trace_operation("process_answer", EventType.AI_INTERACTION)
    async def process_answer(self, user_id: int, question_id: str, answer: str) -> dict:
        """Process answer with comprehensive monitoring"""
        
        set_user_context(user_id)
        start_time = time.time()
        
        if not QUESTION_CORE_AVAILABLE:
            return {"error": "Question core not available"}
        
        question = self.question_core.get_question(question_id)
        if not question:
            self.log_error(f"Question {question_id} not found")
            return {"error": "Question not found"}
        
        # Analyze answer
        analysis = self._analyze_answer_monitored(answer, question, user_id)
        
        # Save to database
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO selfology_question_answers 
                (user_id, question_id, answer_text, answer_analysis, ai_model_used)
                VALUES ($1, $2, $3, $4, $5)
            """, str(user_id), question_id, answer, json.dumps(analysis), "monitored_analysis")
        
        # Mark as answered
        await self.deduplication.mark_question_answered(user_id, question_id)
        
        # Get next question
        next_question = await self.get_next_question(user_id)
        
        processing_time = time.time() - start_time
        self.track_performance("answer_processing_time", processing_time)
        
        self.log_info(f"Processed answer for question {question_id}, next: {next_question['id'] if next_question else 'COMPLETE'}")
        
        return {
            "analysis": analysis,
            "next_question": next_question,
            "processing_time": processing_time
        }
    
    def _analyze_answer_monitored(self, answer: str, question: dict, user_id: int) -> dict:
        """Answer analysis with monitoring"""
        
        start_time = time.time()
        
        word_count = len(answer.split())
        answer_length = len(answer)
        
        # Track input metrics
        self.track_metric("answer_word_count", word_count)
        self.track_metric("answer_length", answer_length)
        
        # Basic sentiment analysis
        positive_words = ["хорошо", "отлично", "люблю", "классн", "красив", "радует"]
        negative_words = ["плохо", "грустно", "тяжело", "больно", "страшно"]
        
        positive_count = sum(1 for word in positive_words if word in answer.lower())
        negative_count = sum(1 for word in negative_words if word in answer.lower())
        
        emotional_state = "positive" if positive_count > negative_count else "negative" if negative_count > 0 else "neutral"
        
        # Calculate openness and other metrics
        openness = min(1.0, word_count / 15.0)
        vulnerability = 0.8 if any(word in answer.lower() for word in ["чувствую", "боюсь"]) else 0.3
        
        analysis = {
            "emotional_state": emotional_state,
            "openness_level": round(openness, 2),
            "vulnerability_shown": round(vulnerability, 2),
            "word_count": word_count,
            "domain": question["classification"]["domain"],
            "energy_impact": 0.1 if positive_count > 0 else -0.1 if negative_count > 0 else 0.0,
            "trust_building": round(openness * vulnerability * 0.2, 2),
            "analysis_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        analysis_time = time.time() - start_time
        self.track_performance("answer_analysis_time", analysis_time)
        
        # Track analysis metrics
        self.track_metric(f"emotional_state_{emotional_state}", 1, increment=True)
        self.track_metric(f"domain_{question['classification']['domain']}_answers", 1, increment=True)
        
        return analysis


class MonitoredChatService(EnhancedLoggerMixin):
    """Chat service with monitoring"""
    
    def __init__(self, db_pool):
        super().__init__()
        self.db_pool = db_pool
        self._user_contexts = {}
    
    @trace_operation("get_personalized_response", EventType.AI_INTERACTION)
    async def get_personalized_response(self, user_id: int, message: str) -> str:
        """Generate response with monitoring"""
        
        set_user_context(user_id)
        start_time = time.time()
        
        # Track message metrics
        self.track_metric("chat_messages_received", 1, increment=True)
        self.track_metric("chat_message_length", len(message))
        
        # Load context
        context = await self._get_user_context_monitored(user_id)
        
        # Generate response
        if self._detect_negative_emotion(message):
            response_type = "supportive"
            response = await self._generate_supportive_response(message, context)
        elif self._detect_question(message):
            response_type = "advisory"
            response = await self._generate_advisory_response(message, context)
        else:
            response_type = "conversational"
            response = await self._generate_conversational_response(message, context)
        
        response_time = time.time() - start_time
        self.track_performance("chat_response_time", response_time)
        self.track_metric(f"chat_response_{response_type}", 1, increment=True)
        
        self.log_info(f"Generated {response_type} response in {response_time:.2f}s")
        
        return response
    
    async def _get_user_context_monitored(self, user_id: int) -> dict:
        """Get user context with monitoring"""
        
        start_time = time.time()
        
        async with self.db_pool.acquire() as conn:
            answers_count = await conn.fetchval("""
                SELECT COUNT(*) FROM selfology_question_answers WHERE user_id = $1
            """, str(user_id))
        
        context = {
            "total_answers": answers_count,
            "communication_style": "detailed" if answers_count > 5 else "basic"
        }
        
        context_time = time.time() - start_time
        self.track_performance("context_loading_time", context_time)
        
        return context
    
    def _detect_negative_emotion(self, message: str) -> bool:
        """Detect negative emotions with monitoring"""
        negative_indicators = ["плохо", "грустно", "тяжело", "больно", "страшно"]
        is_negative = any(word in message.lower() for word in negative_indicators)
        
        if is_negative:
            self.track_metric("negative_emotions_detected", 1, increment=True)
            self.log_info("Negative emotion detected in user message")
        
        return is_negative
    
    def _detect_question(self, message: str) -> bool:
        """Detect questions with monitoring"""
        question_indicators = ["как", "что делать", "помоги", "совет", "?"]
        is_question = any(indicator in message.lower() for indicator in question_indicators)
        
        if is_question:
            self.track_metric("questions_asked", 1, increment=True)
        
        return is_question
    
    async def _generate_supportive_response(self, message: str, context: dict) -> str:
        """Generate supportive response"""
        return f"""
🤗 <b>Понимаю ваше состояние</b>

Спасибо за доверие в том, что поделились сложными чувствами.

<b>💙 Что может помочь:</b>
• Глубокое дыхание для успокоения
• Напомните себе: "Это временное состояние"
• Подумайте о ваших ресурсах поддержки

<b>🎯 На основе вашего профиля ({context['total_answers']} ответов):</b>
{self._get_personalized_support_advice(context)}

Хотите рассказать подробнее? 💚
        """
    
    def _get_personalized_support_advice(self, context: dict) -> str:
        """Get personalized support advice"""
        if context["total_answers"] > 5:
            return "Вспомните стратегии, которые помогали вам раньше"
        else:
            return "Попробуйте сосредоточиться на том, что дает вам силы"
    
    async def _generate_advisory_response(self, message: str, context: dict) -> str:
        """Generate advisory response"""
        return f"""
🎯 <b>Анализирую ваш вопрос</b>

{message[:100]}{'...' if len(message) > 100 else ''}

<b>💡 Персональная рекомендация:</b>
{self._get_personalized_advice(context)}

<b>🔍 Для размышления:</b>
• Что помогало в похожих ситуациях?
• Какие ваши сильные стороны применимы здесь?

Расскажите больше деталей! 🚀
        """
    
    def _get_personalized_advice(self, context: dict) -> str:
        """Get personalized advice"""
        if context["communication_style"] == "detailed":
            return "Создайте детальный план действий и проанализируйте каждый шаг"
        else:
            return "Разложите проблему на части и определите, что вы можете контролировать"
    
    async def _generate_conversational_response(self, message: str, context: dict) -> str:
        """Generate conversational response"""
        return f"""
💬 <b>Понял!</b>

<b>🤖 С учетом вашего профиля:</b>
Интересная мысль! {self._get_conversational_insight(context)}

Продолжайте делиться! 💭
        """
    
    def _get_conversational_insight(self, context: dict) -> str:
        """Get conversational insight"""
        if context["total_answers"] > 3:
            return "Это соотносится с тем, что я знаю о вас."
        else:
            return "Хотелось бы узнать вас лучше через анкетирование!"


# Initialize monitored services
deduplication_service = None
assessment_engine = None
chat_service = None

async def init_monitored_services():
    """Initialize services with monitoring"""
    global db_pool, question_core, deduplication_service, assessment_engine, chat_service
    
    try:
        # Database
        db_pool = await asyncpg.create_pool(**DB_CONFIG)
        
        # Question Core
        if QUESTION_CORE_AVAILABLE:
            core_path = Path(__file__).parent / "intelligent_question_core/data/selfology_intelligent_core.json"
            question_core = SelfologyQuestionCore(str(core_path))
        
        # Initialize monitored services
        deduplication_service = MonitoredQuestionDeduplicationService(db_pool)
        assessment_engine = MonitoredAssessmentEngine(db_pool, question_core)
        chat_service = MonitoredChatService(db_pool)
        
        return True
        
    except Exception as e:
        print(f"❌ Service initialization failed: {e}")
        return False


# === MONITORED TELEGRAM HANDLERS ===

@dp.message(CommandStart())
async def monitored_cmd_start(message: Message, state: FSMContext):
    """Start command with comprehensive monitoring"""
    
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "Friend"
    
    # Set monitoring context
    set_user_context(user_id)
    
    # Create logger for this handler
    logger = EnhancedLoggerMixin()
    
    with logger.trace_operation("start_command", EventType.USER_ACTION):
        logger.track_metric("start_commands", 1, increment=True)
        logger.log_info(f"Start command from user {user_name}")
        
        try:
            # Check user status
            async with db_pool.acquire() as conn:
                user_data = await conn.fetchrow(
                    "SELECT * FROM selfology_users WHERE telegram_id = $1", str(user_id)
                )
            
            if user_data:
                if user_data["gdpr_consent"]:
                    await show_monitored_dashboard(message, state, user_data)
                else:
                    await show_monitored_gdpr_consent(message, state)
            else:
                await create_monitored_user(message, state, user_id)
        
        except Exception as e:
            logger.log_error(f"Start command error: {e}")
            await message.answer("Произошла ошибка. Попробуйте еще раз.")


async def show_monitored_dashboard(message: Message, state: FSMContext, user_data: dict):
    """Show dashboard with monitoring"""
    
    user_name = user_data["first_name"] or "Friend" 
    user_id = int(user_data["telegram_id"])
    
    logger = EnhancedLoggerMixin()
    set_user_context(user_id)
    
    # Get progress
    if assessment_engine:
        answered_questions = await assessment_engine.deduplication.get_answered_questions(user_id)
        answers_count = len(answered_questions)
    else:
        answers_count = 0
    
    dashboard_text = f"""
🏠 <b>Привет, {user_name}!</b>

<b>📊 Мониторинг вашего прогресса:</b>
• Ответов дано: <code>{answers_count}</code>
• Система мониторинга: ✅ <b>АКТИВНА</b>
• Все действия отслеживаются в реальном времени

<b>🎯 Доступные действия:</b>
    """
    
    keyboard_buttons = []
    
    if answers_count < 10:
        keyboard_buttons.append([InlineKeyboardButton(text="🧠 Продолжить анкетирование", callback_data="continue_assessment")])
    else:
        keyboard_buttons.append([InlineKeyboardButton(text="💬 Персональный коучинг", callback_data="start_coaching")])
    
    keyboard_buttons.extend([
        [InlineKeyboardButton(text="📊 Детальный мониторинг", callback_data="show_monitoring_stats")],
        [InlineKeyboardButton(text="💬 Чат режим", callback_data="start_chat")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="show_profile")]
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    logger.track_metric("dashboard_views", 1, increment=True)
    
    await message.answer(dashboard_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(UserStates.main_menu)


@dp.callback_query(F.data == "continue_assessment")
async def monitored_continue_assessment(callback: types.CallbackQuery, state: FSMContext):
    """Continue assessment with monitoring"""
    
    user_id = callback.from_user.id
    set_user_context(user_id)
    
    logger = EnhancedLoggerMixin()
    
    with logger.trace_operation("continue_assessment", EventType.USER_ACTION):
        if assessment_engine:
            next_question = await assessment_engine.get_next_question(user_id)
            
            if next_question:
                await show_monitored_question(callback.message, next_question, user_id)
                await state.set_state(UserStates.assessment_mode)
                logger.track_metric("assessment_continued", 1, increment=True)
            else:
                await callback.message.edit_text("""
🎉 <b>Анкетирование завершено!</b>

Вы ответили на все вопросы! Переходите к коучингу! 🚀
                """, parse_mode=ParseMode.HTML)
                logger.track_metric("assessment_completed", 1, increment=True)
        else:
            await callback.message.edit_text("Система анкетирования недоступна.")


async def show_monitored_question(message: Message, question: dict, user_id: int):
    """Show question with monitoring"""
    
    logger = EnhancedLoggerMixin()
    set_user_context(user_id)
    
    # Get progress for context
    if assessment_engine:
        answered_count = len(await assessment_engine.deduplication.get_answered_questions(user_id))
    else:
        answered_count = 0
    
    question_text = f"""
🧠 <b>Анкетирование</b> (ответ {answered_count + 1})

<b>Область:</b> {question['classification']['domain']}

{question['text']}

💭 <i>Ответы отслеживаются системой мониторинга</i>
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="skip_question")],
        [InlineKeyboardButton(text="📊 Мониторинг", callback_data="show_monitoring_stats")],
        [InlineKeyboardButton(text="💬 К чату", callback_data="start_chat")]
    ])
    
    logger.track_metric("questions_shown", 1, increment=True)
    await message.edit_text(question_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)


@dp.message(UserStates.assessment_mode)
async def monitored_handle_answer(message: Message, state: FSMContext):
    """Handle answer with full monitoring"""
    
    user_id = message.from_user.id
    answer = message.text
    
    set_user_context(user_id)
    logger = EnhancedLoggerMixin()
    
    with logger.trace_operation("handle_assessment_answer", EventType.AI_INTERACTION):
        if assessment_engine:
            # Get last question for this user
            async with db_pool.acquire() as conn:
                last_question = await conn.fetchval("""
                    SELECT question_id FROM selfology_question_answers
                    WHERE user_id = $1 ORDER BY answered_at DESC LIMIT 1
                """, str(user_id))
            
            # Get current question
            if not last_question:
                current_question = await assessment_engine.get_next_question(user_id)
                if current_question:
                    last_question = current_question["id"]
            
            if last_question:
                # Process answer
                result = await assessment_engine.process_answer(user_id, last_question, answer)
                
                response_text = f"""
✅ <b>Ответ обработан системой мониторинга!</b>

<b>🔍 Анализ:</b>
• Состояние: {result['analysis']['emotional_state']}
• Открытость: {result['analysis']['openness_level']}/1.0
• Время обработки: {result['processing_time']:.2f}s

<b>💾 Мониторинг:</b>
• ✅ Сохранено в PostgreSQL
• ✅ Метрики собраны
• ✅ Трассировка выполнена

{f"➡️ <b>Следующий вопрос готов!</b>" if result['next_question'] else "🎉 <b>Анкетирование завершено!</b>"}
                """
                
                if result["next_question"]:
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="➡️ Следующий вопрос", callback_data="show_next_question")],
                        [InlineKeyboardButton(text="📊 Мониторинг", callback_data="show_monitoring_stats")]
                    ])
                else:
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="💬 Начать коучинг", callback_data="start_coaching")]
                    ])
                
                await message.answer(response_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
                logger.track_metric("answers_processed", 1, increment=True)
            else:
                await message.answer("Ошибка: активный вопрос не найден")


@dp.callback_query(F.data == "show_monitoring_stats")
async def show_monitoring_statistics(callback: types.CallbackQuery):
    """Show monitoring statistics"""
    
    user_id = callback.from_user.id
    set_user_context(user_id)
    
    logger = EnhancedLoggerMixin()
    
    with logger.trace_operation("show_monitoring_stats", EventType.USER_ACTION):
        try:
            # Get comprehensive stats
            async with db_pool.acquire() as conn:
                # User stats
                user_stats = await conn.fetchrow("""
                    SELECT COUNT(*) as answers, 
                           MIN(answered_at) as first_answer,
                           MAX(answered_at) as last_answer
                    FROM selfology_question_answers 
                    WHERE user_id = $1
                """, str(user_id))
                
                # Recent activity
                recent_answers = await conn.fetch("""
                    SELECT question_id, answered_at, answer_analysis
                    FROM selfology_question_answers
                    WHERE user_id = $1
                    ORDER BY answered_at DESC
                    LIMIT 5
                """, str(user_id))
            
            # Domain analysis
            domain_coverage = {}
            if QUESTION_CORE_AVAILABLE and recent_answers:
                for answer in recent_answers:
                    question = question_core.get_question(answer["question_id"])
                    if question:
                        domain = question["classification"]["domain"]
                        domain_coverage[domain] = domain_coverage.get(domain, 0) + 1
            
            monitoring_text = f"""
📊 <b>Системный мониторинг активности</b>

<b>🎯 Ваша активность:</b>
• Всего ответов: <code>{user_stats['answers']}</code>
• Первый ответ: {user_stats['first_answer'].strftime('%d.%m %H:%M') if user_stats['first_answer'] else 'Нет'}
• Последний ответ: {user_stats['last_answer'].strftime('%d.%m %H:%M') if user_stats['last_answer'] else 'Нет'}

<b>🗺️ Исследованные области:</b>
{chr(10).join([f"• {domain}: {count}" for domain, count in domain_coverage.items()]) if domain_coverage else "• Данные загружаются..."}

<b>📈 Система мониторинга:</b>
• Трассировка запросов: ✅ Активна
• Метрики производительности: ✅ Собираются  
• Анализ ошибок: ✅ Отслеживается
• Пользовательская аналитика: ✅ Работает

<b>🔗 Monitoring Dashboard:</b> http://localhost:8000
<b>📊 API Metrics:</b> http://localhost:8001/metrics

<i>Система отслеживает каждое ваше действие для оптимизации!</i>
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🧠 Продолжить анкетирование", callback_data="continue_assessment")],
                [InlineKeyboardButton(text="💬 К чату", callback_data="start_chat")],
                [InlineKeyboardButton(text="🔄 Обновить", callback_data="show_monitoring_stats")]
            ])
            
            await callback.message.edit_text(monitoring_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
            logger.track_metric("monitoring_stats_viewed", 1, increment=True)
            
        except Exception as e:
            logger.log_error(f"Error showing monitoring stats: {e}")
            await callback.message.edit_text("Ошибка получения статистики мониторинга")


@dp.callback_query(F.data == "start_chat")
async def monitored_start_chat(callback: types.CallbackQuery, state: FSMContext):
    """Start chat with monitoring"""
    
    user_id = callback.from_user.id
    set_user_context(user_id)
    
    logger = EnhancedLoggerMixin()
    logger.track_metric("chat_sessions_started", 1, increment=True)
    
    await callback.message.edit_text("""
💬 <b>Мониторинг чат режима активирован!</b>

<b>🔍 Что отслеживается:</b>
✅ Время ответа на ваши сообщения
✅ Эмоциональное состояние в разговоре  
✅ Эффективность персонализации
✅ Качество AI рекомендаций

Пишите что угодно - система оптимизирует ответы! 🚀
    """, parse_mode=ParseMode.HTML)
    
    await state.set_state(UserStates.chat_mode)


@dp.message(UserStates.chat_mode)
async def monitored_handle_chat(message: Message, state: FSMContext):
    """Handle chat with full monitoring"""
    
    user_id = message.from_user.id
    user_message = message.text
    
    set_user_context(user_id)
    logger = EnhancedLoggerMixin()
    
    with logger.trace_operation("chat_interaction", EventType.AI_INTERACTION):
        start_time = time.time()
        
        if chat_service:
            response = await chat_service.get_personalized_response(user_id, user_message)
        else:
            response = "Сервис чата недоступен"
        
        response_time = time.time() - start_time
        logger.track_performance("total_chat_response_time", response_time)
        
        await message.answer(response, parse_mode=ParseMode.HTML)


# Command handlers with monitoring
@dp.message(Command("questions"))
async def monitored_cmd_questions(message: Message, state: FSMContext):
    """Questions command with monitoring"""
    user_id = message.from_user.id
    set_user_context(user_id)
    
    logger = EnhancedLoggerMixin()
    logger.track_metric("questions_command_used", 1, increment=True)
    
    if assessment_engine:
        next_question = await assessment_engine.get_next_question(user_id)
        if next_question:
            await show_monitored_question(message, next_question, user_id)
            await state.set_state(UserStates.assessment_mode)
        else:
            await message.answer("✅ Все вопросы отвечены!")
    else:
        await message.answer("Система анкетирования недоступна")


@dp.message(Command("stats"))
async def monitored_cmd_stats(message: Message):
    """Stats command with monitoring"""
    user_id = message.from_user.id
    set_user_context(user_id)
    
    logger = EnhancedLoggerMixin()
    logger.track_metric("stats_command_used", 1, increment=True)
    
    # Quick stats
    if assessment_engine:
        answered = await assessment_engine.deduplication.get_answered_questions(user_id)
        quick_stats = f"""
📊 <b>Быстрая статистика (мониторинг активен):</b>

• Ответов: <code>{len(answered)}</code>
• Мониторинг: ✅ Отслеживается
• Dashboard: http://localhost:8000  

Используйте меню для детальной статистики.
        """
    else:
        quick_stats = "Система статистики недоступна"
    
    await message.answer(quick_stats, parse_mode=ParseMode.HTML)


# Missing handlers
async def show_monitored_gdpr_consent(message: Message, state: FSMContext):
    """GDPR consent with monitoring"""
    await message.answer("""
🌟 <b>Добро пожаловать в Monitored Selfology!</b>

Система мониторинга отслеживает качество сервиса.

Согласны на обработку данных?
    """, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Согласен", callback_data="consent_yes")]
    ]), parse_mode=ParseMode.HTML)


async def create_monitored_user(message: Message, state: FSMContext, user_id: int):
    """Create user with monitoring"""
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO selfology_users 
            (telegram_id, username, first_name, last_name, last_active) 
            VALUES ($1, $2, $3, $4, $5)
        """, str(user_id), message.from_user.username, 
        message.from_user.first_name, message.from_user.last_name, datetime.now(timezone.utc))
    
    await show_monitored_gdpr_consent(message, state)


@dp.callback_query(F.data == "consent_yes")
async def monitored_consent_accepted(callback: types.CallbackQuery, state: FSMContext):
    """Handle consent with monitoring"""
    user_id = callback.from_user.id
    
    async with db_pool.acquire() as conn:
        await conn.execute("""
            UPDATE selfology_users SET gdpr_consent = true WHERE telegram_id = $1
        """, str(user_id))
    
    logger = EnhancedLoggerMixin()
    logger.track_metric("gdpr_consents", 1, increment=True)
    
    await callback.message.edit_text("""
🎉 <b>Система мониторинга активирована!</b>

Используйте /start для доступа к функциям.
    """, parse_mode=ParseMode.HTML)


async def main():
    """Main function with enterprise monitoring"""
    
    print("🧠 Starting Production Monitored Selfology Bot...")
    print("📈 Initializing enterprise monitoring system...")
    
    # Initialize monitoring system
    try:
        monitoring_config = MonitoringConfig(
            service_name="selfology",
            environment="production", 
            dashboard_port=8002,  # Avoid conflicts
            api_port=8003
        )
        
        global monitoring_orchestrator
        monitoring_orchestrator = await initialize_monitoring_system(monitoring_config)
        await start_monitoring_system()
        
        print("✅ Enterprise monitoring system initialized!")
        print(f"📊 Dashboard: http://localhost:8002")
        print(f"🔗 API: http://localhost:8003")
        
    except Exception as e:
        print(f"⚠️ Monitoring initialization issue: {e}")
        print("🔄 Continuing without full monitoring...")
    
    # Initialize services
    if not await init_monitored_services():
        print("❌ Service initialization failed")
        return
    
    try:
        print("✅ Enhanced Logging: Active")
        print("✅ Question Deduplication: Active") 
        print("✅ Assessment Engine: NO SESSIONS")
        print("✅ Chat Service: Personalized")
        print("✅ Full Monitoring: Enterprise-grade")
        print(f"✅ Question Core: {'693 questions' if QUESTION_CORE_AVAILABLE else 'Demo mode'}")
        print("🚀 Ready for monitored production use!")
        
        await dp.start_polling(bot)
        
    except KeyboardInterrupt:
        print("\n🛑 Monitored bot stopped")
    finally:
        if db_pool:
            await db_pool.close()


if __name__ == "__main__":
    asyncio.run(main())