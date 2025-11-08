"""
Message Service

Core service for centralized message management with i18n support
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional, Any, List
from functools import lru_cache

from jinja2 import Environment, FileSystemLoader, Template, TemplateSyntaxError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from .validators import MessageValidator, ValidationResult
from .formatters import TelegramFormatter, RichMessageBuilder
from .constants import MessageConstants

logger = logging.getLogger(__name__)

class MessageService:
    """Централизованный сервис сообщений"""
    
    def __init__(self, templates_dir: Optional[str] = None, debug_mode: bool = False):
        if templates_dir is None:
            # Определяем путь к шаблонам относительно этого файла
            current_file = Path(__file__)
            templates_dir = current_file.parent / "templates"
        
        self.templates_dir = Path(templates_dir)
        self.debug_mode = debug_mode
        self.validator = MessageValidator()
        self.formatter = TelegramFormatter()
        self.constants = MessageConstants()
        
        # Настройка Jinja2
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=False,  # Мы сами контролируем экранирование
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Кэш загруженных шаблонов
        self._templates_cache: Dict[str, Dict[str, Any]] = {}
        self._keyboards_cache: Dict[str, Dict[str, Any]] = {}
        
        # Загрузка всех шаблонов при инициализации
        self._load_all_templates()
        
        logger.info(f"MessageService initialized with templates from {self.templates_dir}")
    
    def _load_all_templates(self):
        """Загрузка всех шаблонов из файлов"""
        if not self.templates_dir.exists():
            logger.warning(f"Templates directory not found: {self.templates_dir}")
            return
        
        for locale_dir in self.templates_dir.iterdir():
            if locale_dir.is_dir() and locale_dir.name in self.constants.LOCALES['supported']:
                self._load_locale_templates(locale_dir.name)
    
    def _load_locale_templates(self, locale: str):
        """Загрузка шаблонов для конкретной локали"""
        locale_path = self.templates_dir / locale
        
        if not locale_path.exists():
            logger.warning(f"Locale directory not found: {locale_path}")
            return
        
        self._templates_cache[locale] = {}
        self._keyboards_cache[locale] = {}
        
        # Загрузка JSON файлов
        for json_file in locale_path.glob("*.json"):
            try:
                with json_file.open('r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                category = json_file.stem
                
                # Разделяем сообщения и клавиатуры
                if 'keyboards' in data:
                    self._keyboards_cache[locale][category] = data['keyboards']
                    # Удаляем keyboards из основных данных
                    data = {k: v for k, v in data.items() if k != 'keyboards'}
                
                if data:  # Если остались данные кроме keyboards
                    self._templates_cache[locale][category] = data
                    
                logger.debug(f"Loaded templates for {locale}/{category}")
                
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Failed to load {json_file}: {e}")
    
    @lru_cache(maxsize=1000)
    def get_message(self, key: str, locale: str = 'ru', 
                   category: str = 'general', **kwargs) -> str:
        """Получить сообщение с подстановкой переменных"""
        
        # Получаем шаблон
        template_data = self._get_template_data(key, locale, category)
        if not template_data:
            return f"[MISSING: {locale}.{category}.{key}]"
        
        template_str = template_data.get('template', '')
        if not template_str:
            return f"[EMPTY_TEMPLATE: {locale}.{category}.{key}]"
        
        # Рендеринг шаблона
        try:
            template = self.jinja_env.from_string(template_str)
            rendered = template.render(**kwargs)
            
            # Очистка и валидация результата
            cleaned = self.formatter.clean_telegram_text(rendered)
            
            # Проверка длины
            if len(cleaned) > 4096:
                cleaned = self.formatter.truncate_message(cleaned)
                logger.warning(f"Message truncated: {locale}.{category}.{key}")
            
            # 🔧 Добавляем debug информацию если включен debug режим
            if self.debug_mode:
                debug_info = f"\n─────────────────────\n🔧 <b>DEBUG:</b> <code>{key}</code> | <i>{category}.json</i>"
                
                # Проверяем что добавление debug инфо не превышает лимит
                total_length = len(cleaned) + len(debug_info)
                if total_length <= 4096:
                    cleaned += debug_info
                else:
                    # Обрезаем основное сообщение чтобы поместилась debug инфо
                    max_content = 4096 - len(debug_info) - 10  # -10 для безопасности
                    cleaned = self.formatter.truncate_message(cleaned, max_content)
                    cleaned += debug_info
            
            return cleaned
            
        except TemplateSyntaxError as e:
            logger.error(f"Template syntax error in {locale}.{category}.{key}: {e}")
            return f"[TEMPLATE_ERROR: {e}]"
        
        except Exception as e:
            logger.error(f"Error rendering template {locale}.{category}.{key}: {e}")
            return f"[RENDER_ERROR: {e}]"
    
    def get_button_text(self, key: str, locale: str = 'ru') -> str:
        """Получить текст кнопки"""
        return self.get_message(key, locale, 'buttons')
    
    def get_keyboard(self, keyboard_key: str, locale: str = 'ru') -> Optional[InlineKeyboardMarkup]:
        """Получить готовую клавиатуру"""
        keyboard_data = self._get_keyboard_data(keyboard_key, locale)
        if not keyboard_data:
            logger.warning(f"Keyboard not found: {locale}.{keyboard_key}")
            return None
        
        try:
            return self._build_keyboard(keyboard_data)
        except Exception as e:
            logger.error(f"Error building keyboard {locale}.{keyboard_key}: {e}")
            return None
    
    def get_rich_message_builder(self, locale: str = 'ru') -> RichMessageBuilder:
        """Получить построитель сообщений"""
        return RichMessageBuilder(locale)
    
    def validate_template(self, key: str, locale: str = 'ru', 
                         category: str = 'general') -> ValidationResult:
        """Валидация шаблона"""
        template_data = self._get_template_data(key, locale, category)
        if not template_data:
            result = ValidationResult(is_valid=False, errors=[], warnings=[])
            result.add_error(f"Template not found: {locale}.{category}.{key}")
            return result
        
        template_str = template_data.get('template', '')
        variables = set(template_data.get('variables', []))
        
        return self.validator.validate_template(template_str, variables)
    
    def reload_templates(self):
        """Перезагрузка всех шаблонов"""
        self._templates_cache.clear()
        self._keyboards_cache.clear()
        self.get_message.cache_clear()  # Очистка кэша LRU
        self._load_all_templates()
        logger.info("Templates reloaded")
    
    def get_available_locales(self) -> List[str]:
        """Получить список доступных локалей"""
        return list(self._templates_cache.keys())
    
    def get_available_categories(self, locale: str = 'ru') -> List[str]:
        """Получить список категорий для локали"""
        return list(self._templates_cache.get(locale, {}).keys())
    
    def get_message_keys(self, locale: str = 'ru', category: str = 'general') -> List[str]:
        """Получить список ключей сообщений для категории"""
        category_data = self._templates_cache.get(locale, {}).get(category, {})
        return list(category_data.keys())
    
    def _get_template_data(self, key: str, locale: str, category: str) -> Optional[Dict[str, Any]]:
        """Получить данные шаблона с fallback"""
        
        # Попытка получить из указанной локали
        template_data = (self._templates_cache
                        .get(locale, {})
                        .get(category, {})
                        .get(key))
        
        if template_data:
            return template_data
        
        # Fallback на русский язык
        if locale != 'ru':
            template_data = (self._templates_cache
                           .get('ru', {})
                           .get(category, {})
                           .get(key))
            
            if template_data:
                logger.debug(f"Using fallback ru for {locale}.{category}.{key}")
                return template_data
        
        # Попытка найти в других категориях той же локали
        for cat_name, cat_data in self._templates_cache.get(locale, {}).items():
            if key in cat_data:
                logger.debug(f"Found {key} in category {cat_name} instead of {category}")
                return cat_data[key]
        
        return None
    
    def _get_keyboard_data(self, keyboard_key: str, locale: str) -> Optional[Dict[str, Any]]:
        """Получить данные клавиатуры с fallback"""
        
        # Поиск по всем категориям
        for category_keyboards in self._keyboards_cache.get(locale, {}).values():
            if keyboard_key in category_keyboards:
                return category_keyboards[keyboard_key]
        
        # Fallback на русский
        if locale != 'ru':
            for category_keyboards in self._keyboards_cache.get('ru', {}).values():
                if keyboard_key in category_keyboards:
                    logger.debug(f"Using fallback ru keyboard for {locale}.{keyboard_key}")
                    return category_keyboards[keyboard_key]
        
        return None
    
    def _build_keyboard(self, keyboard_data: Dict[str, Any]) -> InlineKeyboardMarkup:
        """Построение клавиатуры из данных"""
        buttons_data = keyboard_data.get('buttons', [])
        
        keyboard = []
        for row in buttons_data:
            button_row = []
            for button_config in row:
                if isinstance(button_config, dict):
                    text = button_config.get('text', '')
                    callback_data = button_config.get('callback_data', '')
                    url = button_config.get('url')
                    
                    # Валидация кнопки
                    text_result = self.validator.validate_button_text(text)
                    if not text_result.is_valid:
                        logger.warning(f"Invalid button text: {text_result.errors}")
                        continue
                    
                    if callback_data:
                        callback_result = self.validator.validate_callback_data(callback_data)
                        if not callback_result.is_valid:
                            logger.warning(f"Invalid callback_data: {callback_result.errors}")
                            continue
                        
                        button = InlineKeyboardButton(text=text, callback_data=callback_data)
                    elif url:
                        button = InlineKeyboardButton(text=text, url=url)
                    else:
                        logger.warning(f"Button without callback_data or url: {button_config}")
                        continue
                    
                    button_row.append(button)
            
            if button_row:  # Добавляем ряд только если есть валидные кнопки
                keyboard.append(button_row)
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    def export_templates(self, locale: str = 'ru') -> Dict[str, Any]:
        """Экспорт всех шаблонов локали"""
        return {
            'messages': self._templates_cache.get(locale, {}),
            'keyboards': self._keyboards_cache.get(locale, {})
        }
    
    def import_templates(self, data: Dict[str, Any], locale: str = 'ru'):
        """Импорт шаблонов"""
        if 'messages' in data:
            self._templates_cache[locale] = data['messages']
        
        if 'keyboards' in data:
            self._keyboards_cache[locale] = data['keyboards']
        
        self.get_message.cache_clear()  # Очистка кэша
        logger.info(f"Templates imported for locale: {locale}")