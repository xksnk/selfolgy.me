"""
Menu Builder - построение главного меню

Вспомогательные функции для отображения главного меню бота.
"""

import logging
from aiogram.types import Message, CallbackQuery

logger = logging.getLogger(__name__)


async def show_main_menu(message: Message, user_name: str, messages):
    """
    Показать главное меню бота (для Message)
    
    Args:
        message: Aiogram Message object
        user_name: Имя пользователя для персонализации
        messages: MessageService для получения текстов и клавиатур
    """
    text = messages.get_message('main_menu', 'ru', 'general', user_name=user_name)
    keyboard = messages.get_keyboard('main_menu', 'ru')
    
    await message.answer(text, reply_markup=keyboard, parse_mode='HTML')
    logger.info(f"📋 Main menu shown to user: {user_name}")


async def show_main_menu_callback(callback: CallbackQuery, user_name: str, messages):
    """
    Показать главное меню бота (для CallbackQuery)
    
    Args:
        callback: Aiogram CallbackQuery object
        user_name: Имя пользователя для персонализации
        messages: MessageService для получения текстов и клавиатур
    """
    text = messages.get_message('main_menu', 'ru', 'general', user_name=user_name)
    keyboard = messages.get_keyboard('main_menu', 'ru')
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
    await callback.answer()
    logger.info(f"📋 Main menu shown to user: {user_name}")
