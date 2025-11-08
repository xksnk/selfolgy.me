#!/usr/bin/env python3
"""
Test Selfology Bot with Real Database Integration
Tests new user detection, GDPR consent, and database operations.
"""

import asyncio
import asyncpg
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN = "8197893707:AAEbGC7r_4GGWXvgah-q-mLw5pp7YIxhK9g"

# Database configuration (from environment or defaults)
import os
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
    onboarding = State()
    chatting = State()

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Database connection pool
db_pool = None

async def init_db():
    """Initialize database connection pool"""
    global db_pool
    try:
        db_pool = await asyncpg.create_pool(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"], 
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            database=DB_CONFIG["database"],
            min_size=1,
            max_size=10
        )
        logger.info("✅ Database connection pool created")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to connect to database: {e}")
        return False

async def get_user_from_db(telegram_id: int):
    """Get user from database"""
    async with db_pool.acquire() as conn:
        try:
            result = await conn.fetchrow(
                "SELECT * FROM selfology_users WHERE telegram_id = $1",
                str(telegram_id)
            )
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error getting user {telegram_id}: {e}")
            return None

async def create_user_in_db(telegram_user: types.User):
    """Create new user in database"""
    async with db_pool.acquire() as conn:
        try:
            result = await conn.fetchrow(
                """
                INSERT INTO selfology_users 
                (telegram_id, username, first_name, last_name, last_active) 
                VALUES ($1, $2, $3, $4, $5)
                RETURNING *
                """,
                str(telegram_user.id),
                telegram_user.username,
                telegram_user.first_name,
                telegram_user.last_name,
                datetime.now(timezone.utc)
            )
            
            logger.info(f"✅ New user created: {telegram_user.id} ({telegram_user.first_name})")
            return dict(result)
        except Exception as e:
            logger.error(f"Error creating user {telegram_user.id}: {e}")
            return None

async def update_user_consent(telegram_id: int, consent: bool):
    """Update user GDPR consent"""
    async with db_pool.acquire() as conn:
        try:
            await conn.execute(
                """
                UPDATE selfology_users 
                SET gdpr_consent = $1, updated_at = $2 
                WHERE telegram_id = $3
                """,
                consent,
                datetime.now(timezone.utc),
                str(telegram_id)
            )
            
            logger.info(f"✅ User {telegram_id} consent updated: {consent}")
            return True
        except Exception as e:
            logger.error(f"Error updating consent for {telegram_id}: {e}")
            return False

async def update_user_onboarding(telegram_id: int, completed: bool = True):
    """Update user onboarding status"""
    async with db_pool.acquire() as conn:
        try:
            await conn.execute(
                """
                UPDATE selfology_users 
                SET onboarding_completed = $1, updated_at = $2 
                WHERE telegram_id = $3
                """,
                completed,
                datetime.now(timezone.utc),
                str(telegram_id)
            )
            
            logger.info(f"✅ User {telegram_id} onboarding completed: {completed}")
            return True
        except Exception as e:
            logger.error(f"Error updating onboarding for {telegram_id}: {e}")
            return False

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command with database integration"""
    
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "Friend"
    
    logger.info(f"🚀 /start command from user {user_id} ({user_name})")
    
    try:
        # Check if user exists in database
        user_data = await get_user_from_db(user_id)
        
        if user_data:
            # Existing user
            logger.info(f"👤 Existing user detected: {user_id}")
            
            if user_data["gdpr_consent"] and user_data["onboarding_completed"]:
                # Fully onboarded user
                await show_main_menu(message, state, user_data)
            elif user_data["gdpr_consent"]:
                # Has consent but not onboarded
                await continue_onboarding(message, state)
            else:
                # No consent yet
                await show_gdpr_consent(message, state)
        else:
            # New user - create in database
            logger.info(f"🆕 New user detected: {user_id}")
            
            user_data = await create_user_in_db(message.from_user)
            if user_data:
                await show_gdpr_consent(message, state)
            else:
                await message.answer("❌ Техническая ошибка при регистрации. Попробуйте позже.")
    
    except Exception as e:
        logger.error(f"Error in start command for user {user_id}: {e}")
        await message.answer("❌ Произошла техническая ошибка. Попробуйте позже.")

async def show_gdpr_consent(message: Message, state: FSMContext):
    """Show GDPR consent form"""
    
    user_id = message.from_user.id
    logger.info(f"📋 Showing GDPR consent to user {user_id}")
    
    consent_text = f"""
🌟 **Добро пожаловать в Selfology!**

Привет! Я — ваш персональный AI-коуч для глубокого самопознания. 

🎯 **Что я умею:**
✅ Психологический анализ личности (Big Five)
✅ Персонализированные инсайты и советы
✅ Умный дневник с выявлением паттернов
✅ Трекинг целей и прогресса

🔒 **Обработка данных:**
Для работы мне нужно обрабатывать ваши сообщения и ответы на тесты. 
Все данные хранятся безопасно и используются только для персонализации.

📊 **Ваш ID в системе:** `{user_id}`

Согласны на обработку данных согласно GDPR?
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
    """Handle consent acceptance with database update"""
    
    user_id = callback.from_user.id
    
    logger.info(f"✅ User {user_id} accepted GDPR consent")
    
    # Update consent in database
    success = await update_user_consent(user_id, True)
    
    if success:
        welcome_text = f"""
🎉 **Отлично! Согласие получено и сохранено в базе!**

**📊 Данные обновлены:**
- Пользователь ID: `{user_id}`
- GDPR согласие: ✅ **Дано** 
- Timestamp: `{datetime.now(timezone.utc).isoformat()}`
- База данных: `n8n.selfology_users`

Давайте начнем ваше путешествие самопознания!

**Первый шаг** — пройти быструю психологическую оценку (5-7 минут):
• Определим ваши основные личностные черты
• Выявим жизненные ценности и приоритеты  
• Настроим персонализированные рекомендации

После этого вы сможете общаться со мной как с личным коучем! 🚀
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧠 Начать психологическую оценку", callback_data="start_assessment")],
            [InlineKeyboardButton(text="💬 Просто поговорить", callback_data="start_chat")]
        ])
        
        await callback.message.edit_text(welcome_text, reply_markup=keyboard)
        await state.set_state(UserStates.onboarding)
    else:
        await callback.message.edit_text("❌ Ошибка сохранения согласия в базу данных. Попробуйте еще раз.")

@dp.callback_query(F.data == "consent_no")  
async def consent_declined(callback: types.CallbackQuery, state: FSMContext):
    """Handle consent decline with logging"""
    
    user_id = callback.from_user.id
    
    logger.info(f"❌ User {user_id} declined GDPR consent")
    
    # Update consent in database (declined)
    await update_user_consent(user_id, False)
    
    decline_text = f"""
😔 **Понимаю ваши опасения по поводу конфиденциальности.**

**📊 Статус обновлен:**
- Пользователь ID: `{user_id}`
- GDPR согласие: ❌ **Отклонено**
- База данных: Запись сохранена

К сожалению, без согласия на обработку данных я не смогу предоставить персонализированный коучинг.

Если передумаете, просто нажмите /start снова.

Берегите себя! 👋
    """
    
    await callback.message.edit_text(decline_text)
    await state.clear()

@dp.callback_query(F.data == "start_assessment")
async def start_assessment(callback: types.CallbackQuery, state: FSMContext):
    """Start assessment and mark onboarding complete"""
    
    user_id = callback.from_user.id
    
    # Mark onboarding as completed in database
    await update_user_onboarding(user_id, True)
    
    completion_text = f"""
🎉 **Онбординг завершен! Запись в базе обновлена.**

**📊 Статус пользователя:**
- ID: `{user_id}`
- GDPR согласие: ✅ Дано
- Онбординг: ✅ **Завершен**
- Последнее обновление: `{datetime.now(timezone.utc).isoformat()}`

**🧠 Результат экспресс-оценки:**
Ваш профиль создан и сохранен в векторной базе данных!

**Что дальше:**
💬 Можете общаться со мной как с персональным коучем
📊 Посмотреть профиль: /profile
🎯 Настроить цели: /goals

Просто напишите мне что угодно! 👇
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Начать чат с коучем", callback_data="start_chat")],
        [InlineKeyboardButton(text="📊 Проверить мой профиль в БД", callback_data="show_db_profile")]
    ])
    
    await callback.message.edit_text(completion_text, reply_markup=keyboard)
    await state.set_state(UserStates.chatting)

@dp.callback_query(F.data == "show_db_profile")
async def show_db_profile(callback: types.CallbackQuery):
    """Show user profile from database"""
    
    user_id = callback.from_user.id
    user_data = await get_user_from_db(user_id)
    
    if user_data:
        profile_text = f"""
📊 **Ваш профиль из базы данных:**

**🔢 Системные данные:**
- Database ID: `{user_data['id']}`
- Telegram ID: `{user_data['telegram_id']}`
- Username: `@{user_data['username']}`
- Имя: `{user_data['first_name']} {user_data['last_name'] or ''}`

**📋 Статус:**
- Тариф: `{user_data['tier']}`
- GDPR согласие: {'✅' if user_data['gdpr_consent'] else '❌'}
- Онбординг: {'✅' if user_data['onboarding_completed'] else '❌'}
- Уровень приватности: `{user_data['privacy_level']}`

**⏰ Временные метки:**
- Создан: `{user_data['created_at']}`
- Обновлен: `{user_data['updated_at']}`  
- Последняя активность: `{user_data['last_active']}`

**✅ База данных:** `n8n.selfology_users`
        """
    else:
        profile_text = "❌ Пользователь не найден в базе данных!"
    
    await callback.message.edit_text(profile_text)

async def show_main_menu(message: Message, state: FSMContext, user_data: dict):
    """Show main menu for existing users"""
    
    user_name = user_data["first_name"]
    
    menu_text = f"""
🏠 **Добро пожаловать обратно, {user_name}!**

**📊 Ваш статус в системе:**
- ✅ GDPR согласие дано
- ✅ Онбординг завершен  
- 🎯 Готов к использованию

Что хотите сделать?
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Чат с коучем", callback_data="start_chat")],
        [InlineKeyboardButton(text="📊 Мой профиль в БД", callback_data="show_db_profile")],
        [InlineKeyboardButton(text="🎯 Мои цели", callback_data="show_goals")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")]
    ])
    
    await message.answer(menu_text, reply_markup=keyboard)
    await state.set_state(UserStates.chatting)

async def continue_onboarding(message: Message, state: FSMContext):
    """Continue onboarding for users with consent but incomplete onboarding"""
    
    text = """
🔄 **Продолжаем онбординг**

У вас уже есть согласие на обработку данных, но онбординг не завершен.

Давайте продолжим с того места, где остановились!
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧠 Завершить психологическую оценку", callback_data="start_assessment")]
    ])
    
    await message.answer(text, reply_markup=keyboard)
    await state.set_state(UserStates.onboarding)

@dp.callback_query(F.data == "start_chat")
async def start_chat(callback: types.CallbackQuery, state: FSMContext):
    """Start chat mode"""
    
    chat_text = """
💬 **Режим чата с AI-коучем активирован**

Теперь можете писать любые сообщения, и я буду отвечать с учетом вашего профиля!

🎯 **Что я могу:**
• Помочь разобрать сложную ситуацию
• Предложить стратегии решения проблем
• Проанализировать эмоции и паттерны
• Поддержать в сложные моменты

**Все ваши сообщения логируются для улучшения качества ответов.**

Просто напишите что угодно! 👇
    """
    
    await callback.message.edit_text(chat_text)
    await state.set_state(UserStates.chatting)

@dp.message(UserStates.chatting)
async def handle_chat_message(message: Message, state: FSMContext):
    """Handle chat messages with logging"""
    
    user_id = message.from_user.id
    user_text = message.text
    
    logger.info(f"💬 Chat message from {user_id}: '{user_text[:50]}{'...' if len(user_text) > 50 else ''}'")
    
    # Update last active timestamp
    async with db_pool.acquire() as conn:
        await conn.execute(
            "UPDATE selfology_users SET last_active = $1 WHERE telegram_id = $2",
            datetime.now(timezone.utc),
            str(user_id)
        )
    
    response = f"""
🤖 **AI Коуч отвечает:**

Получил ваше сообщение: "{user_text}"

**📊 Обработка в системе:**
- ✅ Сообщение сохранено в логах
- ✅ Timestamp активности обновлен в БД
- ✅ Контекст учтен для персонализации

*[В продакшене здесь будет настоящий AI-анализ через Claude/GPT]*

**💡 Пример персонального совета:**
На основе вашего профиля рекомендую структурированный подход к решению этого вопроса.

Продолжайте писать! 💬
    """
    
    await message.answer(response)

@dp.message(Command("db"))
async def cmd_check_db(message: Message):
    """Check database connection and user status"""
    
    user_id = message.from_user.id
    
    try:
        # Test database connection
        async with db_pool.acquire() as conn:
            # Get user data
            user_data = await conn.fetchrow(
                "SELECT * FROM selfology_users WHERE telegram_id = $1",
                str(user_id)
            )
            
            # Get total users count
            total_users = await conn.fetchval(
                "SELECT COUNT(*) FROM selfology_users"
            )
            
            # Get recent users
            recent_users = await conn.fetchval(
                "SELECT COUNT(*) FROM selfology_users WHERE created_at > NOW() - INTERVAL '24 hours'"
            )
        
        if user_data:
            db_status = f"""
🗄️ **Статус базы данных:**

**✅ Подключение активно**

**👤 Ваши данные:**
- DB ID: `{user_data['id']}`
- Telegram ID: `{user_data['telegram_id']}`  
- GDPR: {'✅' if user_data['gdpr_consent'] else '❌'}
- Онбординг: {'✅' if user_data['onboarding_completed'] else '❌'}
- Создан: `{user_data['created_at']}`

**📊 Статистика системы:**
- Всего пользователей: `{total_users}`
- Новых за 24ч: `{recent_users}`
- База данных: `n8n.selfology_users`
- Подключение: `✅ PostgreSQL 15`
            """
        else:
            db_status = f"""
❌ **Пользователь не найден в базе!**

ID: `{user_id}`
База: `n8n.selfology_users`

Попробуйте /start для регистрации.
            """
        
        await message.answer(db_status)
        
    except Exception as e:
        logger.error(f"Database check error for user {user_id}: {e}")
        await message.answer(f"❌ Ошибка подключения к базе данных: {e}")

@dp.message(Command("logs"))
async def cmd_show_logs(message: Message):
    """Show recent log entries for debugging"""
    
    try:
        logs_info = """
📝 **Система логирования активна:**

**📁 Файлы логов:**
• `logs/selfology.log` - Основной лог
• `logs/errors/errors.log` - Ошибки
• `logs/users/user_activity.log` - Действия пользователей
• `logs/bot/bot_activity.log` - События бота
• `logs/ai/ai_interactions.log` - AI взаимодействия
• `logs/metrics/metrics.log` - Метрики производительности

**🛠️ Команды мониторинга:**
```
# Статус системы
python scripts/selfology_manager.py status

# Просмотр логов
python scripts/selfology_manager.py logs users 20

# Мониторинг в реальном времени
python scripts/selfology_manager.py dashboard
```

**🔍 Все ваши действия логируются для отладки и улучшения системы.**
        """
        
        await message.answer(logs_info)
        
    except Exception as e:
        logger.error(f"Error showing logs info: {e}")

async def main():
    """Main bot function with database initialization"""
    
    print("🚀 Starting Test DB Bot for Selfology...")
    
    # Initialize database
    if not await init_db():
        print("❌ Failed to connect to database. Check connection settings.")
        return
    
    try:
        print("✅ Database connected successfully")
        print(f"✅ Bot token configured")
        print(f"🔗 Bot username: @SelfologyMeCoachBot")
        print(f"📊 Ready for testing user flow!")
        print()
        print("🧪 TEST SCENARIO:")
        print("1. Send /start to test new user detection")
        print("2. Accept GDPR consent to test database update")
        print("3. Complete onboarding to test full flow")
        print("4. Use /db to check database status")
        print("5. Use /logs to see logging info")
        print()
        
        logger.info("Test DB Bot started successfully")
        
        # Start polling
        await dp.start_polling(bot)
        
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
        logger.info("Bot stopped by user")
    except Exception as e:
        print(f"💥 Bot error: {e}")
        logger.error(f"Bot crashed: {e}")
    finally:
        # Close database pool
        if db_pool:
            await db_pool.close()
            logger.info("Database connection pool closed")

if __name__ == "__main__":
    asyncio.run(main())