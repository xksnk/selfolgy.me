"""
Telegram Interface - модульная структура Telegram бота

Архитектура:
- lifecycle: Управление жизненным циклом бота
- handlers: Обработчики команд и сообщений  
- middleware: Промежуточные слои (логирование, etc)
- utilities: Вспомогательные функции
- controller: Главный координатор

SPRINT 1 Refactoring (Nov 2025):
Разбили монолитный selfology_controller.py (1572 строки) на модульную структуру
"""

from .lifecycle import BotInstanceLock, BotLifecycle
from .handlers.command_handlers import CommandHandlers
from .middleware.state_logger import StateLoggerMiddleware
from .utilities.message_splitter import send_long_message
from .utilities.menu_builder import show_main_menu, show_main_menu_callback

__all__ = [
    "BotInstanceLock",
    "BotLifecycle",
    "CommandHandlers",
    "StateLoggerMiddleware",
    "send_long_message",
    "show_main_menu",
    "show_main_menu_callback",
]
