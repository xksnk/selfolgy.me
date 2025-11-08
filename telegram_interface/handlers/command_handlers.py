"""
Command Handlers - базовые команды бота

Обработчики для:
- /start - точка входа, GDPR consent, главное меню
- /help - справка по боту
- /profile - профиль пользователя
"""

import logging
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)


class CommandHandlers:
    """
    Обработчики базовых команд бота
    
    Все методы статические - не требуют состояния.
    Получают необходимые зависимости через параметры.
    """

    @staticmethod
    async def cmd_start(
        message: Message,
        state: FSMContext,
        user_dao,
        messages,
        onboarding_states,
        show_main_menu_func
    ):
        """
        Команда /start - точка входа в бота
        
        Workflow:
        1. Создать/получить пользователя из БД
        2. Проверить GDPR consent
        3. Если нет consent -> показать GDPR
        4. Если есть consent -> главное меню
        """
        user_name = message.from_user.full_name or "Друг"
        telegram_id = str(message.from_user.id)
        logger.info(f"👤 User started: {user_name} (ID: {telegram_id})")

        # Проверяем пользователя в БД
        telegram_data = {
            'id': message.from_user.id,
            'username': message.from_user.username,
            'first_name': message.from_user.first_name,
            'last_name': message.from_user.last_name
        }

        user = await user_dao.get_or_create_user(telegram_data)

        # Проверяем GDPR consent
        has_consent = user.get('consent', False)

        if not has_consent:
            # Новый пользователь - показываем GDPR
            text = messages.get_message('welcome', 'ru', 'onboarding')
            keyboard = messages.get_keyboard('gdpr_consent', 'ru')

            await message.answer(text, reply_markup=keyboard, parse_mode='HTML')
            await state.set_state(onboarding_states.gdpr_consent)
        else:
            # Пользователь с согласием - главное меню
            await show_main_menu_func(message, user_name)

    @staticmethod
    async def cmd_help(message: Message, messages):
        """Команда /help - справка по боту"""
        text = messages.get_message('help', 'ru', 'general')
        keyboard = messages.get_keyboard('back_to_menu', 'ru')

        await message.answer(text, reply_markup=keyboard, parse_mode='HTML')

    @staticmethod
    async def cmd_profile(message: Message, user_dao, messages):
        """Команда /profile - профиль пользователя"""
        telegram_id = str(message.from_user.id)
        logger.info(f"📊 Profile requested by user {telegram_id}")

        # Получаем данные профиля
        profile_data = await user_dao.get_user_profile_data(telegram_id)

        if profile_data:
            text = messages.get_message('user_profile', 'ru', 'general', **profile_data)
            keyboard = messages.get_keyboard('profile_actions', 'ru')

            await message.answer(text, reply_markup=keyboard, parse_mode='HTML')
        else:
            # Пользователь не найден
            text = messages.get_message('access_denied', 'ru', 'errors',
                access_reason="Профиль не найден",
                action_suggestion="Пройдите регистрацию с помощью /start"
            )
            keyboard = messages.get_keyboard('back_to_menu', 'ru')

            await message.answer(text, reply_markup=keyboard, parse_mode='HTML')
