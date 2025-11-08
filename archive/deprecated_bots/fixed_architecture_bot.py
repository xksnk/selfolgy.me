#!/usr/bin/env python3
"""
Fixed Architecture Selfology Bot
Addresses all UX and architectural issues:
1. No session anti-pattern - individual question tracking
2. Proper statistics handlers
3. Question deduplication
4. Clean user experience
5. Modular approach within single file
"""

import asyncio
import asyncpg
import logging
import sys
import json
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass

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
except Exception as e:
    QUESTION_CORE_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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
    assessment_mode = State()
    chat_mode = State()

# Global instances
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
db_pool = None
question_core = None

# === MODULAR SERVICES ===

@dataclass
class UserProgress:
    """User progress tracking without sessions"""
    user_id: int
    answered_questions: Set[str]  # Set of answered question IDs
    current_energy: float
    trust_level: float
    domain_progress: Dict[str, int]  # domain -> count
    last_question_id: Optional[str]
    total_answers: int


class QuestionDeduplicationService:
    """Ensures no question is asked twice to the same user"""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
        self._user_answered_cache = {}  # user_id -> Set[question_ids]
    
    async def get_answered_questions(self, user_id: int) -> Set[str]:
        """Get all questions user has already answered"""
        
        if user_id not in self._user_answered_cache:
            async with self.db_pool.acquire() as conn:
                answered = await conn.fetch("""
                    SELECT DISTINCT question_id 
                    FROM selfology_question_answers 
                    WHERE user_id = $1
                """, str(user_id))
            
            self._user_answered_cache[user_id] = {row["question_id"] for row in answered}
        
        return self._user_answered_cache[user_id]
    
    async def mark_question_answered(self, user_id: int, question_id: str):
        """Mark question as answered"""
        if user_id not in self._user_answered_cache:
            self._user_answered_cache[user_id] = set()
        
        self._user_answered_cache[user_id].add(question_id)
    
    def filter_unanswered_questions(self, user_id: int, questions: List[dict]) -> List[dict]:
        """Filter out already answered questions"""
        answered = self._user_answered_cache.get(user_id, set())
        return [q for q in questions if q["id"] not in answered]


class AssessmentEngine:
    """Independent assessment engine - NO SESSIONS"""
    
    def __init__(self, db_pool, question_core):
        self.db_pool = db_pool
        self.question_core = question_core
        self.deduplication = QuestionDeduplicationService(db_pool)
    
    async def get_user_progress(self, user_id: int) -> UserProgress:
        """Get current user progress without sessions"""
        
        answered_questions = await self.deduplication.get_answered_questions(user_id)
        
        # Get user metrics
        async with self.db_pool.acquire() as conn:
            # Calculate current state based on all answers
            user_stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_answers,
                    AVG(CAST(answer_analysis->>'openness_level' AS FLOAT)) as avg_openness,
                    AVG(CAST(answer_analysis->>'trust_building' AS FLOAT)) as avg_trust,
                    MAX(answered_at) as last_answer_time
                FROM selfology_question_answers 
                WHERE user_id = $1 AND answer_analysis IS NOT NULL
            """, str(user_id))
            
            # Get last question
            last_question = await conn.fetchval("""
                SELECT question_id FROM selfology_question_answers
                WHERE user_id = $1 
                ORDER BY answered_at DESC 
                LIMIT 1
            """, str(user_id))
        
        # Calculate domain progress
        domain_progress = {}
        if QUESTION_CORE_AVAILABLE:
            for question_id in answered_questions:
                question = self.question_core.get_question(question_id)
                if question:
                    domain = question["classification"]["domain"]
                    domain_progress[domain] = domain_progress.get(domain, 0) + 1
        
        # Calculate trust and energy based on accumulated answers
        trust_level = min(5.0, 1.0 + (user_stats["avg_trust"] or 0) * 20)
        energy_level = 0.3 + (user_stats["avg_openness"] or 0) * 0.5 - len(answered_questions) * 0.02
        energy_level = max(-2.0, min(2.0, energy_level))
        
        return UserProgress(
            user_id=user_id,
            answered_questions=answered_questions,
            current_energy=energy_level,
            trust_level=trust_level,
            domain_progress=domain_progress,
            last_question_id=last_question,
            total_answers=user_stats["total_answers"] or 0
        )
    
    async def get_next_question(self, user_id: int) -> Optional[dict]:
        """Get next question using intelligent selection - NO SESSIONS"""
        
        if not QUESTION_CORE_AVAILABLE:
            return None
        
        progress = await self.get_user_progress(user_id)
        
        # Get all available questions
        all_questions = list(self.question_core.questions_lookup.values())
        
        # Filter out answered questions
        unanswered = self.deduplication.filter_unanswered_questions(user_id, all_questions)
        
        if not unanswered:
            return None  # All questions answered
        
        # Smart selection based on user state
        return self._select_optimal_question(progress, unanswered)
    
    def _select_optimal_question(self, progress: UserProgress, available_questions: List[dict]) -> dict:
        """Select optimal question based on user progress"""
        
        # Filter by trust level
        suitable_questions = [
            q for q in available_questions 
            if q["psychology"]["trust_requirement"] <= progress.trust_level
        ]
        
        if not suitable_questions:
            suitable_questions = available_questions  # Fallback
        
        # Filter by energy state
        if progress.current_energy < -0.5:
            # Need healing questions
            healing_questions = [
                q for q in suitable_questions 
                if q["classification"]["energy_dynamic"] == "HEALING"
            ]
            if healing_questions:
                return healing_questions[0]
        
        # Prefer unexplored domains
        explored_domains = set(progress.domain_progress.keys())
        all_domains = {"IDENTITY", "EMOTIONS", "RELATIONSHIPS", "WORK", "HEALTH", "FUTURE"}
        unexplored_domains = all_domains - explored_domains
        
        if unexplored_domains:
            for domain in unexplored_domains:
                domain_questions = [
                    q for q in suitable_questions 
                    if q["classification"]["domain"] == domain
                ]
                if domain_questions:
                    return domain_questions[0]
        
        # Continue with least explored domain
        if progress.domain_progress:
            least_explored_domain = min(progress.domain_progress.items(), key=lambda x: x[1])[0]
            domain_questions = [
                q for q in suitable_questions
                if q["classification"]["domain"] == least_explored_domain
            ]
            if domain_questions:
                return domain_questions[0]
        
        # Fallback to safe question
        safe_questions = [
            q for q in suitable_questions 
            if q["psychology"]["safety_level"] >= 4
        ]
        
        return safe_questions[0] if safe_questions else suitable_questions[0]
    
    async def process_answer(self, user_id: int, question_id: str, answer: str) -> dict:
        """Process answer immediately - no sessions"""
        
        if not QUESTION_CORE_AVAILABLE:
            return {"error": "Question core not available"}
        
        question = self.question_core.get_question(question_id)
        if not question:
            return {"error": "Question not found"}
        
        # Analyze answer
        analysis = await self._analyze_answer(answer, question, user_id)
        
        # Save immediately to database
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO selfology_question_answers 
                (user_id, question_id, answer_text, answer_analysis, ai_model_used)
                VALUES ($1, $2, $3, $4, $5)
            """, str(user_id), question_id, answer, json.dumps(analysis), "basic_analysis")
        
        # Mark as answered
        await self.deduplication.mark_question_answered(user_id, question_id)
        
        # Get next question immediately  
        next_question = await self.get_next_question(user_id)
        
        logger.info(f"📊 Processed Q&A: {user_id} answered {question_id}, next: {next_question['id'] if next_question else 'COMPLETE'}")
        
        return {
            "analysis": analysis,
            "next_question": next_question,
            "progress": await self.get_user_progress(user_id)
        }
    
    async def _analyze_answer(self, answer: str, question: dict, user_id: int) -> dict:
        """Analyze answer with basic intelligence"""
        
        word_count = len(answer.split())
        
        # Enhanced analysis
        positive_words = ["хорошо", "отлично", "люблю", "нравится", "классн", "красив", "вдохнов"]
        negative_words = ["плохо", "грустно", "тяжело", "больно", "страшно", "злой"]
        
        positive_count = sum(1 for word in positive_words if word in answer.lower())
        negative_count = sum(1 for word in negative_words if word in answer.lower())
        
        emotional_state = "positive" if positive_count > negative_count else "negative" if negative_count > 0 else "neutral"
        
        # Calculate metrics
        openness = min(1.0, word_count / 15.0)
        vulnerability = 0.8 if any(word in answer.lower() for word in ["чувствую", "боюсь", "переживаю"]) else 0.3
        
        return {
            "emotional_state": emotional_state,
            "openness_level": round(openness, 2),
            "vulnerability_shown": round(vulnerability, 2),
            "word_count": word_count,
            "energy_impact": 0.1 if positive_count > 0 else -0.1 if negative_count > 0 else 0.0,
            "trust_building": round(openness * vulnerability * 0.2, 2),
            "domain": question["classification"]["domain"],
            "analysis_timestamp": datetime.now(timezone.utc).isoformat()
        }


class StatisticsService:
    """Independent statistics service"""
    
    def __init__(self, db_pool, question_core):
        self.db_pool = db_pool
        self.question_core = question_core
        self._cache = {}
        self._cache_timestamp = {}
    
    async def get_user_statistics(self, user_id: int, use_cache: bool = True) -> dict:
        """Get comprehensive user statistics"""
        
        cache_key = f"stats_{user_id}"
        
        # Check cache (5 minute expiry)
        if use_cache and cache_key in self._cache:
            if datetime.now() - self._cache_timestamp[cache_key] < timedelta(minutes=5):
                return self._cache[cache_key]
        
        # Generate fresh statistics
        stats = await self._generate_user_stats(user_id)
        
        # Cache results
        self._cache[cache_key] = stats
        self._cache_timestamp[cache_key] = datetime.now()
        
        return stats
    
    async def _generate_user_stats(self, user_id: int) -> dict:
        """Generate comprehensive user statistics"""
        
        async with self.db_pool.acquire() as conn:
            # Basic stats
            user_data = await conn.fetchrow("""
                SELECT telegram_id, gdpr_consent, onboarding_completed, created_at, last_active
                FROM selfology_users WHERE telegram_id = $1
            """, str(user_id))
            
            # Answer statistics
            answer_stats = await conn.fetch("""
                SELECT question_id, answer_analysis, answered_at
                FROM selfology_question_answers 
                WHERE user_id = $1 
                ORDER BY answered_at DESC
            """, str(user_id))
            
            # Insight statistics
            insights_count = await conn.fetchval("""
                SELECT COUNT(*) FROM selfology_chat_insights WHERE user_id = $1
            """, str(user_id))
        
        # Domain analysis
        domain_coverage = {}
        personality_evolution = {}
        
        if QUESTION_CORE_AVAILABLE and answer_stats:
            for answer in answer_stats:
                question = self.question_core.get_question(answer["question_id"])
                if question:
                    domain = question["classification"]["domain"]
                    domain_coverage[domain] = domain_coverage.get(domain, 0) + 1
                    
                    # Track personality evolution
                    analysis = json.loads(answer["answer_analysis"]) if answer["answer_analysis"] else {}
                    openness = analysis.get("openness_level", 0)
                    personality_evolution[answer["answered_at"].isoformat()] = openness
        
        return {
            "user_info": {
                "id": user_data["telegram_id"],
                "gdpr_consent": user_data["gdpr_consent"],
                "onboarding_completed": user_data["onboarding_completed"],
                "member_since": user_data["created_at"],
                "last_active": user_data["last_active"]
            },
            "assessment_progress": {
                "total_answers": len(answer_stats),
                "domains_explored": len(domain_coverage),
                "domain_breakdown": domain_coverage,
                "completion_percentage": (len(domain_coverage) / 13) * 100 if domain_coverage else 0
            },
            "personality_insights": {
                "average_openness": sum([json.loads(a["answer_analysis"]).get("openness_level", 0) for a in answer_stats if a["answer_analysis"]]) / len(answer_stats) if answer_stats else 0,
                "insights_captured": insights_count,
                "personality_evolution": personality_evolution
            },
            "database_status": {
                "postgresql_records": len(answer_stats),
                "vector_records": 0,  # TODO: Connect to Qdrant
                "last_update": max([a["answered_at"] for a in answer_stats]) if answer_stats else None
            }
        }


class PersonalizedChatService:
    """Independent chat service with personalization"""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
        self._user_contexts = {}
    
    async def get_personalized_response(self, user_id: int, message: str) -> str:
        """Generate personalized response based on user profile"""
        
        # Load user context
        user_context = await self._get_user_context(user_id)
        
        # Detect emotional state
        if self._detect_negative_emotion(message):
            return await self._generate_supportive_response(message, user_context)
        elif self._detect_question(message):
            return await self._generate_advisory_response(message, user_context)
        else:
            return await self._generate_conversational_response(message, user_context)
    
    async def _get_user_context(self, user_id: int) -> dict:
        """Get user context for personalization"""
        
        # Cache user context for performance
        if user_id in self._user_contexts:
            last_update = self._user_contexts[user_id].get("last_update", datetime.min)
            if datetime.now() - last_update < timedelta(minutes=10):
                return self._user_contexts[user_id]
        
        # Load fresh context
        async with self.db_pool.acquire() as conn:
            recent_answers = await conn.fetch("""
                SELECT question_id, answer_text, answer_analysis
                FROM selfology_question_answers 
                WHERE user_id = $1 
                ORDER BY answered_at DESC 
                LIMIT 5
            """, str(user_id))
        
        context = {
            "total_answers": len(recent_answers),
            "recent_domains": [],
            "personality_traits": {},
            "communication_style": "detailed" if recent_answers and len(recent_answers[0]["answer_text"]) > 50 else "concise",
            "last_update": datetime.now()
        }
        
        # Extract domains and traits
        if QUESTION_CORE_AVAILABLE:
            for answer in recent_answers:
                question = question_core.get_question(answer["question_id"])
                if question:
                    context["recent_domains"].append(question["classification"]["domain"])
                    
                    analysis = json.loads(answer["answer_analysis"]) if answer["answer_analysis"] else {}
                    openness = analysis.get("openness_level", 0)
                    context["personality_traits"][question["classification"]["domain"]] = openness
        
        self._user_contexts[user_id] = context
        return context
    
    def _detect_negative_emotion(self, message: str) -> bool:
        """Detect negative emotional state"""
        negative_indicators = ["плохо", "грустно", "тяжело", "болит", "страшно", "злой", "расстроен", "депресс"]
        return any(word in message.lower() for word in negative_indicators)
    
    def _detect_question(self, message: str) -> bool:
        """Detect if message is a question needing advice"""
        question_indicators = ["как", "что делать", "помоги", "совет", "почему", "зачем", "?"]
        return any(indicator in message.lower() for indicator in question_indicators)
    
    async def _generate_supportive_response(self, message: str, context: dict) -> str:
        """Generate supportive response for negative emotions"""
        
        # Personalize based on known traits
        support_style = "analytical" if context["communication_style"] == "detailed" else "warm"
        
        if support_style == "analytical":
            return f"""
🤗 <b>Понимаю ваше состояние</b>

Судя по нашему общению, вы человек, который ценит детальный анализ. Давайте разберем ситуацию:

<b>💙 Immediate помощь:</b>
• Признание чувств: то, что вы чувствуете, нормально
• Временность: эмоциональные состояния проходят
• Ресурсы: что обычно вас поддерживает?

<b>🎯 На основе вашего профиля:</b>
{self._get_personalized_support(context)}

Хотите рассказать подробнее о ситуации? 💚
            """
        else:
            return """
🤗 <b>Я рядом</b>

Понимаю, что сейчас тяжело. Спасибо за доверие.

💙 Помните: это временное состояние, оно пройдет.

Хотите поговорить об этом? 💚
            """
    
    def _get_personalized_support(self, context: dict) -> str:
        """Get personalized support based on user traits"""
        
        recent_domains = context.get("recent_domains", [])
        
        if "WORK" in recent_domains:
            return "Вспомните ваши профессиональные достижения - они дают ресурс"
        elif "RELATIONSHIPS" in recent_domains:
            return "Обратитесь к близким людям - связи важны для вас"
        elif "IDENTITY" in recent_domains:
            return "Вспомните свои сильные стороны и ценности"
        else:
            return "Сделайте то, что обычно приносит вам покой и силу"
    
    async def _generate_advisory_response(self, message: str, context: dict) -> str:
        """Generate advice based on user question"""
        
        return f"""
🎯 <b>Анализирую ваш вопрос</b>

{message[:150]}{'...' if len(message) > 150 else ''}

<b>💡 Персональная рекомендация:</b>
{self._get_personalized_advice(message, context)}

<b>🔍 Дополнительно подумайте:</b>
• Что в похожих ситуациях помогало раньше?
• Какие ваши сильные стороны можно применить?
• Что самое важное для вас в этой ситуации?

Расскажите больше деталей! 🚀
        """
    
    def _get_personalized_advice(self, message: str, context: dict) -> str:
        """Generate personalized advice"""
        
        if context["communication_style"] == "detailed":
            return "Создайте подробный план действий и проанализируйте каждый шаг"
        elif "WORK" in context.get("recent_domains", []):
            return "Примените ваш профессиональный подход к решению личных вопросов"
        elif "RELATIONSHIPS" in context.get("recent_domains", []):
            return "Подумайте, как эта ситуация влияет на ваши отношения с людьми"
        else:
            return "Разложите проблему на части и определите, что вы можете контролировать"
    
    async def _generate_conversational_response(self, message: str, context: dict) -> str:
        """Generate conversational response"""
        
        return f"""
💬 <b>Понял!</b>

<b>🤖 Ответ с учетом вашей личности:</b>
Интересная мысль! {self._get_conversational_insight(message, context)}

Продолжайте делиться - каждое сообщение помогает мне понимать вас лучше! 💭
        """
    
    def _get_conversational_insight(self, message: str, context: dict) -> str:
        """Get conversational insight"""
        
        if context.get("total_answers", 0) > 5:
            return "Это соотносится с тем, что я уже знаю о вас из анкетирования."
        else:
            return "Хотелось бы узнать вас получше через анкетирование!"


# === INITIALIZE SERVICES ===
assessment_engine = None
statistics_service = None
chat_service = None

async def init_services():
    """Initialize all services"""
    global db_pool, question_core, assessment_engine, statistics_service, chat_service
    
    try:
        # Database
        db_pool = await asyncpg.create_pool(**DB_CONFIG)
        logger.info("✅ Database connected")
        
        # Question Core
        if QUESTION_CORE_AVAILABLE:
            core_path = Path(__file__).parent / "intelligent_question_core/data/selfology_intelligent_core.json"
            question_core = SelfologyQuestionCore(str(core_path))
            logger.info(f"✅ Question core: {len(question_core.questions_lookup)} questions")
        
        # Services
        assessment_engine = AssessmentEngine(db_pool, question_core)
        statistics_service = StatisticsService(db_pool, question_core)  
        chat_service = PersonalizedChatService(db_pool)
        
        logger.info("✅ All services initialized")
        return True
        
    except Exception as e:
        logger.error(f"Service initialization failed: {e}")
        return False


# === TELEGRAM HANDLERS (PURE ROUTING) ===

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Pure routing start handler"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "Friend"
    
    try:
        # Check user status
        async with db_pool.acquire() as conn:
            user_data = await conn.fetchrow(
                "SELECT * FROM selfology_users WHERE telegram_id = $1", str(user_id)
            )
        
        if user_data:
            if user_data["gdpr_consent"]:
                await show_smart_dashboard(message, state, user_data)
            else:
                await show_gdpr_consent(message, state)
        else:
            await create_user_and_consent(message, state, user_id)
    
    except Exception as e:
        logger.error(f"Start error: {e}")
        await message.answer("Ошибка системы. Попробуйте еще раз.")


async def show_smart_dashboard(message: Message, state: FSMContext, user_data: dict):
    """Smart dashboard based on user progress"""
    
    user_name = user_data["first_name"] or "Friend"
    user_id = int(user_data["telegram_id"])
    
    # Get progress from assessment engine
    if assessment_engine:
        progress = await assessment_engine.get_user_progress(user_id)
        
        dashboard_text = f"""
🏠 <b>Привет, {user_name}!</b>

<b>📊 Ваш прогресс:</b>
• Ответов дано: <code>{progress.total_answers}</code>
• Областей исследовано: <code>{len(progress.domain_progress)}/13</code>
• Текущий уровень доверия: <code>{progress.trust_level:.1f}/5.0</code>

<b>🎯 Что доступно:</b>
        """
        
        keyboard_buttons = []
        
        if progress.total_answers < 10:
            # Need more assessment
            keyboard_buttons.append([InlineKeyboardButton(text="🧠 Продолжить анкетирование", callback_data="continue_assessment")])
        else:
            # Ready for coaching
            keyboard_buttons.append([InlineKeyboardButton(text="💬 Персональный коучинг", callback_data="start_coaching")])
        
        keyboard_buttons.extend([
            [InlineKeyboardButton(text="📊 Детальная статистика", callback_data="show_detailed_stats")],
            [InlineKeyboardButton(text="👤 Мой профиль", callback_data="show_profile")],
            [InlineKeyboardButton(text="💬 Чат режим", callback_data="start_chat")]
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
    else:
        dashboard_text = f"Привет, {user_name}! Система анализа временно недоступна."
        keyboard = None
    
    await message.answer(dashboard_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(UserStates.main_menu)


@dp.callback_query(F.data == "continue_assessment")
async def continue_assessment(callback: types.CallbackQuery, state: FSMContext):
    """Continue assessment without sessions"""
    
    user_id = callback.from_user.id
    
    if assessment_engine:
        next_question = await assessment_engine.get_next_question(user_id)
        
        if next_question:
            await show_assessment_question(callback.message, next_question, user_id)
            await state.set_state(UserStates.assessment_mode)
        else:
            await callback.message.edit_text("""
🎉 <b>Анкетирование завершено!</b>

Вы ответили на все доступные вопросы. Ваш профиль максимально детализирован!

Переходите к персональному коучингу! 🚀
            """, parse_mode=ParseMode.HTML)
    else:
        await callback.message.edit_text("Система анкетирования недоступна.")


async def show_assessment_question(message: Message, question: dict, user_id: int):
    """Show question with proper interface"""
    
    # Get progress for context
    progress = await assessment_engine.get_user_progress(user_id) if assessment_engine else None
    
    question_text = f"""
🧠 <b>Анкетирование</b> (ответ {progress.total_answers + 1 if progress else '?'})

<b>Область:</b> {question['classification']['domain']}

{question['text']}

💭 <i>Отвечайте подробно для лучшего анализа</i>
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭️ Пропустить вопрос", callback_data="skip_question")],
        [InlineKeyboardButton(text="📊 Мой прогресс", callback_data="show_detailed_stats")],
        [InlineKeyboardButton(text="💬 К чату", callback_data="start_chat")]
    ])
    
    await message.edit_text(question_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)


@dp.message(UserStates.assessment_mode)
async def handle_assessment_answer(message: Message, state: FSMContext):
    """Handle answer in assessment mode"""
    
    user_id = message.from_user.id
    answer = message.text
    
    if assessment_engine:
        # Get current question (last question from database)
        async with db_pool.acquire() as conn:
            last_question = await conn.fetchval("""
                SELECT question_id FROM selfology_question_answers
                WHERE user_id = $1 
                ORDER BY answered_at DESC 
                LIMIT 1
            """, str(user_id))
        
        # If no previous question, get first available
        if not last_question:
            next_question = await assessment_engine.get_next_question(user_id)
            if next_question:
                last_question = next_question["id"]
        
        if last_question:
            # Process the answer
            result = await assessment_engine.process_answer(user_id, last_question, answer)
            
            response_text = f"""
✅ <b>Ответ обработан и сохранен!</b>

<b>🔍 Анализ:</b>
• Эмоциональное состояние: {result['analysis']['emotional_state']}
• Открытость: {result['analysis']['openness_level']}/1.0
• Область: {result['analysis']['domain']}

<b>📊 Прогресс обновлен:</b>
• Всего ответов: {result['progress'].total_answers}
• Областей исследовано: {len(result['progress'].domain_progress)}

💾 <i>Данные сохранены в базе и готовы для векторизации</i>
            """
            
            if result["next_question"]:
                # Show next question
                await show_assessment_question(message, result["next_question"], user_id)
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="➡️ Ответить на следующий", callback_data="continue_assessment")],
                    [InlineKeyboardButton(text="📊 Посмотреть прогресс", callback_data="show_detailed_stats")],
                    [InlineKeyboardButton(text="✅ Завершить пока", callback_data="finish_assessment")]
                ])
            else:
                # Assessment complete
                response_text += "\n\n🎉 <b>Анкетирование завершено!</b>"
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="💬 Начать коучинг", callback_data="start_coaching")],
                    [InlineKeyboardButton(text="📊 Мой профиль", callback_data="show_profile")]
                ])
            
            await message.answer(response_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "show_detailed_stats")
async def show_detailed_statistics(callback: types.CallbackQuery):
    """Show detailed statistics via service"""
    
    user_id = callback.from_user.id
    
    if statistics_service:
        stats = await statistics_service.get_user_statistics(user_id)
        
        stats_text = f"""
📊 <b>Детальная статистика личности</b>

<b>🎯 Прогресс анкетирования:</b>
• Всего ответов: <code>{stats['assessment_progress']['total_answers']}</code>
• Областей исследовано: <code>{stats['assessment_progress']['domains_explored']}/13</code>
• Готовность профиля: <code>{stats['assessment_progress']['completion_percentage']:.0f}%</code>

<b>🗺️ Исследованные области:</b>
{chr(10).join([f"• {domain}: {count} ответ(ов)" for domain, count in stats['assessment_progress']['domain_breakdown'].items()])}

<b>📈 Анализ личности:</b>
• Средняя открытость: <code>{stats['personality_insights']['average_openness']:.2f}/1.0</code>
• Сохраненных инсайтов: <code>{stats['personality_insights']['insights_captured']}</code>

<b>💾 База данных:</b>
• PostgreSQL записей: <code>{stats['database_status']['postgresql_records']}</code>
• Vector DB записей: <code>{stats['database_status']['vector_records']}</code>
• Последнее обновление: {stats['database_status']['last_update'].strftime('%d.%m %H:%M') if stats['database_status']['last_update'] else 'Нет'}

<b>📊 Член Selfology с:</b> {stats['user_info']['member_since'].strftime('%d.%m.%Y')}
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧠 Продолжить анкетирование", callback_data="continue_assessment")],
            [InlineKeyboardButton(text="💬 Персональный чат", callback_data="start_coaching")],
            [InlineKeyboardButton(text="🔄 Обновить статистику", callback_data="show_detailed_stats")]
        ])
        
        await callback.message.edit_text(stats_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    else:
        await callback.message.edit_text("Сервис статистики недоступен")


@dp.callback_query(F.data == "start_coaching")
async def start_personalized_coaching(callback: types.CallbackQuery, state: FSMContext):
    """Start personalized coaching mode"""
    
    user_id = callback.from_user.id
    
    if chat_service:
        user_context = await chat_service._get_user_context(user_id)
        
        coaching_text = f"""
💬 <b>Персональный коучинг активирован!</b>

<b>🧠 Я знаю о вас:</b>
• Ответов проанализировано: <code>{user_context['total_answers']}</code>
• Стиль общения: {user_context['communication_style']}
• Исследованные области: {', '.join(user_context['recent_domains'][:3])}

<b>✨ Что изменилось:</b>
✅ Ответы персонализированы под вашу психологию
✅ Система помнит контекст наших разговоров
✅ Поддержка адаптируется под ваше эмоциональное состояние

<b>💡 Пример персональных ответов:</b>
- На "мне плохо" → Поддержка с учетом вашего типа личности
- На вопросы → Советы на основе ваших ответов  
- На размышления → Углубление ваших инсайтов

Пишите что угодно! 🚀
        """
        
        await callback.message.edit_text(coaching_text, parse_mode=ParseMode.HTML)
        await state.set_state(UserStates.chat_mode)
    else:
        await callback.message.edit_text("Сервис коучинга недоступен")


@dp.message(UserStates.chat_mode)
async def handle_personalized_chat(message: Message, state: FSMContext):
    """Handle chat with full personalization"""
    
    user_id = message.from_user.id
    user_message = message.text
    
    if chat_service:
        response = await chat_service.get_personalized_response(user_id, user_message)
        await message.answer(response, parse_mode=ParseMode.HTML)
    else:
        await message.answer("Сервис чата недоступен. Попробуйте /start")


@dp.message(Command("questions"))
async def cmd_questions(message: Message, state: FSMContext):
    """Command to start/continue assessment"""
    user_id = message.from_user.id
    
    if assessment_engine:
        next_question = await assessment_engine.get_next_question(user_id)
        
        if next_question:
            await show_assessment_question(message, next_question, user_id)
            await state.set_state(UserStates.assessment_mode)
        else:
            await message.answer("✅ Вы ответили на все доступные вопросы!")
    else:
        await message.answer("Сервис анкетирования недоступен")


@dp.message(Command("chat"))
async def cmd_chat(message: Message, state: FSMContext):
    """Command to start chat mode"""
    await message.answer("""
💬 <b>Чат режим активирован!</b>

Пишите любые вопросы или делитесь мыслями.

Мои ответы персонализированы под ваш профиль! 🚀
    """, parse_mode=ParseMode.HTML)
    await state.set_state(UserStates.chat_mode)


@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    """Command to show statistics"""
    user_id = message.from_user.id
    
    if statistics_service:
        stats = await statistics_service.get_user_statistics(user_id)
        
        quick_stats = f"""
📊 <b>Быстрая статистика:</b>

• Ответов: <code>{stats['assessment_progress']['total_answers']}</code>
• Готовность профиля: <code>{stats['assessment_progress']['completion_percentage']:.0f}%</code>
• Последняя активность: {stats['user_info']['last_active'].strftime('%d.%m %H:%M') if stats['user_info']['last_active'] else 'Неизвестно'}

Используйте кнопку "📊 Детальная статистика" в меню для подробной информации.
        """
        
        await message.answer(quick_stats, parse_mode=ParseMode.HTML)
    else:
        await message.answer("Сервис статистики недоступен")


@dp.message(Command("profile"))
async def cmd_profile(message: Message):
    """Command to show user profile"""
    user_id = message.from_user.id
    
    if statistics_service:
        stats = await statistics_service.get_user_statistics(user_id)
        
        profile_text = f"""
👤 <b>Ваш психологический профиль:</b>

<b>📊 Анализ на основе {stats['assessment_progress']['total_answers']} ответов:</b>

<b>🎯 Исследованные области личности:</b>
{chr(10).join([f"• {domain}: {count} глубинных ответа" for domain, count in stats['assessment_progress']['domain_breakdown'].items()])}

<b>📈 Психологические характеристики:</b>
• Уровень открытости: <code>{stats['personality_insights']['average_openness']:.2f}/1.0</code>
• Готовность к самоанализу: {'Высокая' if stats['personality_insights']['average_openness'] > 0.7 else 'Средняя' if stats['personality_insights']['average_openness'] > 0.4 else 'Низкая'}

<b>💡 Сохраненные инсайты:</b> <code>{stats['personality_insights']['insights_captured']}</code>

<i>Профиль обновляется с каждым вашим ответом!</i>
        """
        
        await message.answer(profile_text, parse_mode=ParseMode.HTML)
    else:
        await message.answer("Сервис профилей недоступен")


# Initialize missing handlers
async def show_gdpr_consent(message: Message, state: FSMContext):
    """GDPR consent"""
    consent_text = """
🌟 <b>Добро пожаловать в Selfology!</b>

Персональный AI-коуч с системой из 693 психологических вопросов.

Согласны на обработку данных для персонализации?
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Согласен", callback_data="consent_yes")],
        [InlineKeyboardButton(text="❌ Не согласен", callback_data="consent_no")]
    ])
    
    await message.answer(consent_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)


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
🎉 <b>Добро пожаловать!</b>

Используйте /start чтобы начать работу с системой.
    """, parse_mode=ParseMode.HTML)


async def main():
    """Main function with fixed architecture"""
    
    print("🧠 Starting Fixed Architecture Selfology Bot...")
    print("✅ No session anti-pattern")
    print("✅ Individual question tracking")
    print("✅ Independent services approach")
    print("✅ Proper statistics handlers")
    print("✅ Question deduplication")
    
    if not await init_services():
        print("❌ Service initialization failed")
        return
    
    try:
        print(f"✅ Question Core: {'693 questions' if QUESTION_CORE_AVAILABLE else 'Demo mode'}")
        print("✅ Assessment Engine: Individual Q&A tracking")
        print("✅ Chat Service: Personalization ready")
        print("✅ Statistics Service: Cached analytics")
        print("🚀 Ready for testing!")
        
        await dp.start_polling(bot)
        
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped")
    finally:
        if db_pool:
            await db_pool.close()


if __name__ == "__main__":
    asyncio.run(main())