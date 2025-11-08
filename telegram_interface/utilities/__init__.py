"""
Utilities - вспомогательные функции

Модули:
- message_splitter: Разбиение длинных сообщений для Telegram
- menu_builder: Построение главного меню
- question_display: Отображение вопросов онбординга
"""

from .message_splitter import send_long_message
from .menu_builder import show_main_menu, show_main_menu_callback
from .question_display import show_onboarding_question

__all__ = [
    "send_long_message",
    "show_main_menu",
    "show_main_menu_callback",
    "show_onboarding_question",
]
