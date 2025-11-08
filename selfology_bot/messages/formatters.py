"""
Telegram Formatters

Safe formatting utilities for Telegram messages with HTML support
"""

import html
import re
from typing import Dict, Any, Optional, Union
from .constants import MessageConstants

class TelegramFormatter:
    """Форматтер для Telegram сообщений"""
    
    def __init__(self):
        self.constants = MessageConstants()
    
    def escape_html(self, text: str) -> str:
        """Экранирование HTML символов"""
        if not text:
            return ""
        
        # Базовое экранирование HTML
        text = html.escape(str(text))
        
        # Дополнительная обработка для Telegram
        # Некоторые символы нужно экранировать особым образом
        replacements = {
            '&lt;': '<',    # Возвращаем < для HTML тегов
            '&gt;': '>',    # Возвращаем > для HTML тегов  
            '&amp;': '&',   # Возвращаем & для HTML entities
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        return text
    
    def safe_format(self, template: str, **kwargs) -> str:
        """Безопасное форматирование с экранированием"""
        # Экранируем все переменные
        safe_kwargs = {}
        for key, value in kwargs.items():
            if isinstance(value, (str, int, float)):
                safe_kwargs[key] = self.escape_html(str(value))
            else:
                safe_kwargs[key] = str(value)
        
        try:
            return template.format(**safe_kwargs)
        except KeyError as e:
            # Заменяем недостающие переменные на placeholder
            missing_var = e.args[0]
            safe_kwargs[missing_var] = f"[MISSING: {missing_var}]"
            return template.format(**safe_kwargs)
        except (ValueError, TypeError) as e:
            return f"[FORMAT_ERROR: {e}]"
    
    def format_user_mention(self, user_id: Union[str, int], name: str, 
                          link: bool = False) -> str:
        """Форматирование упоминания пользователя"""
        safe_name = self.escape_html(name)
        
        if link:
            return f'<a href="tg://user?id={user_id}">{safe_name}</a>'
        else:
            return f"<b>{safe_name}</b>"
    
    def format_list(self, items: list, style: str = 'bullet') -> str:
        """Форматирование списка"""
        if not items:
            return ""
        
        styles = {
            'bullet': '•',
            'number': lambda i: f"{i+1}.",
            'check': '✅',
            'arrow': '➤',
            'dash': '—'
        }
        
        formatted_items = []
        for i, item in enumerate(items):
            safe_item = self.escape_html(str(item))
            
            if style == 'number':
                prefix = styles[style](i)
            else:
                prefix = styles.get(style, '•')
            
            formatted_items.append(f"{prefix} {safe_item}")
        
        return '\n'.join(formatted_items)
    
    def format_progress_bar(self, current: int, total: int, 
                          width: int = 10, filled: str = '█', 
                          empty: str = '░') -> str:
        """Форматирование прогресс-бара"""
        if total == 0:
            return empty * width
        
        progress = min(current / total, 1.0)
        filled_width = int(progress * width)
        empty_width = width - filled_width
        
        bar = filled * filled_width + empty * empty_width
        percentage = int(progress * 100)
        
        return f"{bar} {percentage}%"
    
    def format_table(self, data: Dict[str, Any], 
                    headers: bool = True) -> str:
        """Простое форматирование таблицы"""
        if not data:
            return ""
        
        lines = []
        
        for key, value in data.items():
            safe_key = self.escape_html(str(key))
            safe_value = self.escape_html(str(value))
            
            if headers:
                lines.append(f"<b>{safe_key}:</b> {safe_value}")
            else:
                lines.append(f"{safe_key}: {safe_value}")
        
        return '\n'.join(lines)
    
    def format_code_block(self, code: str, language: str = "") -> str:
        """Форматирование блока кода"""
        safe_code = self.escape_html(code)
        
        if language:
            return f"<pre><code class=\"{language}\">{safe_code}</code></pre>"
        else:
            return f"<pre>{safe_code}</pre>"
    
    def format_inline_code(self, code: str) -> str:
        """Форматирование инлайн кода"""
        safe_code = self.escape_html(code)
        return f"<code>{safe_code}</code>"
    
    def format_link(self, text: str, url: str, 
                   validate_url: bool = True) -> str:
        """Форматирование ссылки"""
        safe_text = self.escape_html(text)
        
        if validate_url and not self._is_valid_url(url):
            return f"{safe_text} [INVALID_URL]"
        
        return f'<a href="{url}">{safe_text}</a>'
    
    def format_quote(self, text: str, author: str = "") -> str:
        """Форматирование цитаты"""
        safe_text = self.escape_html(text)
        safe_author = self.escape_html(author) if author else ""
        
        quote = f"<i>«{safe_text}»</i>"
        if author:
            quote += f"\n— <b>{safe_author}</b>"
        
        return quote
    
    def format_spoiler(self, text: str) -> str:
        """Форматирование спойлера (скрытый текст)"""
        safe_text = self.escape_html(text)
        # Telegram пока не поддерживает spoiler теги официально
        # Используем альтернативное форматирование
        return f"<i>[spoiler] {safe_text}</i>"
    
    def format_emoji_text(self, emoji_key: str, text: str, 
                         bold: bool = False) -> str:
        """Форматирование текста с emoji"""
        emoji = self.constants.get_emoji(emoji_key)
        safe_text = self.escape_html(text)
        
        formatted_text = f"{emoji} {safe_text}"
        
        if bold:
            formatted_text = f"<b>{formatted_text}</b>"
        
        return formatted_text
    
    def truncate_message(self, text: str, max_length: int = 4096, 
                        suffix: str = "...") -> str:
        """Обрезка сообщения до максимальной длины"""
        if len(text) <= max_length:
            return text
        
        # Пытаемся обрезать по границам слов
        truncated = text[:max_length - len(suffix)]
        
        # Находим последний пробел
        last_space = truncated.rfind(' ')
        if last_space > max_length * 0.8:  # Если пробел не слишком далеко
            truncated = truncated[:last_space]
        
        return truncated + suffix
    
    def clean_telegram_text(self, text: str) -> str:
        """Очистка текста для Telegram"""
        if not text:
            return ""
        
        # Удаляем лишние переносы строк
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Удаляем пробелы в начале и конце строк
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        # Удаляем пробелы в начале и конце всего текста
        text = text.strip()
        
        return text
    
    def format_multiline(self, lines: list, separator: str = '\n') -> str:
        """Форматирование многострочного текста"""
        safe_lines = [self.escape_html(str(line)) for line in lines if line]
        return separator.join(safe_lines)
    
    def _is_valid_url(self, url: str) -> bool:
        """Простая проверка валидности URL"""
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+'
            r'(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        return url_pattern.match(url) is not None

class RichMessageBuilder:
    """Построитель сложных сообщений"""
    
    def __init__(self, locale: str = 'ru'):
        self.locale = locale
        self.formatter = TelegramFormatter()
        self.constants = MessageConstants()
        self.parts = []
    
    def add_header(self, text: str, emoji_key: str = None) -> 'RichMessageBuilder':
        """Добавить заголовок"""
        if emoji_key:
            emoji = self.constants.get_emoji(emoji_key)
            formatted = f"{emoji} <b>{self.formatter.escape_html(text)}</b>"
        else:
            formatted = f"<b>{self.formatter.escape_html(text)}</b>"
        
        self.parts.append(formatted)
        return self
    
    def add_text(self, text: str, **kwargs) -> 'RichMessageBuilder':
        """Добавить обычный текст"""
        formatted = self.formatter.safe_format(text, **kwargs)
        self.parts.append(formatted)
        return self
    
    def add_list(self, items: list, style: str = 'bullet') -> 'RichMessageBuilder':
        """Добавить список"""
        formatted_list = self.formatter.format_list(items, style)
        self.parts.append(formatted_list)
        return self
    
    def add_separator(self, style: str = 'line') -> 'RichMessageBuilder':
        """Добавить разделитель"""
        separator = self.constants.SEPARATORS.get(style, '\n')
        self.parts.append(separator)
        return self
    
    def add_link(self, text: str, url: str) -> 'RichMessageBuilder':
        """Добавить ссылку"""
        link = self.formatter.format_link(text, url)
        self.parts.append(link)
        return self
    
    def add_quote(self, text: str, author: str = "") -> 'RichMessageBuilder':
        """Добавить цитату"""
        quote = self.formatter.format_quote(text, author)
        self.parts.append(quote)
        return self
    
    def build(self) -> str:
        """Собрать сообщение"""
        message = '\n'.join(self.parts)
        return self.formatter.clean_telegram_text(message)
    
    def clear(self) -> 'RichMessageBuilder':
        """Очистить построитель"""
        self.parts.clear()
        return self