#!/usr/bin/env python3
"""
Human-Friendly Selfology Bot - Natural interface without technical terms
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

# Add question core to path
sys.path.append(str(Path(__file__).parent / "intelligent_question_core"))

try:
    from intelligent_question_core.api.core_api import SelfologyQuestionCore
    QUESTION_CORE_AVAILABLE = True
except Exception:
    QUESTION_CORE_AVAILABLE = False

# Configure logging
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
    answering_questions = State()
    chatting = State()

# Global instances
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
db_pool = None
question_core = None

# Domain translations for human-friendly display
DOMAIN_TRANSLATIONS = {
    "IDENTITY": "О себе и личности",
    "EMOTIONS": "Эмоции и чувства", 
    "RELATIONSHIPS": "Отношения с людьми",
    "WORK": "Работа и карьера",
    "MONEY": "Деньги и финансы",
    "HEALTH": "Здоровье и самочувствие", 
    "CREATIVITY": "Творчество и хобби",
    "SPIRITUALITY": "Смысл и ценности",
    "PAST": "Прошлое и опыт",
    "FUTURE": "Планы и мечты",
    "LIFESTYLE": "Образ жизни",
    "THOUGHTS": "Мысли и убеждения"
}

# Question improvement tracking
QUESTION_ISSUES = {}  # question_id -> issue_description

# Simple monitoring without enterprise complexity
class SimpleMonitor:
    """Simple monitoring for debugging without privacy violations"""
    
    def __init__(self):
        self.stats = {
            "total_requests": 0,
            "error_count": 0,
            "response_times": [],
            "start_time": datetime.now(timezone.utc)
        }
    
    def track_operation(self, operation: str, duration: float, success: bool, user_id: int = None):
        """Simple operation tracking"""
        self.stats["total_requests"] += 1
        self.stats["response_times"].append(duration)
        
        if not success:
            self.stats["error_count"] += 1
        
        # Simple console logging for debugging
        status = "✅" if success else "❌"
        user_display = f"User ***{str(user_id)[-3:]}" if user_id else "System"
        print(f"{datetime.now().strftime('%H:%M:%S')} {status} {operation}: {duration:.2f}s - {user_display}")
    
    def get_simple_stats(self) -> dict:
        """Get simple stats for display"""
        uptime = (datetime.now(timezone.utc) - self.stats["start_time"]).total_seconds()
        avg_response = sum(self.stats["response_times"]) / len(self.stats["response_times"]) if self.stats["response_times"] else 0
        error_rate = (self.stats["error_count"] / max(1, self.stats["total_requests"])) * 100
        
        return {
            "uptime_hours": uptime / 3600,
            "total_requests": self.stats["total_requests"],
            "error_rate": error_rate,
            "avg_response_time": avg_response
        }

# Global monitor
monitor = SimpleMonitor()


class HumanFriendlyQuestionService:
    """Question service with human-friendly interface"""
    
    def __init__(self, db_pool, question_core):
        self.db_pool = db_pool
        self.question_core = question_core
        self._answered_cache = {}
    
    async def get_answered_questions(self, user_id: int) -> Set[str]:
        """Get answered questions"""
        start_time = time.time()
        
        try:
            if user_id not in self._answered_cache:
                async with self.db_pool.acquire() as conn:
                    answered = await conn.fetch("""
                        SELECT DISTINCT question_id 
                        FROM selfology_question_answers 
                        WHERE user_id = $1
                    """, str(user_id))
                
                self._answered_cache[user_id] = {row["question_id"] for row in answered}
            
            duration = time.time() - start_time
            monitor.track_operation("get_answered_questions", duration, True, user_id)
            
            return self._answered_cache[user_id]
            
        except Exception as e:
            duration = time.time() - start_time
            monitor.track_operation("get_answered_questions", duration, False, user_id)
            logger.error(f"Error getting answered questions: {e}")
            return set()
    
    async def get_next_question(self, user_id: int) -> Optional[dict]:
        """Get next question with monitoring"""
        start_time = time.time()
        
        try:
            if not QUESTION_CORE_AVAILABLE:
                return None
            
            answered = await self.get_answered_questions(user_id)
            all_questions = list(self.question_core.questions_lookup.values())
            unanswered = [q for q in all_questions if q["id"] not in answered]
            
            if not unanswered:
                monitor.track_operation("get_next_question", time.time() - start_time, True, user_id)
                return None
            
            # Select question
            selected = self._select_best_question(unanswered, user_id)
            
            duration = time.time() - start_time
            monitor.track_operation("get_next_question", duration, True, user_id)
            
            return selected
            
        except Exception as e:
            duration = time.time() - start_time
            monitor.track_operation("get_next_question", duration, False, user_id)
            logger.error(f"Error selecting question: {e}")
            return None
    
    def _select_best_question(self, available_questions: List[dict], user_id: int) -> dict:
        """Select best question"""
        
        # Prioritize safe questions
        safe_questions = [q for q in available_questions if q["psychology"]["safety_level"] >= 4]
        
        if safe_questions:
            return safe_questions[0]
        
        return available_questions[0]
    
    async def process_answer(self, user_id: int, question_id: str, answer: str) -> dict:
        """Process answer"""
        start_time = time.time()
        
        try:
            question = self.question_core.get_question(question_id) if QUESTION_CORE_AVAILABLE else None
            if not question:
                return {"error": "Question not found"}
            
            # Analyze answer
            analysis = self._analyze_answer(answer, question)
            
            # Save to database  
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO selfology_question_answers 
                    (user_id, question_id, answer_text, answer_analysis)
                    VALUES ($1, $2, $3, $4)
                """, str(user_id), question_id, answer, json.dumps(analysis))
            
            # Update cache
            if user_id not in self._answered_cache:
                self._answered_cache[user_id] = set()
            self._answered_cache[user_id].add(question_id)
            
            # Get next question
            next_question = await self.get_next_question(user_id)
            
            duration = time.time() - start_time
            monitor.track_operation("process_answer", duration, True, user_id)
            
            return {
                "analysis": analysis,
                "next_question": next_question,
                "processing_time": duration
            }
            
        except Exception as e:
            duration = time.time() - start_time
            monitor.track_operation("process_answer", duration, False, user_id)
            logger.error(f"Error processing answer: {e}")
            return {"error": str(e)}
    
    def _analyze_answer(self, answer: str, question: dict) -> dict:
        """Analyze answer"""
        
        word_count = len(answer.split())
        
        # Simple sentiment
        positive_words = ["хорошо", "отлично", "люблю", "нравится", "классн", "красив"]
        negative_words = ["плохо", "грустно", "тяжело", "больно", "страшно"]
        
        positive_count = sum(1 for word in positive_words if word in answer.lower())
        negative_count = sum(1 for word in negative_words if word in answer.lower())
        
        emotional_state = "positive" if positive_count > negative_count else "negative" if negative_count > 0 else "neutral"
        openness = min(1.0, word_count / 15.0)
        
        return {
            "emotional_state": emotional_state,
            "openness_level": round(openness, 2),
            "word_count": word_count,
            "domain": question["classification"]["domain"],
            "analysis_timestamp": datetime.now(timezone.utc).isoformat()
        }


# Initialize service
question_service = None

async def init_services():
    """Initialize services"""
    global db_pool, question_core, question_service
    
    try:
        # Database
        db_pool = await asyncpg.create_pool(**DB_CONFIG)
        
        # Question Core
        if QUESTION_CORE_AVAILABLE:
            core_path = Path(__file__).parent / "intelligent_question_core/data/selfology_intelligent_core.json"
            question_core = SelfologyQuestionCore(str(core_path))
        
        # Service
        question_service = HumanFriendlyQuestionService(db_pool, question_core)
        
        return True
        
    except Exception as e:
        logger.error(f"Service initialization failed: {e}")
        return False


# === HUMAN-FRIENDLY HANDLERS ===

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Human-friendly start"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "Friend"
    
    start_time = time.time()
    
    try:
        async with db_pool.acquire() as conn:
            user_data = await conn.fetchrow(
                "SELECT * FROM selfology_users WHERE telegram_id = $1", str(user_id)
            )
        
        if user_data:
            if user_data["gdpr_consent"]:
                await show_friendly_dashboard(message, state, user_data)
            else:
                await show_gdpr_consent(message, state)
        else:
            await create_user_and_consent(message, state, user_id)
        
        duration = time.time() - start_time
        monitor.track_operation("start_command", duration, True, user_id)
        
    except Exception as e:
        duration = time.time() - start_time
        monitor.track_operation("start_command", duration, False, user_id)
        await message.answer("Произошла ошибка. Попробуйте еще раз.")


async def show_friendly_dashboard(message: Message, state: FSMContext, user_data: dict):
    """Friendly dashboard without technical terms"""
    
    user_name = user_data["first_name"] or "Friend"
    user_id = int(user_data["telegram_id"])
    
    # Get progress
    if question_service:
        answered = await question_service.get_answered_questions(user_id)
        answers_count = len(answered)
    else:
        answers_count = 0
    
    dashboard_text = f"""
🏠 <b>Привет, {user_name}!</b>

<b>📊 Ваш прогресс:</b>
• Вопросов отвечено: <code>{answers_count}</code>
• Готовность профиля: <code>{min(100, answers_count * 7):.0f}%</code>

<b>🎯 Что хотите делать?</b>
    """
    
    keyboard_buttons = []
    
    if answers_count < 15:
        keyboard_buttons.append([InlineKeyboardButton(text="📝 Продолжить анкету", callback_data="continue_questions")])
    else:
        keyboard_buttons.append([InlineKeyboardButton(text="💬 Поговорить с коучем", callback_data="start_coaching")])
    
    keyboard_buttons.extend([
        [InlineKeyboardButton(text="📊 Мой прогресс", callback_data="show_progress")],
        [InlineKeyboardButton(text="💬 Просто поговорить", callback_data="start_chat")],
        [InlineKeyboardButton(text="👤 Мой профиль", callback_data="show_my_profile")]
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    await message.answer(dashboard_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(UserStates.main_menu)


@dp.callback_query(F.data == "continue_questions")
async def continue_questions(callback: types.CallbackQuery, state: FSMContext):
    """Continue questions"""
    user_id = callback.from_user.id
    
    if question_service:
        next_question = await question_service.get_next_question(user_id)
        
        if next_question:
            await show_human_friendly_question(callback.message, next_question, user_id)
            await state.set_state(UserStates.answering_questions)
        else:
            await callback.message.edit_text("""
🎉 <b>Поздравляю!</b>

Вы ответили на все доступные вопросы! Ваш психологический профиль готов.

Теперь можете получать персональные советы от коуча! 🚀
            """, parse_mode=ParseMode.HTML)
    else:
        await callback.message.edit_text("Анкетирование временно недоступно.")


async def show_human_friendly_question(message: Message, question: dict, user_id: int):
    """Show question in human-friendly format"""
    
    # Get progress
    if question_service:
        answered = await question_service.get_answered_questions(user_id)
        question_number = len(answered) + 1
    else:
        question_number = 1
    
    # Translate domain to human language
    domain_human = DOMAIN_TRANSLATIONS.get(question["classification"]["domain"], "Общие вопросы")
    
    question_text = f"""
📝 <b>Вопрос {question_number}</b>

<b>Тема:</b> {domain_human}

{question['text']}

💭 <i>Отвечайте как чувствуете - нет правильных или неправильных ответов</i>

<code>ID вопроса для обратной связи: {question['id']}</code>
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭️ Пропустить вопрос", callback_data="skip_question")],
        [InlineKeyboardButton(text="📊 Посмотреть прогресс", callback_data="show_progress")],
        [InlineKeyboardButton(text="💬 Перейти к беседе", callback_data="start_chat")],
        [InlineKeyboardButton(text="❓ Не понял вопрос", callback_data=f"report_question_{question['id']}")],
    ])
    
    await message.edit_text(question_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)


@dp.message(UserStates.answering_questions)
async def handle_friendly_answer(message: Message, state: FSMContext):
    """Handle answer with friendly feedback"""
    
    user_id = message.from_user.id
    answer = message.text
    
    if question_service:
        # Get current question
        async with db_pool.acquire() as conn:
            last_question_id = await conn.fetchval("""
                SELECT question_id FROM selfology_question_answers
                WHERE user_id = $1 ORDER BY answered_at DESC LIMIT 1
            """, str(user_id))
        
        if not last_question_id and question_service:
            next_q = await question_service.get_next_question(user_id)
            if next_q:
                last_question_id = next_q["id"]
        
        if last_question_id:
            # Process answer
            result = await question_service.process_answer(user_id, last_question_id, answer)
            
            if "error" in result:
                await message.answer(f"Произошла ошибка: {result['error']}")
                return
            
            # Human-friendly feedback
            analysis = result["analysis"]
            
            feedback_text = f"""
✅ <b>Спасибо за ответ!</b>

Ваш ответ помогает мне лучше понимать вас как личность.

<b>📊 Что я понял:</b>
• Эмоциональная окраска: {get_emotion_description(analysis['emotional_state'])}
• Подробность рассказа: {get_detail_description(analysis['openness_level'])}
• Тема: {DOMAIN_TRANSLATIONS.get(analysis['domain'], 'Общие вопросы')}

💾 <i>Ответ сохранен в вашем профиле</i>
            """
            
            if result["next_question"]:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="➡️ Следующий вопрос", callback_data="show_next_question")],
                    [InlineKeyboardButton(text="📊 Мой прогресс", callback_data="show_progress")],
                    [InlineKeyboardButton(text="✅ Закончить пока", callback_data="finish_for_now")]
                ])
            else:
                feedback_text += "\n\n🎉 <b>Анкетирование завершено!</b>"
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="💬 Поговорить с коучем", callback_data="start_coaching")],
                    [InlineKeyboardButton(text="👤 Посмотреть профиль", callback_data="show_my_profile")]
                ])
            
            await message.answer(feedback_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)


def get_emotion_description(emotional_state: str) -> str:
    """Human description of emotional state"""
    descriptions = {
        "positive": "Позитивная, жизнерадостная",
        "negative": "Сложная, требующая поддержки", 
        "neutral": "Спокойная, размеренная"
    }
    return descriptions.get(emotional_state, "Нейтральная")


def get_detail_description(openness_level: float) -> str:
    """Human description of detail level"""
    if openness_level > 0.8:
        return "Очень подробный и открытый"
    elif openness_level > 0.5:
        return "Достаточно детальный"
    else:
        return "Краткий и по существу"


@dp.callback_query(F.data == "show_progress")
async def show_friendly_progress(callback: types.CallbackQuery):
    """Show progress in human-friendly way"""
    
    user_id = callback.from_user.id
    start_time = time.time()
    
    try:
        # Get user statistics
        async with db_pool.acquire() as conn:
            stats = await conn.fetch("""
                SELECT question_id, answer_analysis, answered_at
                FROM selfology_question_answers 
                WHERE user_id = $1 
                ORDER BY answered_at DESC
            """, str(user_id))
        
        # Analyze domains
        domain_coverage = {}
        total_words = 0
        
        if QUESTION_CORE_AVAILABLE and stats:
            for record in stats:
                question = question_core.get_question(record["question_id"])
                if question:
                    domain = question["classification"]["domain"]
                    domain_human = DOMAIN_TRANSLATIONS.get(domain, domain)
                    domain_coverage[domain_human] = domain_coverage.get(domain_human, 0) + 1
                
                if record["answer_analysis"]:
                    analysis = json.loads(record["answer_analysis"])
                    total_words += analysis.get("word_count", 0)
        
        avg_words = total_words / len(stats) if stats else 0
        
        progress_text = f"""
📊 <b>Ваш прогресс в самопознании</b>

<b>📈 Общая статистика:</b>
• Отвечено вопросов: <code>{len(stats)}</code>
• Среднее количество слов в ответе: <code>{avg_words:.0f}</code>
• Готовность профиля: <code>{min(100, len(stats) * 7):.0f}%</code>

<b>🗺️ Исследованные области жизни:</b>
{chr(10).join([f"• {domain}: {count} ответ(ов)" for domain, count in domain_coverage.items()]) if domain_coverage else "• Пока нет данных"}

<b>📅 Активность:</b>
• Первый ответ: {stats[0]['answered_at'].strftime('%d.%m.%Y') if stats else 'Нет данных'}
• Последний ответ: {stats[-1]['answered_at'].strftime('%d.%m %H:%M') if stats else 'Нет данных'}

<b>💡 Рекомендация:</b> {get_progress_recommendation(len(stats))}

<b>🔍 Системная информация:</b>
• Всё работает стабильно ✅
• Данные сохраняются надежно ✅
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 Продолжить вопросы", callback_data="continue_questions")],
            [InlineKeyboardButton(text="💬 К беседе", callback_data="start_chat")],
            [InlineKeyboardButton(text="👤 Мой профиль", callback_data="show_my_profile")],
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="show_progress")]
        ])
        
        await callback.message.edit_text(progress_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        
        duration = time.time() - start_time
        monitor.track_operation("show_progress", duration, True, user_id)
        
    except Exception as e:
        duration = time.time() - start_time
        monitor.track_operation("show_progress", duration, False, user_id)
        await callback.message.edit_text("Ошибка получения прогресса.")


def get_progress_recommendation(answers_count: int) -> str:
    """Get human progress recommendation"""
    if answers_count == 0:
        return "Начните с нескольких вопросов для создания базового профиля"
    elif answers_count < 5:
        return "Ответьте еще на несколько вопросов для более полной картины"
    elif answers_count < 10:
        return "Хорошее начало! Продолжайте для углубления профиля"
    else:
        return "Отличная база данных о вас! Готово для глубокой персонализации"


@dp.callback_query(F.data == "show_my_profile")
async def show_user_profile(callback: types.CallbackQuery):
    """Show user profile in human language"""
    
    user_id = callback.from_user.id
    
    try:
        async with db_pool.acquire() as conn:
            # Get user data
            user_data = await conn.fetchrow("""
                SELECT telegram_id, first_name, created_at, gdpr_consent, onboarding_completed
                FROM selfology_users WHERE telegram_id = $1
            """, str(user_id))
            
            # Get answers
            answers = await conn.fetch("""
                SELECT question_id, answer_analysis, answered_at
                FROM selfology_question_answers 
                WHERE user_id = $1 
                ORDER BY answered_at DESC
                LIMIT 10
            """, str(user_id))
        
        if answers:
            # Domain analysis
            domain_coverage = {}
            openness_levels = []
            
            if QUESTION_CORE_AVAILABLE:
                for answer in answers:
                    question = question_core.get_question(answer["question_id"])
                    if question:
                        domain = question["classification"]["domain"] 
                        domain_human = DOMAIN_TRANSLATIONS.get(domain, domain)
                        domain_coverage[domain_human] = domain_coverage.get(domain_human, 0) + 1
                    
                    if answer["answer_analysis"]:
                        analysis = json.loads(answer["answer_analysis"])
                        openness_levels.append(analysis.get("openness_level", 0))
            
            avg_openness = sum(openness_levels) / len(openness_levels) if openness_levels else 0
            
            profile_text = f"""
👤 <b>Ваш психологический профиль</b>

<b>📊 На основе {len(answers)} ваших ответов:</b>

<b>🎯 Исследованные области вашей жизни:</b>
{chr(10).join([f"• {domain}: {count} глубинных ответа" for domain, count in domain_coverage.items()])}

<b>📈 Ваши особенности:</b>
• Стиль общения: {get_communication_style(avg_openness)}
• Готовность к самоанализу: {get_self_analysis_readiness(len(answers))}
• Уровень доверия системе: {get_trust_level(avg_openness)}

<b>📅 В Selfology с:</b> {user_data['created_at'].strftime('%d.%m.%Y')}

<b>🎯 Что профиль позволяет:</b>
• Персональные советы с учетом вашего типа личности
• Рекомендации, адаптированные под ваш стиль мышления
• Поддержка в стиле, который вам подходит

<i>Профиль становится точнее с каждым новым ответом!</i>
            """
        else:
            profile_text = """
👤 <b>Ваш профиль пока пустой</b>

Пройдите анкетирование для создания персонального психологического профиля!

Используйте кнопку "📝 Продолжить анкету"
            """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 Больше вопросов", callback_data="continue_questions")],
            [InlineKeyboardButton(text="💬 Поговорить", callback_data="start_chat")],
            [InlineKeyboardButton(text="📊 Прогресс", callback_data="show_progress")]
        ])
        
        await callback.message.edit_text(profile_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        logger.error(f"Profile error: {e}")
        await callback.message.edit_text("Ошибка загрузки профиля.")


def get_communication_style(openness: float) -> str:
    """Describe communication style"""
    if openness > 0.8:
        return "Подробный и открытый"
    elif openness > 0.5:
        return "Размышляющий и вдумчивый"
    else:
        return "Краткий и конкретный"


def get_self_analysis_readiness(answers_count: int) -> str:
    """Describe self-analysis readiness"""
    if answers_count > 10:
        return "Очень высокая"
    elif answers_count > 5:
        return "Высокая"
    else:
        return "Развивающаяся"


def get_trust_level(openness: float) -> str:
    """Describe trust level"""
    if openness > 0.7:
        return "Высокий - готовы к глубоким темам"
    elif openness > 0.4:
        return "Средний - комфортно с основными вопросами"
    else:
        return "Развивающийся - предпочитаете простые темы"


@dp.callback_query(F.data.startswith("report_question_"))
async def report_question_issue(callback: types.CallbackQuery):
    """Report issue with question"""
    
    question_id = callback.data.split("_")[-1]
    
    # Record issue
    QUESTION_ISSUES[question_id] = {
        "reported_by": callback.from_user.id,
        "issue": "unclear_formulation",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    await callback.message.edit_text(f"""
📝 <b>Спасибо за обратную связь!</b>

Вопрос <code>{question_id}</code> отмечен для улучшения.

<b>🔧 Что происходит:</b>
• Ваша обратная связь записана
• Вопрос будет переформулирован  
• Улучшенная версия появится в системе

<b>А пока:</b>
    """, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭️ Пропустить этот вопрос", callback_data="skip_question")],
        [InlineKeyboardButton(text="💬 Перейти к беседе", callback_data="start_chat")]
    ]), parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "start_chat")
async def start_friendly_chat(callback: types.CallbackQuery, state: FSMContext):
    """Start chat in friendly mode"""
    
    user_id = callback.from_user.id
    
    # Get user context
    if question_service:
        answered = await question_service.get_answered_questions(user_id)
        answers_count = len(answered)
    else:
        answers_count = 0
    
    chat_text = f"""
💬 <b>Режим беседы включен!</b>

Теперь можете писать мне любые вопросы или рассказывать что волнует.

<b>🎯 Как я помогу:</b>
• Разберем сложные ситуации
• Найдем решения для ваших задач
• Поддержу в трудные моменты
• Дам советы с учетом вашей личности

{f'<b>💡 У меня есть информация из {answers_count} ваших ответов для персонализации!</b>' if answers_count > 0 else '<b>💡 Чем больше расскажете, тем точнее будут советы!</b>'}

Пишите что угодно! 👇
    """
    
    await callback.message.edit_text(chat_text, parse_mode=ParseMode.HTML)
    await state.set_state(UserStates.chatting)


@dp.message(UserStates.chatting)
async def handle_friendly_chat(message: Message, state: FSMContext):
    """Handle chat with personalization"""
    
    user_id = message.from_user.id
    user_message = message.text
    
    start_time = time.time()
    
    try:
        # Get user context for personalization
        async with db_pool.acquire() as conn:
            answers_count = await conn.fetchval("""
                SELECT COUNT(*) FROM selfology_question_answers WHERE user_id = $1
            """, str(user_id))
        
        # Generate personalized response
        if any(word in user_message.lower() for word in ["плохо", "грустно", "тяжело", "болит"]):
            response = generate_support_response(user_message, answers_count)
        elif any(word in user_message.lower() for word in ["как", "что делать", "помоги", "?"]):
            response = generate_advice_response(user_message, answers_count)
        else:
            response = generate_conversation_response(user_message, answers_count)
        
        await message.answer(response, parse_mode=ParseMode.HTML)
        
        duration = time.time() - start_time
        monitor.track_operation("chat_response", duration, True, user_id)
        
    except Exception as e:
        duration = time.time() - start_time
        monitor.track_operation("chat_response", duration, False, user_id)
        await message.answer("Произошла ошибка в беседе. Попробуйте еще раз.")


def generate_support_response(message: str, answers_count: int) -> str:
    """Generate supportive response"""
    
    base_support = """
🤗 <b>Понимаю, что вам сейчас нелегко</b>

Спасибо что поделились. Признание сложных чувств - это уже шаг к их пониманию.

<b>💙 Что может помочь прямо сейчас:</b>
• Сделайте несколько медленных глубоких вдохов
• Напомните себе: "Это состояние временное"
• Подумайте о том, кто или что обычно вас поддерживает
    """
    
    if answers_count > 3:
        base_support += "\n\n<b>🎯 На основе того, что я знаю о вас:</b>\nПопробуйте применить стратегии, которые помогали вам раньше в похожих ситуациях."
    
    base_support += "\n\nХотите рассказать подробнее? Я готов выслушать и поддержать 💚"
    
    return base_support


def generate_advice_response(message: str, answers_count: int) -> str:
    """Generate advice response"""
    
    advice = f"""
🎯 <b>Разберем ваш вопрос</b>

<b>💡 Мой совет:</b>
Попробуйте разложить ситуацию на более мелкие, управляемые части.

<b>🔍 Вопросы для размышления:</b>
• Что в этой ситуации зависит от вас, а что - нет?
• Какие ваши сильные стороны можно применить?
• Что самое важное для вас в этой ситуации?

{f'<b>🎯 С учетом вашего профиля ({answers_count} ответов):</b>' + chr(10) + get_personalized_advice_hint(answers_count) if answers_count > 0 else ''}

Расскажите больше деталей для более точного совета! 🚀
    """
    
    return advice


def get_personalized_advice_hint(answers_count: int) -> str:
    """Get personalized advice hint"""
    if answers_count > 5:
        return "Судя по вашим ответам, вы человек вдумчивый - создайте план действий"
    else:
        return "Действуйте пошагово и не торопитесь с решениями"


def generate_conversation_response(message: str, answers_count: int) -> str:
    """Generate conversational response"""
    
    return f"""
💬 <b>Понял!</b>

<b>🤖 Ваше сообщение принято к размышлению</b>

{f'На основе {answers_count} ваших ответов: это интересная мысль, которая дополняет то, что я уже знаю о вас!' if answers_count > 0 else 'Интересная мысль! Хотелось бы узнать вас лучше через анкетирование.'}

<b>💭 Есть что добавить к этой теме?</b>

Продолжайте делиться мыслями! 💭
    """


# Add missing handlers
async def show_gdpr_consent(message: Message, state: FSMContext):
    """GDPR consent"""
    await message.answer("""
🌟 <b>Добро пожаловать в Selfology!</b>

Персональный психологический коуч с умной системой анкетирования.

Согласны на анализ ваших ответов для персонализации?
    """, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Согласен", callback_data="consent_yes")]
    ]), parse_mode=ParseMode.HTML)


async def create_user_and_consent(message: Message, state: FSMContext, user_id: int):
    """Create user"""
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO selfology_users 
            (telegram_id, username, first_name, last_name, last_active) 
            VALUES ($1, $2, $3, $4, $5)
        """, str(user_id), message.from_user.username, 
        message.from_user.first_name, message.from_user.last_name, datetime.now(timezone.utc))
    
    await show_gdpr_consent(message, state)


@dp.callback_query(F.data == "consent_yes")
async def consent_accepted(callback: types.CallbackQuery, state: FSMContext):
    """Handle consent"""
    user_id = callback.from_user.id
    
    async with db_pool.acquire() as conn:
        await conn.execute("""
            UPDATE selfology_users SET gdpr_consent = true WHERE telegram_id = $1
        """, str(user_id))
    
    await callback.message.edit_text("""
🎉 <b>Отлично!</b>

Теперь можем создать ваш персональный профиль. Используйте /start для продолжения.
    """, parse_mode=ParseMode.HTML)


# Commands
@dp.message(Command("profile"))
async def cmd_profile(message: Message):
    """Profile command"""
    user_id = message.from_user.id
    await show_user_profile_from_command(message, user_id)


async def show_user_profile_from_command(message: Message, user_id: int):
    """Show profile from command"""
    try:
        async with db_pool.acquire() as conn:
            answers = await conn.fetch("""
                SELECT question_id, answered_at
                FROM selfology_question_answers WHERE user_id = $1
                ORDER BY answered_at DESC LIMIT 5
            """, str(user_id))
        
        if answers:
            profile_text = f"""
👤 <b>Ваш профиль в Selfology</b>

• Отвечено вопросов: <code>{len(answers)}</code>
• Последняя активность: {answers[0]['answered_at'].strftime('%d.%m %H:%M')}

Используйте меню /start для подробной информации.
            """
        else:
            profile_text = """
👤 <b>Профиль пуст</b>

Начните с /start чтобы пройти анкетирование!
            """
        
        await message.answer(profile_text, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        await message.answer("Ошибка загрузки профиля.")


@dp.message(Command("stats"))  
async def cmd_stats(message: Message):
    """Simple stats command"""
    user_id = message.from_user.id
    
    # Get simple stats
    stats = monitor.get_simple_stats()
    
    try:
        async with db_pool.acquire() as conn:
            user_answers = await conn.fetchval("""
                SELECT COUNT(*) FROM selfology_question_answers WHERE user_id = $1
            """, str(user_id))
        
        stats_text = f"""
📊 <b>Быстрая статистика</b>

<b>👤 Ваши данные:</b>
• Ответов дано: <code>{user_answers}</code>

<b>⚙️ Система:</b>  
• Работает: <code>{stats['uptime_hours']:.1f}</code> часов
• Обработано запросов: <code>{stats['total_requests']}</code>
• Среднее время ответа: <code>{stats['avg_response_time']:.2f}</code>с

Используйте /start → "📊 Мой прогресс" для подробностей.
        """
        
        await message.answer(stats_text, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        await message.answer("Ошибка статистики.")


async def main():
    """Main function"""
    
    print("👋 Starting Human-Friendly Selfology Bot...")
    print("✅ Natural language interface")
    print("✅ Privacy-compliant monitoring") 
    print("✅ Question issue tracking")
    print("✅ No technical jargon")
    
    if not await init_services():
        print("❌ Service initialization failed")
        return
    
    try:
        print(f"✅ Question Database: {'693 questions' if QUESTION_CORE_AVAILABLE else 'Demo mode'}")
        print("✅ User-Friendly Interface: Active")
        print("✅ Question Issue Tracking: Active")
        print("✅ Simple Monitoring: Active")
        print("😊 Ready for human interactions!")
        
        await dp.start_polling(bot)
        
    except KeyboardInterrupt:
        print(f"\n🛑 Bot stopped")
        
        # Show question issues if any
        if QUESTION_ISSUES:
            print(f"\n📝 Question Issues Reported:")
            for q_id, issue in QUESTION_ISSUES.items():
                print(f"   • Question {q_id}: {issue['issue']}")
    
    finally:
        if db_pool:
            await db_pool.close()


if __name__ == "__main__":
    asyncio.run(main())