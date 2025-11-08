"""
Selfology Messages System

Централизованная система управления сообщениями с поддержкой:
- Мультиязычности (ru, en, es)
- HTML форматирования для Telegram
- Шаблонизации с переменными
- Валидации и безопасности
- Клавиатур и кнопок
"""

from .service import MessageService
from .validators import MessageValidator, ValidationResult
from .formatters import TelegramFormatter
from .constants import MessageConstants

# Singleton instance для всего приложения
_message_service = None

def get_message_service(debug_mode: bool = False) -> MessageService:
    """Получить синглтон MessageService"""
    global _message_service
    if _message_service is None:
        _message_service = MessageService(debug_mode=debug_mode)
    else:
        # Обновляем режим если нужно
        _message_service.debug_mode = debug_mode
    return _message_service

# Удобные shortcuts
def get_message(key: str, locale: str = 'ru', category: str = 'general', **kwargs) -> str:
    """Быстрый доступ к сообщению"""
    return get_message_service().get_message(key, locale, category, **kwargs)

def get_button_text(key: str, locale: str = 'ru') -> str:
    """Быстрый доступ к тексту кнопки"""
    return get_message_service().get_button_text(key, locale)

def get_keyboard(keyboard_key: str, locale: str = 'ru'):
    """Быстрый доступ к клавиатуре"""
    return get_message_service().get_keyboard(keyboard_key, locale)

__all__ = [
    'MessageService',
    'MessageValidator', 
    'ValidationResult',
    'TelegramFormatter',
    'MessageConstants',
    'get_message_service',
    'get_message',
    'get_button_text', 
    'get_keyboard'
]