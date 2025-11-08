"""
Chat Handler - Pure routing to Chat Coach service
NO business logic - only routes requests to Chat Coach
"""
import asyncpg
from aiogram import Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from ...services.chat_coach import ChatCoachService
from ...data_access.user_dao import UserDAO
from ...core.logging import telegram_logger
from ...selfology_bot.messages import get_message, get_keyboard


class ChatStates(StatesGroup):
    chatting = State()
    waiting_for_consent = State()


def setup_chat_handlers(dp: Dispatcher, db_pool: asyncpg.Pool):
    """Setup chat handlers - pure routing only"""
    
    # Initialize chat service
    chat_coach = ChatCoachService(db_pool)
    user_dao = UserDAO(db_pool)
    
    @dp.message(CommandStart())
    async def cmd_start(message: Message, state: FSMContext):
        """Route /start to user management and show main menu"""
        
        user_id = str(message.from_user.id)
        telegram_logger.log_user_action("start_command", user_id)
        
        # Extract telegram user data
        telegram_data = {
            "username": message.from_user.username,
            "first_name": message.from_user.first_name,
            "last_name": message.from_user.last_name
        }
        
        # Get or create user
        user = await user_dao.get_or_create_user(user_id, telegram_data)
        
        if user.get("gdpr_consent"):
            # User has consent - show main menu
            await show_main_menu(message, user)
        else:
            # Need consent first
            await show_gdpr_consent(message, state)
    
    async def show_gdpr_consent(message: Message, state: FSMContext):
        """Show GDPR consent form"""
        
        # 🎨 Используем централизованную систему сообщений
        consent_text = get_message('welcome', 'ru', 'onboarding')
        keyboard = get_keyboard('gdpr_consent', 'ru')
        
        await message.answer(consent_text, reply_markup=keyboard, parse_mode='HTML')
        await state.set_state(ChatStates.waiting_for_consent)
    
    async def show_main_menu(message: Message, user: dict):
        """Show main menu based on user status"""
        
        user_name = user.get("first_name", "Friend")
        onboarding_complete = user.get("onboarding_completed", False)
        
        if onboarding_complete:
            menu_text = f"""
🏠 **Главное меню**

Привет, {user_name}! Добро пожаловать в Selfology.

Ваш профиль готов к работе! Что хотите делать?
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💬 Чат с AI-коучем", callback_data="start_chat")],
                [InlineKeyboardButton(text="🧠 Дополнительная оценка", callback_data="continue_assessment")],
                [InlineKeyboardButton(text="📊 Мой профиль", callback_data="show_profile")],
                [InlineKeyboardButton(text="📈 Статистика", callback_data="show_stats")]
            ])
        
        else:
            menu_text = f"""
👋 **Привет, {user_name}!**

Добро пожаловать в Selfology! Рекомендую начать с психологической оценки.

**Что это даст:**
• Детальный анализ личности
• Персональные рекомендации
• Умные советы от AI-коуча
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🧠 Начать оценку", callback_data="start_assessment")],
                [InlineKeyboardButton(text="💬 Сразу к чату", callback_data="start_chat")],
                [InlineKeyboardButton(text="📊 Мой статус", callback_data="show_stats")]
            ])
        
        await message.answer(menu_text, reply_markup=keyboard)
    
    @dp.callback_query(F.data == "consent_yes")
    async def consent_accepted(callback: CallbackQuery, state: FSMContext):
        """Route consent acceptance to user service"""
        
        user_id = str(callback.from_user.id)
        
        # Update consent in database
        await user_dao.update_user_consent(user_id, True)
        
        telegram_logger.log_user_action("gdpr_consent_accepted", user_id)
        
        # Get updated user data
        user = await user_dao.get_or_create_user(user_id, {
            "username": callback.from_user.username,
            "first_name": callback.from_user.first_name,
            "last_name": callback.from_user.last_name
        })
        
        await callback.message.edit_text("✅ Спасибо за согласие! Настраиваю ваш профиль...")
        await show_main_menu(callback.message, user)
        await state.clear()
    
    @dp.callback_query(F.data == "consent_no")
    async def consent_declined(callback: CallbackQuery, state: FSMContext):
        """Handle consent decline"""
        
        telegram_logger.log_user_action("gdpr_consent_declined", str(callback.from_user.id))
        
        decline_text = """
😔 Понимаю ваши опасения.

К сожалению, без согласия я не могу предоставить персонализированный коучинг.

Если передумаете, просто нажмите /start снова.

Берегите себя! 👋
        """
        
        await callback.message.edit_text(decline_text)
        await state.clear()
    
    @dp.callback_query(F.data == "start_chat")
    async def start_chat_session(callback: CallbackQuery, state: FSMContext):
        """Route chat start to Chat Coach service"""
        
        user_id = str(callback.from_user.id)
        
        # Route to Chat Coach service
        result = await chat_coach.start_chat_session(user_id)
        
        if result.success:
            await callback.message.edit_text(result.response_text)
            await state.set_state(ChatStates.chatting)
            
            telegram_logger.log_user_action("chat_session_started", user_id)
        else:
            await callback.answer(f"Ошибка запуска чата: {result.message}")
    
    @dp.message(Command("chat"))
    async def cmd_chat(message: Message, state: FSMContext):
        """Direct chat command"""
        
        user_id = str(message.from_user.id)
        
        # Start chat session
        result = await chat_coach.start_chat_session(user_id)
        
        if result.success:
            await message.answer(result.response_text)
            await state.set_state(ChatStates.chatting)
        else:
            await message.answer(f"Ошибка: {result.message}")
    
    @dp.message(ChatStates.chatting)
    async def handle_chat_message(message: Message, state: FSMContext):
        """Route chat message to Chat Coach service"""
        
        user_id = str(message.from_user.id)
        user_message = message.text
        
        # Route to Chat Coach service  
        result = await chat_coach.process_message(user_id, user_message)
        
        if result.success:
            response_text = result.response_text
            
            # Add insights info if detected
            if result.insights_detected:
                insights_info = f"\n\n💡 **Обнаружены инсайты:** {len(result.insights_detected)}"
                response_text += insights_info
            
            # Add personality updates info
            if result.personality_updates:
                updates_info = f"\n📈 **Профиль обновлен:** {len(result.personality_updates)} характеристик"
                response_text += updates_info
            
            await message.answer(response_text)
            
            telegram_logger.log_user_action("chat_message_processed", user_id,
                                           response_time=result.processing_time)
        
        else:
            await message.answer(f"❌ Ошибка обработки сообщения: {result.message}")
    
    @dp.message(Command("history"))
    async def cmd_chat_history(message: Message):
        """Show chat history"""
        
        user_id = str(message.from_user.id)
        
        # Route to Chat Coach service
        result = await chat_coach.get_conversation_history(user_id, limit=10)
        
        if result.success:
            await message.answer(f"📝 **История разговора:**\n\n{result.response_text}")
        else:
            await message.answer(f"❌ Ошибка получения истории: {result.message}")
    
    # Route other callbacks to appropriate services
    @dp.callback_query(F.data == "start_assessment")
    async def route_to_assessment(callback: CallbackQuery):
        """Route to assessment handler"""
        # Create a fake message to trigger assessment
        fake_message = type('obj', (object,), {
            'from_user': callback.from_user,
            'answer': callback.message.edit_text
        })
        # This would be handled by assessment handler
        await callback.answer("Перенаправляю к системе оценки...")
    
    @dp.callback_query(F.data == "show_profile")  
    async def route_to_profile(callback: CallbackQuery):
        """Route to profile handler"""
        await callback.answer("Загружаю профиль...")
    
    @dp.callback_query(F.data == "show_stats")
    async def route_to_stats(callback: CallbackQuery):
        """Route to statistics handler"""
        await callback.answer("Загружаю статистику...")
    
    telegram_logger.info("Chat handlers configured")