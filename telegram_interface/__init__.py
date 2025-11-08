"""
Telegram Interface - модульная структура Telegram бота

SPRINT 1 Refactoring (Nov 2025):
Разбили монолитный selfology_controller.py (1572 строки) на модульную архитектуру

Архитектура:
- controller: Главный координатор (196 строк)
- lifecycle: Управление жизненным циклом бота (451 строк)
- handlers: Обработчики команд и сообщений (1014 строк в 5 модулях)
- middleware: Промежуточные слои (76 строк)
- utilities: Вспомогательные функции (206 строк в 3 модулях)
- handler_registry: Регистрация handlers с DI (365 строк)
- states: FSM состояния (29 строк)
- config: Конфигурация (35 строк)

ИТОГО: ~2370 строк в 14 модулях (было: 1572 строки в 1 файле)

Качество:
✅ No God Objects
✅ SOLID principles compliance
✅ Clean Architecture
✅ Dependency Injection
✅ Easy to test
✅ Easy to maintain
"""

from .controller import SelfologyController
from .lifecycle import BotInstanceLock, BotLifecycle
from .handler_registry import HandlerRegistry
from .states import OnboardingStates, ChatStates
from .handlers import (
    CommandHandlers,
    OnboardingHandlers,
    ChatHandlers,
    AdminHandlers,
    CallbackHandlers
)
from .middleware import StateLoggerMiddleware
from .utilities import (
    send_long_message,
    show_main_menu,
    show_main_menu_callback,
    show_onboarding_question
)

__all__ = [
    # Main controller
    "SelfologyController",
    
    # Lifecycle
    "BotInstanceLock",
    "BotLifecycle",
    
    # Registry
    "HandlerRegistry",
    
    # States
    "OnboardingStates",
    "ChatStates",
    
    # Handlers
    "CommandHandlers",
    "OnboardingHandlers",
    "ChatHandlers",
    "AdminHandlers",
    "CallbackHandlers",
    
    # Middleware
    "StateLoggerMiddleware",
    
    # Utilities
    "send_long_message",
    "show_main_menu",
    "show_main_menu_callback",
    "show_onboarding_question",
]
