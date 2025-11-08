from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from ..states import OnboardingStates, ChatStates
from ...core.database import get_db
from ...models import User
from ...services.user_service import UserService
from ...messages import get_message_service, get_message, get_keyboard

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command - main entry point"""
    
    # Получаем сервис сообщений
    messages = get_message_service()
    
    # Создаем пользователя (пока без DB для демонстрации)
    user_name = message.from_user.full_name or "Друг"
    
    # Проверяем состояние пользователя (пока заглушка)
    onboarding_completed = False  # TODO: проверить из БД
    
    if not onboarding_completed:
        await start_onboarding(message, state)
    else:
        await show_main_menu(message, state, user_name)


async def show_main_menu(message: Message, state: FSMContext, user_name: str = ""):
    """Show main menu for existing users"""
    
    # Статус пользователя для динамического контента
    status_message = f"Добро пожаловать, {user_name}!"
    
    # Используем систему сообщений
    menu_text = get_message('main_menu', 'ru', 'general', status_message=status_message)
    keyboard = get_keyboard('main_menu', 'ru')
    
    await message.answer(menu_text, reply_markup=keyboard, parse_mode='HTML')
    await state.clear()  # Очищаем состояние FSM


@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery, state: FSMContext):
    """Handle main menu callback"""
    
    user_name = callback.from_user.full_name or "Друг"
    status_message = f"Добро пожаловать, {user_name}!"
    
    menu_text = get_message('main_menu', 'ru', 'general', status_message=status_message)
    keyboard = get_keyboard('main_menu', 'ru')
    
    await callback.message.edit_text(menu_text, reply_markup=keyboard, parse_mode='HTML')
    await state.clear()


async def start_onboarding(message: Message, state: FSMContext):
    """Start the onboarding process for new users"""
    
    # Используем систему сообщений
    welcome_text = get_message('welcome', 'ru', 'onboarding')
    keyboard = get_keyboard('gdpr_consent', 'ru')
    
    await message.answer(welcome_text, reply_markup=keyboard, parse_mode='HTML')
    await state.set_state(OnboardingStates.gdpr_consent)


@router.callback_query(F.data == "gdpr_details")
async def show_gdpr_info(callback: CallbackQuery):
    """Show GDPR consent information"""
    
    # Используем систему сообщений
    gdpr_text = get_message('gdpr_consent', 'ru', 'onboarding')
    keyboard = get_keyboard('gdpr_consent', 'ru')
    
    await callback.message.edit_text(gdpr_text, reply_markup=keyboard, parse_mode='HTML')


@router.callback_query(F.data == "gdpr_accept")
async def gdpr_accepted(callback: CallbackQuery, state: FSMContext):
    """Handle GDPR consent acceptance"""
    
    # TODO: Сохранить согласие в базу данных
    # user_service = UserService(session)
    # await user_service.update_user_consent(callback.from_user.id, True)
    
    # Используем систему сообщений
    intro_text = get_message('gdpr_accepted', 'ru', 'onboarding')
    keyboard = get_keyboard('start_assessment', 'ru')
    
    await callback.message.edit_text(intro_text, reply_markup=keyboard, parse_mode='HTML')
    await state.set_state(OnboardingStates.personality_test_intro)


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Show help information"""
    
    help_text = get_message('help', 'ru', 'general')
    keyboard = get_keyboard('back_to_menu', 'ru')
    
    await message.answer(help_text, reply_markup=keyboard, parse_mode='HTML')


@router.callback_query(F.data == "help")
async def callback_help(callback: CallbackQuery):
    """Handle help callback"""
    
    help_text = get_message('help', 'ru', 'general')
    keyboard = get_keyboard('back_to_menu', 'ru')
    
    await callback.message.edit_text(help_text, reply_markup=keyboard, parse_mode='HTML')


@router.callback_query(F.data == "gdpr_decline") 
async def gdpr_declined(callback: CallbackQuery, state: FSMContext):
    """Handle GDPR consent decline"""
    
    decline_text = """
😔 К сожалению, без согласия на обработку данных я не могу предоставить персонализированный коучинг.

Если вы передумаете, просто нажмите /start снова.

Хорошего дня! 👋
    """
    
    await callback.message.edit_text(decline_text)
    await state.clear()


async def show_main_menu(message: Message, state: FSMContext):
    """Show main menu for existing users"""
    
    menu_text = """
🏠 Главное меню

Выберите действие:
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Чат с коучем", callback_data="start_chat")],
        [InlineKeyboardButton(text="📊 Мой профиль", callback_data="show_profile")],
        [InlineKeyboardButton(text="🎯 Цели", callback_data="manage_goals")],
        [InlineKeyboardButton(text="📝 Дневник", callback_data="daily_checkin")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")],
        [InlineKeyboardButton(text="📈 Аналитика", callback_data="show_analytics")]
    ])
    
    await message.answer(menu_text, reply_markup=keyboard)
    await state.set_state(ChatStates.idle)


@router.callback_query(F.data == "start_chat")
async def start_chat_session(callback: CallbackQuery, state: FSMContext):
    """Start a chat session with AI coach"""
    
    chat_text = """
💬 Режим чата с AI-коучем активирован

Можете задать любой вопрос или просто рассказать, что у вас на душе. 

Я проанализирую ваше сообщение с учетом вашего психологического профиля и дам персонализированный совет.

🎯 Что я могу:
• Помочь разобрать сложную ситуацию
• Предложить стратегии решения проблем
• Проанализировать эмоции и паттерны
• Поддержать в сложные моменты

Просто напишите мне что угодно! 👇
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(chat_text, reply_markup=keyboard)
    await state.set_state(ChatStates.chatting)


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Show help information"""
    
    help_text = """
🆘 Помощь по боту Selfology

📋 Основные команды:
/start - Главное меню
/chat - Быстрый старт чата с коучем
/profile - Показать мой профиль
/goals - Управление целями
/settings - Настройки
/help - Эта справка

💡 Возможности:
• Персонализированный AI-коучинг
• Психологический анализ личности
• Трекинг целей и привычек
• Умный дневник с инсайтами
• Векторный поиск по вашей истории

📞 Поддержка: @selfology_support
🌐 Сайт: https://selfology.me
    """
    
    await message.answer(help_text)