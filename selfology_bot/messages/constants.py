"""
Message Constants and Styling

Centralized constants for emojis, styling, and formatting
"""

from typing import Dict, Any

class MessageConstants:
    """Константы для сообщений"""
    
    # Emojis for different message types
    EMOJI = {
        # Actions
        'welcome': '🌟',
        'success': '✅', 
        'error': '❌',
        'warning': '⚠️',
        'info': 'ℹ️',
        'loading': '⏳',
        'done': '✨',
        
        # Features
        'assessment': '🧠',
        'chat': '💬', 
        'profile': '📊',
        'settings': '⚙️',
        'privacy': '🔒',
        'security': '🛡️',
        'goal': '🎯',
        'insights': '💡',
        'analytics': '📈',
        
        # Psychology
        'personality': '🧩',
        'emotions': '💭',
        'relationships': '👥',
        'growth': '🌱',
        'mindfulness': '🧘',
        
        # Navigation
        'home': '🏠',
        'back': '⬅️',
        'next': '➡️',
        'up': '⬆️',
        'down': '⬇️',
        'menu': '📋',
        
        # Status
        'online': '🟢',
        'offline': '🔴', 
        'busy': '🟡',
        'new': '🆕',
        'hot': '🔥',
        'top': '⭐',
    }
    
    # HTML styles for Telegram
    STYLES = {
        'bold': lambda text: f'<b>{text}</b>',
        'italic': lambda text: f'<i>{text}</i>',
        'underline': lambda text: f'<u>{text}</u>',
        'strike': lambda text: f'<s>{text}</s>',
        'code': lambda text: f'<code>{text}</code>',
        'pre': lambda text: f'<pre>{text}</pre>',
        'link': lambda text, url: f'<a href="{url}">{text}</a>',
    }
    
    # Message separators
    SEPARATORS = {
        'line': '\n' + '─' * 20 + '\n',
        'double_line': '\n' + '═' * 20 + '\n', 
        'dot_line': '\n' + '・' * 10 + '\n',
        'space': '\n\n',
        'small_space': '\n',
    }
    
    # Default parse modes
    PARSE_MODES = {
        'html': 'HTML',
        'markdown': 'Markdown',
        'markdown_v2': 'MarkdownV2', 
        'none': None
    }
    
    # Color schemes (for future theming)
    COLORS = {
        'primary': '#007AFF',   # Blue
        'success': '#34C759',   # Green
        'warning': '#FF9500',   # Orange
        'error': '#FF3B30',     # Red
        'secondary': '#8E8E93', # Gray
        'accent': '#AF52DE',    # Purple
    }
    
    # Maximum message lengths for different platforms
    LIMITS = {
        'telegram_message': 4096,
        'telegram_caption': 1024,
        'button_text': 64,
        'callback_data': 64,
        'inline_query': 256,
    }
    
    # Default locales and fallbacks
    LOCALES = {
        'supported': ['ru', 'en', 'es'],
        'default': 'ru',
        'fallback': 'ru',
    }
    
    @classmethod
    def get_emoji(cls, key: str) -> str:
        """Получить emoji по ключу"""
        return cls.EMOJI.get(key, '🤖')
    
    @classmethod
    def format_with_emoji(cls, emoji_key: str, text: str) -> str:
        """Форматировать текст с emoji"""
        emoji = cls.get_emoji(emoji_key)
        return f"{emoji} {text}"
    
    @classmethod
    def bold(cls, text: str) -> str:
        """Жирный текст"""
        return cls.STYLES['bold'](text)
    
    @classmethod
    def italic(cls, text: str) -> str:
        """Курсив"""
        return cls.STYLES['italic'](text)
    
    @classmethod
    def code(cls, text: str) -> str:
        """Моноширинный текст"""
        return cls.STYLES['code'](text)
    
    @classmethod
    def link(cls, text: str, url: str) -> str:
        """Ссылка"""
        return cls.STYLES['link'](text, url)