"""
Handlers - обработчики команд и сообщений Telegram бота

Модули:
- command_handlers: Базовые команды (/start, /help, /profile)
- onboarding_handlers: Процесс онбординга
- chat_handlers: AI чат
- admin_handlers: Административные команды
- callback_handlers: Callback кнопки
"""

from .command_handlers import CommandHandlers
from .onboarding_handlers import OnboardingHandlers
from .chat_handlers import ChatHandlers
from .admin_handlers import AdminHandlers
from .callback_handlers import CallbackHandlers

__all__ = [
    "CommandHandlers",
    "OnboardingHandlers",
    "ChatHandlers",
    "AdminHandlers",
    "CallbackHandlers",
]
