#!/usr/bin/env python3
"""
Simple Selfology Telegram Bot for Testing
"""

import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN = "8197893707:AAEbGC7r_4GGWXvgah-q-mLw5pp7YIxhK9g"

# States
class UserStates(StatesGroup):
    waiting_for_consent = State()
    onboarding = State()
    chatting = State()

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Simple user storage (in memory for testing)
users_db = {}

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command"""
    
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "Friend"
    
    # Check if user exists
    if user_id not in users_db:
        # New user - show GDPR consent
        users_db[user_id] = {
            "id": user_id,
            "name": user_name,
            "username": message.from_user.username,
            "consent": False,
            "onboarded": False
        }
        
        await show_gdpr_consent(message, state)
    else:
        # Existing user - show main menu
        await show_main_menu(message, state)

async def show_gdpr_consent(message: Message, state: FSMContext):
    """Show GDPR consent form"""
    
    consent_text = f"""
🌟 Добро пожаловать в Selfology!

Привет! Я — ваш персональный AI-коуч для глубокого самопознания. 

🎯 **Что я умею:**
✅ Психологический анализ личности (Big Five)
✅ Персонализированные инсайты и советы
✅ Умный дневник с выявлением паттернов
✅ Трекинг целей и прогресса

🔒 **Обработка данных:**
Для работы мне нужно обрабатывать ваши сообщения и ответы на тесты. 
Все данные хранятся безопасно и используются только для персонализации.

Согласны на обработку данных?
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Согласен", callback_data="consent_yes")],
        [InlineKeyboardButton(text="❌ Не согласен", callback_data="consent_no")],
        [InlineKeyboardButton(text="📋 Подробнее", callback_data="consent_details")]
    ])
    
    await message.answer(consent_text, reply_markup=keyboard)
    await state.set_state(UserStates.waiting_for_consent)

@dp.callback_query(F.data == "consent_yes")
async def consent_accepted(callback: types.CallbackQuery, state: FSMContext):
    """Handle consent acceptance"""
    
    user_id = callback.from_user.id
    users_db[user_id]["consent"] = True
    
    welcome_text = """
🎉 Отлично! Добро пожаловать в Selfology!

Давайте начнем ваше путешествие самопознания. 

**Первый шаг** — пройти быструю психологическую оценку (5-7 минут):
• Определим ваши основные личностные черты
• Выявим жизненные ценности и приоритеты  
• Настроим персонализированные рекомендации

После этого вы сможете:
💬 Общаться со мной как с личным коучем
📊 Получать инсайты о себе
🎯 Отслеживать прогресс по целям
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Начать оценку", callback_data="start_assessment")],
        [InlineKeyboardButton(text="💬 Просто поговорить", callback_data="start_chat")]
    ])
    
    await callback.message.edit_text(welcome_text, reply_markup=keyboard)
    await state.set_state(UserStates.onboarding)

@dp.callback_query(F.data == "consent_no")
async def consent_declined(callback: types.CallbackQuery, state: FSMContext):
    """Handle consent decline"""
    
    decline_text = """
😔 Понимаю ваши опасения по поводу конфиденциальности.

К сожалению, без согласия на обработку данных я не смогу предоставить персонализированный коучинг.

Если передумаете, просто нажмите /start снова.

Берегите себя! 👋
    """
    
    await callback.message.edit_text(decline_text)
    await state.clear()

@dp.callback_query(F.data == "consent_details")
async def show_consent_details(callback: types.CallbackQuery):
    """Show detailed consent information"""
    
    details_text = """
📋 **Подробная информация о обработке данных**

**Какие данные обрабатываются:**
• Telegram ID и имя пользователя
• Ответы на психологические тесты
• Сообщения в чате для анализа контекста
• Аналитические данные о прогрессе

**Как данные защищены:**
🔒 Шифрование при передаче и хранении
🏠 Данные не покидают наши серверы
🚫 Никогда не передаем третьим лицам
♻️ Можете удалить в любой момент

**Цель обработки:**
Предоставление персонализированного AI-коучинга для вашего развития

**Ваши права:**
• Просмотр всех данных (команда /export)
• Удаление данных (команда /delete)
• Отзыв согласия в любой момент

Полная политика: https://selfology.me/privacy
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Принять", callback_data="consent_yes")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data="consent_no")]
    ])
    
    await callback.message.edit_text(details_text, reply_markup=keyboard)

@dp.callback_query(F.data == "start_assessment")
async def start_assessment(callback: types.CallbackQuery, state: FSMContext):
    """Start psychological assessment"""
    
    assessment_text = """
🧠 **Психологическая оценка личности**

Сейчас я задам вам несколько вопросов, чтобы понять:
• Ваши основные черты личности (Big Five)
• Жизненные ценности и приоритеты
• Текущие цели и мотивацию

Это займет 5-7 минут и поможет мне давать вам более точные советы.

**Первый вопрос:**
Насколько вы согласны с утверждением: "Я часто экспериментирую с новыми идеями и подходами"
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💯 Полностью согласен", callback_data="answer_5")],
        [InlineKeyboardButton(text="✅ Скорее согласен", callback_data="answer_4")],
        [InlineKeyboardButton(text="🤔 Нейтрально", callback_data="answer_3")],
        [InlineKeyboardButton(text="❌ Скорее не согласен", callback_data="answer_2")],
        [InlineKeyboardButton(text="🚫 Совершенно не согласен", callback_data="answer_1")]
    ])
    
    await callback.message.edit_text(assessment_text, reply_markup=keyboard)

@dp.callback_query(F.data.startswith("answer_"))
async def handle_assessment_answer(callback: types.CallbackQuery, state: FSMContext):
    """Handle assessment answer"""
    
    score = int(callback.data.split("_")[1])
    
    # For demo - just show completion
    completion_text = f"""
🎉 **Оценка завершена!**

Спасибо за ответы! Я проанализировал ваш профиль.

**Ваша оценка открытости к новому опыту:** {score}/5

На основе ваших ответов я буду давать персонализированные рекомендации.

**Что дальше?**
💬 Можете задать любой вопрос или поделиться тем, что вас беспокоит
📊 Посмотреть полный профиль: /profile
🎯 Настроить цели: /goals

Просто напишите мне что угодно, и я отвечу с учетом вашей личности!
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Начать чат", callback_data="start_chat")],
        [InlineKeyboardButton(text="📊 Мой профиль", callback_data="show_profile")]
    ])
    
    # Mark user as onboarded
    user_id = callback.from_user.id
    users_db[user_id]["onboarded"] = True
    
    await callback.message.edit_text(completion_text, reply_markup=keyboard)
    await state.set_state(UserStates.chatting)

@dp.callback_query(F.data == "start_chat")
async def start_chat(callback: types.CallbackQuery, state: FSMContext):
    """Start chat mode"""
    
    chat_text = """
💬 **Режим чата активирован**

Теперь можете писать мне любые сообщения! 

Я буду отвечать с учетом вашего психологического профиля и помогать:
• Разобрать сложные ситуации  
• Найти решения проблем
• Лучше понять себя и свои реакции
• Достичь поставленных целей

**Примеры вопросов:**
"Как мне лучше справляться со стрессом?"
"Почему я откладываю важные дела?"
"Как улучшить отношения с коллегами?"

Просто напишите что угодно! 👇
    """
    
    await callback.message.edit_text(chat_text)
    await state.set_state(UserStates.chatting)

async def show_main_menu(message: Message, state: FSMContext):
    """Show main menu for existing users"""
    
    user_id = message.from_user.id
    user_name = users_db[user_id]["name"]
    
    menu_text = f"""
🏠 **Главное меню**

Привет, {user_name}! Рад видеть вас снова.

Что хотите сделать?
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Продолжить чат", callback_data="start_chat")],
        [InlineKeyboardButton(text="📊 Мой профиль", callback_data="show_profile")],
        [InlineKeyboardButton(text="🎯 Мои цели", callback_data="show_goals")],
        [InlineKeyboardButton(text="📝 Дневник", callback_data="daily_checkin")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")]
    ])
    
    await message.answer(menu_text, reply_markup=keyboard)
    await state.set_state(UserStates.chatting)

@dp.message(UserStates.chatting)
async def handle_chat_message(message: Message, state: FSMContext):
    """Handle chat messages from users"""
    
    user_id = message.from_user.id
    user_text = message.text
    
    # Simple AI-like response (placeholder)
    response = f"""
🤖 **AI Коуч отвечает:**

Спасибо за ваш вопрос: "{user_text}"

Я анализирую ваше сообщение с учетом вашего психологического профиля...

*[Здесь будет настоящий AI-анализ через Claude/GPT]*

**Мой совет:**
Попробуйте разложить эту ситуацию на более мелкие части и подумать, какие из них вы можете контролировать.

Есть еще вопросы? Продолжайте писать! 💬
    """
    
    await message.answer(response)

@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Show help"""
    
    help_text = """
🆘 **Помощь по Selfology Bot**

**Основные команды:**
/start - Главное меню
/help - Эта справка
/profile - Мой психологический профиль  
/goals - Управление целями
/export - Экспорт всех данных

**Возможности:**
🧠 Психологический анализ личности
💬 Персонализированный AI-коучинг
📊 Трекинг прогресса и инсайты
🎯 Управление целями

**Поддержка:** @selfology_support
**Сайт:** https://selfology.me
    """
    
    await message.answer(help_text)

@dp.callback_query(F.data == "show_profile")
async def show_profile(callback: types.CallbackQuery):
    """Show user profile"""
    
    profile_text = """
📊 **Ваш психологический профиль**

**Основные черты личности:**
🎨 Открытость к опыту: 85%
📋 Добросовестность: 72%
👥 Экстраверсия: 45%
🤝 Доброжелательность: 78%
😰 Эмоциональная нестабильность: 34%

**Жизненные ценности:**
❤️ Семья и близкие: Высокая важность
🚀 Карьера: Средняя важность  
💪 Здоровье: Высокая важность

*Данные основаны на ваших ответах в тестах*

Хотите пройти расширенную оценку? /assessment
    """
    
    await callback.message.edit_text(profile_text)

async def main():
    """Run the bot"""
    
    print("🚀 Starting Selfology Bot...")
    print(f"✅ Bot token configured")
    print(f"🔗 Bot username: @SelfologyPersonalCoachBot")
    print("🎯 Ready for users!")
    
    # Start polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())