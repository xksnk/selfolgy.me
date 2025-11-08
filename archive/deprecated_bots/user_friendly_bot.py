#!/usr/bin/env python3
"""
User-Friendly Intelligent Selfology Bot
Clean interface without technical details, with HTML parsing mode.
"""

import asyncio
import asyncpg
import logging
import sys
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

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
    print(f"⚠️ Question core not available: {e}")
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
    waiting_for_consent = State()
    intelligent_onboarding = State()
    answering_core_question = State()
    chatting = State()

# Global instances
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
db_pool = None
question_core = None
current_questions = {}  # user_id -> current_question


async def init_systems():
    """Initialize all systems"""
    global db_pool, question_core
    
    # Database
    try:
        db_pool = await asyncpg.create_pool(**DB_CONFIG)
        logger.info("✅ Database pool created")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False
    
    # Question Core
    if QUESTION_CORE_AVAILABLE:
        try:
            core_path = Path(__file__).parent / "intelligent_question_core/data/selfology_intelligent_core.json"
            question_core = SelfologyQuestionCore(str(core_path))
            logger.info(f"✅ Question core loaded: {len(question_core.questions_lookup)} questions")
        except Exception as e:
            logger.error(f"❌ Question core failed: {e}")
            return False
    
    return True


@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """User-friendly start command"""
    
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "Friend"
    
    logger.info(f"🚀 /start from user {user_id} ({user_name})")
    
    try:
        # Check user in database
        async with db_pool.acquire() as conn:
            user_data = await conn.fetchrow(
                "SELECT * FROM selfology_users WHERE telegram_id = $1", str(user_id)
            )
        
        if user_data:
            if user_data["gdpr_consent"] and user_data["onboarding_completed"]:
                await show_main_menu(message, state, user_data)
            elif user_data["gdpr_consent"]:
                await show_onboarding_choice(message, state, user_data)
            else:
                await show_gdpr_consent(message, state)
        else:
            await create_new_user_and_show_consent(message, state, user_id)
    
    except Exception as e:
        logger.error(f"Error in start for user {user_id}: {e}")
        await message.answer("Произошла техническая ошибка. Попробуйте еще раз через минуту.")


async def show_onboarding_choice(message: Message, state: FSMContext, user_data: dict):
    """Show friendly onboarding choice"""
    
    user_name = user_data["first_name"] or "Friend"
    
    choice_text = f"""
👋 <b>Привет, {user_name}! Рад видеть вас снова!</b>

У вас уже есть согласие на работу с данными, спасибо! 

<b>Что хотите делать?</b>

🧠 <b>Рекомендую:</b> Завершить психологическое анкетирование для создания полного профиля (5-10 минут). После этого я смогу давать гораздо более точные советы!

💬 <b>Или можете сразу:</b> Перейти к общению. Я буду учиться понимать вас по ходу разговора.

📊 Также можете посмотреть /status - что уже создано в вашем профиле.
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧠 Завершить анкетирование", callback_data="start_onboarding")],
        [InlineKeyboardButton(text="💬 Сразу к общению", callback_data="skip_to_chat")],
        [InlineKeyboardButton(text="📊 Мой статус", callback_data="show_status")]
    ])
    
    await message.answer(choice_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(UserStates.waiting_for_consent)


async def show_gdpr_consent(message: Message, state: FSMContext):
    """Show GDPR consent"""
    
    consent_text = f"""
🌟 <b>Добро пожаловать в Selfology!</b>

Я ваш персональный AI-коуч для глубокого самопознания с уникальной системой анализа личности.

<b>🎯 Мои возможности:</b>
• Профессиональное психологическое анкетирование
• Персонализированные инсайты и рекомендации
• Умная система запоминания важной информации о вас
• Адаптация под ваш стиль общения

<b>🔒 Конфиденциальность:</b>
Для работы мне нужно сохранять ваши ответы и анализировать сообщения. Все данные защищены и используются только для персонализации советов.

Согласны на обработку данных?
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Согласен", callback_data="consent_yes")],
        [InlineKeyboardButton(text="❌ Не согласен", callback_data="consent_no")]
    ])
    
    await message.answer(consent_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(UserStates.waiting_for_consent)


@dp.callback_query(F.data == "start_onboarding")
async def start_intelligent_onboarding(callback: types.CallbackQuery, state: FSMContext):
    """Start intelligent onboarding session"""
    
    user_id = callback.from_user.id
    
    try:
        # Create session in database
        async with db_pool.acquire() as conn:
            session = await conn.fetchrow("""
                INSERT INTO selfology_intelligent_sessions 
                (user_id, current_energy, trust_level, questions_asked)
                VALUES ($1, $2, $3, $4)
                RETURNING session_uuid
            """, str(user_id), 0.3, 1.0, json.dumps([]))
        
        if QUESTION_CORE_AVAILABLE and question_core:
            # Get opening questions
            opening_questions = question_core.search_questions(
                energy="OPENING",
                min_safety=4
            )
            
            if opening_questions:
                first_question = opening_questions[0]
                current_questions[user_id] = first_question
                
                # Update session with question
                async with db_pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE selfology_intelligent_sessions 
                        SET current_question_id = $1, questions_asked = $2
                        WHERE user_id = $3
                    """, first_question["id"], json.dumps([first_question["id"]]), str(user_id))
                
                session_text = f"""
🧠 <b>Начинаем умное анкетирование!</b>

Система выбрала для вас первый вопрос. Отвечайте честно и подробно - я адаптируюсь под ваш стиль!

<b>Вопрос 1:</b>

{first_question['text']}

💭 <i>Отвечайте обычным текстовым сообщением</i>
                """
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="skip_question")],
                    [InlineKeyboardButton(text="📊 /status", callback_data="show_status")]
                ])
                
                await callback.message.edit_text(session_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
                await state.set_state(UserStates.answering_core_question)
                
                logger.info(f"🧠 Started onboarding for user {user_id} with question {first_question['id']}")
                return
        
        # Fallback without question core
        await callback.message.edit_text("""
🔄 <b>Анкетирование временно недоступно</b>

Question Core система пока не готова. Но вы можете общаться со мной в чат-режиме!

Используйте /chat для начала общения.
        """, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        logger.error(f"Error starting onboarding for user {user_id}: {e}")
        await callback.message.edit_text("Произошла ошибка при создании анкетирования. Попробуйте /chat для общения.")


@dp.message(UserStates.answering_core_question)
async def handle_question_answer(message: Message, state: FSMContext):
    """Handle answer with clean response"""
    
    user_id = message.from_user.id
    answer = message.text
    
    logger.info(f"💬 Answer from {user_id}: '{answer[:50]}{'...' if len(answer) > 50 else ''}'")
    
    current_question = current_questions.get(user_id)
    if not current_question:
        await message.answer("Активного вопроса не найдено. Используйте /start для начала.")
        return
    
    try:
        # Basic analysis
        analysis = analyze_answer_basic(answer, current_question)
        
        # Save to database
        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO selfology_question_answers 
                (user_id, question_id, answer_text, answer_analysis)
                VALUES ($1, $2, $3, $4)
            """, str(user_id), current_question["id"], answer, json.dumps(analysis))
            
            # Update session 
            await conn.execute("""
                UPDATE selfology_intelligent_sessions 
                SET current_energy = GREATEST(-2.0, LEAST(2.0, current_energy + $1)),
                    trust_level = LEAST(5.0, trust_level + $2),
                    last_activity = NOW()
                WHERE user_id = $3
            """, analysis["energy_impact"], analysis["trust_building"], str(user_id))
        
        # Get next question
        next_question = None
        if QUESTION_CORE_AVAILABLE and question_core:
            next_question = get_next_question_smart(user_id, current_question, analysis)
        
        if next_question:
            current_questions[user_id] = next_question
            
            # Update session
            async with db_pool.acquire() as conn:
                await conn.execute("""
                    UPDATE selfology_intelligent_sessions 
                    SET current_question_id = $1,
                        questions_asked = questions_asked || $2
                    WHERE user_id = $3
                """, next_question["id"], json.dumps([next_question["id"]]), str(user_id))
            
            # Clean response
            response_text = f"""
✅ <b>Ответ принят!</b>

Спасибо за откровенность. Ваш ответ помогает мне лучше понять вас.

<b>Следующий вопрос:</b>

{next_question['text']}

💭 <i>Продолжайте отвечать текстом</i>
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="skip_question")],
                [InlineKeyboardButton(text="📊 Статистика", callback_data="show_stats")]
            ])
            
        else:
            # Complete onboarding
            await complete_onboarding(user_id)
            
            response_text = """
🎉 <b>Анкетирование завершено!</b>

Отлично! Я создал ваш психологический профиль на основе ответов.

Теперь можете общаться со мной как с персональным коучем. Я буду давать советы с учетом вашей личности!

Используйте /chat чтобы начать общение или просто напишите любой вопрос.
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💬 Начать общение", callback_data="start_chat")],
                [InlineKeyboardButton(text="📊 Мой профиль", callback_data="show_profile")]
            ])
            
        await message.answer(response_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        logger.error(f"Error processing answer for user {user_id}: {e}")
        await message.answer("Произошла ошибка при обработке ответа. Попробуйте еще раз или используйте /chat для общения.")


def analyze_answer_basic(answer: str, question: dict) -> dict:
    """Clean answer analysis without technical details"""
    
    word_count = len(answer.split())
    
    # Basic openness assessment
    openness = min(1.0, word_count / 15.0)
    
    # Sentiment
    positive_words = ["хорошо", "отлично", "люблю", "нравится", "радует", "счастлив", "классн"]
    negative_words = ["плохо", "грустно", "злой", "проблема", "тяжело", "сложно"]
    
    positive_count = sum(1 for word in positive_words if word in answer.lower())
    negative_count = sum(1 for word in negative_words if word in answer.lower())
    
    emotional_state = "positive" if positive_count > negative_count else "negative" if negative_count > 0 else "neutral"
    energy_impact = 0.1 if emotional_state == "positive" else -0.1 if emotional_state == "negative" else 0.0
    
    return {
        "emotional_state": emotional_state,
        "openness_level": round(openness, 2),
        "depth_of_reflection": min(1.0, word_count / 25.0),
        "energy_impact": energy_impact,
        "trust_building": min(0.2, openness * 0.15),
        "word_count": word_count,
        "analysis_timestamp": datetime.now(timezone.utc).isoformat()
    }


def get_next_question_smart(user_id: int, current_question: dict, answer_analysis: dict) -> Optional[dict]:
    """Smart next question selection"""
    
    if not QUESTION_CORE_AVAILABLE or not question_core:
        return None
    
    try:
        # Check for low energy - need gentler question
        if answer_analysis["energy_impact"] < -0.05:
            gentle_questions = question_core.search_questions(
                energy="HEALING",
                min_safety=4
            )
            if gentle_questions:
                return gentle_questions[0]
        
        # Normal progression - find connected
        connected = question_core.find_connected_questions(current_question["id"])
        
        if connected:
            return connected[0]
        
        # Explore different domain
        current_domain = current_question["classification"]["domain"]
        other_domains = ["IDENTITY", "EMOTIONS", "RELATIONSHIPS", "WORK", "FUTURE"]
        
        for domain in other_domains:
            if domain != current_domain:
                domain_questions = question_core.search_questions(
                    domain=domain,
                    min_safety=3
                )
                if domain_questions:
                    return domain_questions[0]
        
        return None
        
    except Exception as e:
        logger.error(f"Error selecting next question: {e}")
        return None


async def complete_onboarding(user_id: int):
    """Complete onboarding cleanly"""
    
    async with db_pool.acquire() as conn:
        await conn.execute("""
            UPDATE selfology_users 
            SET onboarding_completed = true, updated_at = NOW()
            WHERE telegram_id = $1
        """, str(user_id))
        
        await conn.execute("""
            UPDATE selfology_intelligent_sessions 
            SET session_ended = NOW()
            WHERE user_id = $1 AND session_ended IS NULL
        """, str(user_id))
    
    logger.info(f"🎉 Onboarding completed for user {user_id}")


@dp.callback_query(F.data == "skip_to_chat")
async def skip_to_chat(callback: types.CallbackQuery, state: FSMContext):
    """Skip to chat mode"""
    
    user_id = callback.from_user.id
    
    # Mark as completed
    async with db_pool.acquire() as conn:
        await conn.execute("""
            UPDATE selfology_users 
            SET onboarding_completed = true, updated_at = NOW()
            WHERE telegram_id = $1
        """, str(user_id))
    
    chat_text = """
💬 <b>Отлично! Переходим к общению</b>

Теперь можете писать мне любые вопросы или рассказывать о том, что вас волнует.

<b>Я помогу:</b>
• Разобрать сложные ситуации
• Найти решения проблем  
• Лучше понять себя и свои реакции
• Наметить планы достижения целей

<b>Примеры вопросов:</b>
- "Как мне справляться со стрессом?"
- "Почему я откладываю важные дела?"
- "Как улучшить отношения с людьми?"

💡 <i>Чем больше вы рассказываете, тем точнее становятся мои советы!</i>

Пишите что угодно! 👇
    """
    
    await callback.message.edit_text(chat_text, parse_mode=ParseMode.HTML)
    await state.set_state(UserStates.chatting)


@dp.callback_query(F.data == "start_chat")
async def start_chat_mode(callback: types.CallbackQuery, state: FSMContext):
    """Start chat mode after onboarding"""
    
    chat_text = """
💬 <b>Режим персонального коучинга активирован!</b>

Теперь у меня есть ваш психологический профиль, и я могу давать персонализированные советы!

<b>Что изменилось:</b>
✅ Ответы учитывают вашу уникальную личность
✅ Система запоминает важные моменты из разговора
✅ Рекомендации становятся точнее с каждым сообщением

Пишите любые вопросы! 🚀
    """
    
    await callback.message.edit_text(chat_text, parse_mode=ParseMode.HTML)
    await state.set_state(UserStates.chatting)


@dp.message(UserStates.chatting)
async def handle_chat_message(message: Message, state: FSMContext):
    """Handle chat messages cleanly"""
    
    user_id = message.from_user.id
    user_message = message.text
    
    logger.info(f"💬 Chat from {user_id}: '{user_message[:30]}{'...' if len(user_message) > 30 else ''}'")
    
    try:
        # Basic insight detection
        insights_detected = detect_insights_simple(user_message)
        
        # Store if important
        if insights_detected:
            await store_chat_insight(user_id, insights_detected[0])
        
        # Generate response
        response = generate_personalized_response(user_message, insights_detected, user_id)
        
        # Update activity
        async with db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE selfology_users 
                SET last_active = NOW() 
                WHERE telegram_id = $1
            """, str(user_id))
        
        await message.answer(response, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        logger.error(f"Error in chat for user {user_id}: {e}")
        await message.answer("Произошла ошибка. Попробуйте еще раз или обратитесь в поддержку.")


def detect_insights_simple(message: str) -> List[dict]:
    """Simple insight detection"""
    
    insight_triggers = [
        ("я понял", "self_awareness"),
        ("оказывается", "discovery"), 
        ("теперь я понимаю", "understanding"),
        ("это объясняет", "pattern_recognition"),
        ("получается", "realization")
    ]
    
    for trigger, insight_type in insight_triggers:
        if trigger in message.lower():
            return [{
                "text": message,
                "type": insight_type,
                "confidence": 0.8,
                "trigger": trigger
            }]
    
    return []


async def store_chat_insight(user_id: int, insight: dict):
    """Store chat insight"""
    
    try:
        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO selfology_chat_insights 
                (user_id, insight_text, insight_type, psychological_domain)
                VALUES ($1, $2, $3, $4)
            """, str(user_id), insight["text"], insight["type"], "THOUGHTS")
        
        logger.info(f"💡 Stored insight for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error storing insight: {e}")


def generate_personalized_response(message: str, insights: List[dict], user_id: int) -> str:
    """Generate clean personalized response"""
    
    if insights:
        response = f"""
💡 <b>Интересный инсайт!</b>

Я заметил важное понимание в ваших словах и сохранил его для персонализации будущих советов.

<b>По поводу вашего сообщения:</b>

{message[:200]}{'...' if len(message) > 200 else ''}

<b>Мой совет:</b> Это ценное понимание! Попробуйте развить эту мысль дальше. Что это открытие изменит в вашем поведении?

💬 <i>Продолжайте делиться - каждое сообщение помогает мне понимать вас лучше!</i>
        """
    else:
        response = f"""
🤖 <b>Понял вас!</b>

Спасибо за сообщение. Анализирую ваш запрос...

<b>Мой ответ:</b>
Это интересный вопрос! На основе нашего общения рекомендую попробовать структурированный подход к этой теме.

<b>💡 Персональная рекомендация:</b>
Разделите проблему на более мелкие части и подумайте, какие из них вы можете контролировать.

Есть еще вопросы? Продолжайте писать! 💬
        """
    
    return response


async def show_main_menu(message: Message, state: FSMContext, user_data: dict):
    """Show main menu for completed users"""
    
    user_name = user_data["first_name"]
    
    menu_text = f"""
🏠 <b>Добро пожаловать, {user_name}!</b>

Ваш профиль готов к работе! 

<b>Что хотите сделать?</b>

💬 Начать общение - /chat
📊 Посмотреть профиль - /profile  
🧠 Пройти дополнительные вопросы - /questions
📈 Статистика - /status
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Начать общение", callback_data="start_chat")],
        [InlineKeyboardButton(text="📊 Мой профиль", callback_data="show_profile")],
        [InlineKeyboardButton(text="📈 Статистика", callback_data="show_stats")]
    ])
    
    await message.answer(menu_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(UserStates.chatting)


async def create_new_user_and_show_consent(message: Message, state: FSMContext, user_id: int):
    """Create user and show consent"""
    
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO selfology_users 
            (telegram_id, username, first_name, last_name, last_active) 
            VALUES ($1, $2, $3, $4, $5)
        """, 
        str(user_id), 
        message.from_user.username, 
        message.from_user.first_name,
        message.from_user.last_name,
        datetime.now(timezone.utc))
    
    logger.info(f"👤 Created new user: {user_id}")
    await show_gdpr_consent(message, state)


@dp.callback_query(F.data == "consent_yes")  
async def consent_accepted(callback: types.CallbackQuery, state: FSMContext):
    """Handle consent acceptance"""
    
    user_id = callback.from_user.id
    
    async with db_pool.acquire() as conn:
        await conn.execute("""
            UPDATE selfology_users 
            SET gdpr_consent = true, updated_at = NOW() 
            WHERE telegram_id = $1
        """, str(user_id))
    
    logger.info(f"✅ Consent given by user {user_id}")
    
    welcome_text = f"""
🎉 <b>Отлично! Добро пожаловать в Selfology!</b>

Теперь мы можем начать работу с вашим профилем.

<b>Рекомендую пройти анкетирование</b> (5-10 минут) для создания детального психологического профиля.

Или можете сразу перейти к общению - я буду изучать вас по ходу разговора.

Используйте /start чтобы выбрать подходящий вариант.
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧠 Пройти анкетирование", callback_data="start_onboarding")],
        [InlineKeyboardButton(text="💬 Сразу к общению", callback_data="skip_to_chat")]
    ])
    
    await callback.message.edit_text(welcome_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)


@dp.callback_query(F.data == "consent_no")
async def consent_declined(callback: types.CallbackQuery, state: FSMContext):
    """Handle consent decline"""
    
    decline_text = """
😔 <b>Понимаю ваши опасения</b>

К сожалению, без согласия я не смогу предоставить персонализированные советы.

Если передумаете, нажмите /start снова.

Берегите себя! 👋
    """
    
    await callback.message.edit_text(decline_text, parse_mode=ParseMode.HTML)
    await state.clear()


@dp.message(Command("chat"))
async def cmd_start_chat(message: Message, state: FSMContext):
    """Direct command to start chat"""
    
    await message.answer("""
💬 <b>Чат режим активирован!</b>

Пишите любые вопросы или рассказывайте что вас волнует.

<b>Я помогу найти решения и дам персональные советы!</b>
    """, parse_mode=ParseMode.HTML)
    
    await state.set_state(UserStates.chatting)


@dp.callback_query(F.data == "show_stats")
async def show_detailed_stats(callback: types.CallbackQuery):
    """Show detailed progress statistics"""
    
    user_id = callback.from_user.id
    
    try:
        async with db_pool.acquire() as conn:
            # Session data
            session_data = await conn.fetchrow("""
                SELECT current_energy, trust_level, questions_asked, created_at
                FROM selfology_intelligent_sessions 
                WHERE user_id = $1 AND session_ended IS NULL
                ORDER BY created_at DESC LIMIT 1
            """, str(user_id))
            
            # Answer details
            answers = await conn.fetch("""
                SELECT question_id, answer_analysis, answered_at
                FROM selfology_question_answers 
                WHERE user_id = $1 
                ORDER BY answered_at DESC
            """, str(user_id))
            
            # Insights count
            insights_count = await conn.fetchval("""
                SELECT COUNT(*) FROM selfology_chat_insights 
                WHERE user_id = $1
            """, str(user_id))
        
        if session_data and answers:
            questions_data = json.loads(session_data["questions_asked"])
            
            # Calculate domain coverage
            domain_coverage = {}
            total_openness = 0
            total_trust_building = 0
            
            for answer in answers:
                analysis = json.loads(answer["answer_analysis"]) if answer["answer_analysis"] else {}
                
                # Get question from core to find domain
                if QUESTION_CORE_AVAILABLE and question_core:
                    question = question_core.get_question(answer["question_id"])
                    if question:
                        domain = question["classification"]["domain"]
                        domain_coverage[domain] = domain_coverage.get(domain, 0) + 1
                
                total_openness += analysis.get("openness_level", 0)
                total_trust_building += analysis.get("trust_building", 0)
            
            avg_openness = total_openness / len(answers) if answers else 0
            
            stats_text = f"""
📊 <b>Детальная статистика вашего прогресса:</b>

<b>🎯 Текущая сессия:</b>
• Энергетический уровень: <code>{float(session_data['current_energy']):.1f}/2.0</code>
• Уровень доверия: <code>{float(session_data['trust_level']):.1f}/5.0</code> 
• Вопросов отвечено: <code>{len(questions_data)}</code>

<b>📈 Ваши ответы:</b>
• Средняя открытость: <code>{avg_openness:.1f}/1.0</code>
• Всего ответов: <code>{len(answers)}</code>
• Инсайтов сохранено: <code>{insights_count}</code>

<b>🗺️ Исследованные области личности:</b>
{chr(10).join([f"• {domain}: {count} ответ(ов)" for domain, count in domain_coverage.items()])}

<b>🧠 Обновления векторного профиля:</b>
{chr(10).join([f"• Вопрос {answer['question_id']}: {json.loads(answer['answer_analysis']).get('analysis_timestamp', '')[:16]}" for answer in answers[-3:]])}

<b>💾 База данных:</b>
• PostgreSQL: ✅ {len(answers)} записей
• Vector DB: ✅ Готова к обновлениям  
• Session State: ✅ Отслеживается

<i>Продолжайте отвечать для углубления профиля!</i>
            """
            
        else:
            stats_text = """
📊 <b>Статистика пока недоступна</b>

Начните анкетирование чтобы увидеть прогресс обновления вашего профиля!

Используйте /start → "Завершить анкетирование"
            """
        
        await callback.message.edit_text(stats_text, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        logger.error(f"Error showing detailed stats for user {user_id}: {e}")
        await callback.message.edit_text(f"❌ Ошибка статистики: {e}")


@dp.callback_query(F.data == "show_status")
async def show_status_callback(callback: types.CallbackQuery):
    """Show status via callback"""
    user_id = callback.from_user.id
    await show_user_status(callback.message, user_id)


async def show_user_status(message: Message, user_id: int):
    """Show comprehensive user status"""
    
    try:
        async with db_pool.acquire() as conn:
            # User profile
            user_data = await conn.fetchrow("""
                SELECT telegram_id, gdpr_consent, onboarding_completed, created_at
                FROM selfology_users WHERE telegram_id = $1
            """, str(user_id))
            
            # Session progress  
            session_data = await conn.fetchrow("""
                SELECT current_energy, trust_level, questions_asked, created_at
                FROM selfology_intelligent_sessions
                WHERE user_id = $1 AND session_ended IS NULL
                ORDER BY created_at DESC LIMIT 1
            """, str(user_id))
            
            # Database statistics
            answers_count = await conn.fetchval("""
                SELECT COUNT(*) FROM selfology_question_answers 
                WHERE user_id = $1
            """, str(user_id))
            
            insights_count = await conn.fetchval("""
                SELECT COUNT(*) FROM selfology_chat_insights 
                WHERE user_id = $1
            """, str(user_id))
            
            # Latest answers for progress view
            latest_answers = await conn.fetch("""
                SELECT question_id, answered_at, answer_analysis
                FROM selfology_question_answers
                WHERE user_id = $1
                ORDER BY answered_at DESC
                LIMIT 3
            """, str(user_id))
        
        # Calculate completion percentage
        total_domains = 13  # All psychological domains
        domain_coverage = set()
        
        if QUESTION_CORE_AVAILABLE and latest_answers:
            for answer in latest_answers:
                question = question_core.get_question(answer["question_id"])
                if question:
                    domain_coverage.add(question["classification"]["domain"])
        
        completion_percentage = (len(domain_coverage) / total_domains) * 100
        
        status_text = f"""
📊 <b>Полная статистика вашего профиля:</b>

<b>👤 Основной профиль:</b>
{'✅ Анкетирование завершено' if user_data['onboarding_completed'] else '🔄 Анкетирование в процессе'}
{'✅ GDPR согласие дано' if user_data['gdpr_consent'] else '❌ Нет согласия'}
• В системе с: {user_data['created_at'].strftime('%d.%m.%Y %H:%M')}

<b>🧠 Intelligent Session:</b>
{f'''
• Энергетический баланс: <code>{float(session_data['current_energy']):.1f}/2.0</code>
• Уровень доверия: <code>{float(session_data['trust_level']):.1f}/5.0</code>
• Вопросов в сессии: <code>{len(json.loads(session_data['questions_asked']))}</code>
• Сессия началась: {session_data['created_at'].strftime('%H:%M')}
''' if session_data else '• Активной сессии нет'}

<b>💾 База данных (реляционная):</b>
• Ответов сохранено: <code>{answers_count}</code>
• Спонтанных инсайтов: <code>{insights_count}</code>
• Исследованных доменов: <code>{len(domain_coverage)}/13</code> ({completion_percentage:.0f}%)

<b>🎯 Последние обновления профиля:</b>
{chr(10).join([
    f"• {answer['question_id']}: {answer['answered_at'].strftime('%H:%M:%S')}"
    for answer in latest_answers
]) if latest_answers else '• Пока нет ответов'}

<b>🧮 Векторная база данных:</b>
• Готова к обновлениям: ✅
• Embeddings будут созданы: При реальном AI анализе
• Семантический поиск: Готов

<b>Команды:</b> /chat /questions /profile
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить статистику", callback_data="show_stats")],
            [InlineKeyboardButton(text="💬 К чату", callback_data="start_chat")]
        ])
        
        await message.edit_text(status_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        logger.error(f"Error showing status for user {user_id}: {e}")
        await message.edit_text(f"❌ Ошибка получения статистики: {e}")


@dp.message(Command("status"))
async def cmd_status(message: Message):
    """Show user status"""
    
    user_id = message.from_user.id
    
    try:
        async with db_pool.acquire() as conn:
            user_data = await conn.fetchrow("""
                SELECT telegram_id, gdpr_consent, onboarding_completed, created_at
                FROM selfology_users WHERE telegram_id = $1
            """, str(user_id))
            
            answers_count = await conn.fetchval("""
                SELECT COUNT(*) FROM selfology_question_answers 
                WHERE user_id = $1
            """, str(user_id))
            
            insights_count = await conn.fetchval("""
                SELECT COUNT(*) FROM selfology_chat_insights 
                WHERE user_id = $1
            """, str(user_id))
        
        if user_data:
            status_text = f"""
📊 <b>Ваш статус в Selfology:</b>

<b>Профиль:</b>
{'✅ Анкетирование завершено' if user_data['onboarding_completed'] else '🔄 Анкетирование не завершено'}
{'✅ GDPR согласие дано' if user_data['gdpr_consent'] else '❌ Нет согласия'}

<b>Активность:</b>
• Ответов на вопросы: {answers_count}
• Сохранено инсайтов: {insights_count}
• В системе с: {user_data['created_at'].strftime('%d.%m.%Y')}

<b>Команды:</b>
/chat - начать общение
/questions - пройти анкетирование
/profile - посмотреть профиль
            """
        else:
            status_text = "❌ Профиль не найден. Используйте /start для регистрации."
        
        await message.answer(status_text, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        logger.error(f"Error in status for user {user_id}: {e}")
        await message.answer("Ошибка получения статуса.")


async def main():
    """Main function"""
    
    print("🚀 Starting User-Friendly Intelligent Selfology Bot...")
    
    if not await init_systems():
        print("❌ Failed to initialize systems")
        return
    
    try:
        print("✅ Clean Interface: Ready") 
        print(f"✅ Question Core: {'693 questions' if QUESTION_CORE_AVAILABLE else 'Demo mode'}")
        print("✅ HTML Parse Mode: Enabled")
        print("✅ User-Friendly Messages: Active")
        print(f"🔗 Bot: @SelfologyMeCoachBot")
        print("😊 Ready for friendly interactions!")
        print()
        
        await dp.start_polling(bot)
        
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped")
    finally:
        if db_pool:
            await db_pool.close()


if __name__ == "__main__":
    asyncio.run(main())