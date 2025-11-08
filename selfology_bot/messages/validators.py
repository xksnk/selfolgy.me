"""
Message Validators

Validation system for message templates, HTML safety, and Telegram compatibility
"""

import re
import html
from typing import Dict, List, Set, Optional
from pydantic import BaseModel, ValidationError
from dataclasses import dataclass

@dataclass
class ValidationResult:
    """Результат валидации"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    
    def add_error(self, error: str):
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str):
        self.warnings.append(warning)

class MessageValidator:
    """Валидатор сообщений для Telegram"""
    
    # Разрешенные HTML теги в Telegram
    TELEGRAM_HTML_TAGS = {
        'b', 'strong',     # жирный
        'i', 'em',         # курсив  
        'u', 'ins',        # подчеркнутый
        's', 'strike', 'del', # зачеркнутый
        'code',            # моноширинный
        'pre',             # преформатированный
        'a'                # ссылка
    }
    
    # Опасные паттерны для XSS
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'onclick\s*=',
        r'onload\s*=', 
        r'onerror\s*=',
        r'data:text/html',
        r'vbscript:',
    ]
    
    # Паттерн для извлечения переменных Jinja2
    JINJA_VAR_PATTERN = r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\s*\}\}'
    
    def validate_template(self, template: str, required_vars: Optional[Set[str]] = None) -> ValidationResult:
        """Полная валидация шаблона"""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # Проверка на пустоту
        if not template or not template.strip():
            result.add_error("Template is empty")
            return result
        
        # Проверка длины
        if len(template) > 4096:
            result.add_error(f"Template too long: {len(template)} characters (max 4096)")
        
        # Валидация HTML
        html_result = self.validate_telegram_html(template)
        if not html_result.is_valid:
            result.errors.extend(html_result.errors)
            result.warnings.extend(html_result.warnings)
        
        # Проверка безопасности
        security_result = self.check_template_security(template)
        if not security_result.is_valid:
            result.errors.extend(security_result.errors)
        
        # Проверка переменных Jinja2
        template_vars = self.extract_template_variables(template)
        if required_vars:
            missing_vars = required_vars - template_vars
            if missing_vars:
                result.add_error(f"Missing required variables: {missing_vars}")
            
            extra_vars = template_vars - required_vars
            if extra_vars:
                result.add_warning(f"Extra variables found: {extra_vars}")
        
        # Проверка синтаксиса Jinja2
        jinja_result = self.validate_jinja_syntax(template)
        if not jinja_result.is_valid:
            result.errors.extend(jinja_result.errors)
        
        return result
    
    def validate_telegram_html(self, text: str) -> ValidationResult:
        """Валидация HTML для Telegram"""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # Поиск всех HTML тегов
        tag_pattern = r'<(/?)(\w+)(?:\s[^>]*)?/?>'
        tags = re.findall(tag_pattern, text, re.IGNORECASE)
        
        tag_stack = []
        for is_closing, tag_name in tags:
            tag_lower = tag_name.lower()
            
            # Проверка разрешенных тегов
            if tag_lower not in self.TELEGRAM_HTML_TAGS:
                result.add_error(f"Unsupported HTML tag: <{tag_name}>")
                continue
            
            # Проверка вложенности тегов
            if is_closing:
                if not tag_stack:
                    result.add_error(f"Closing tag without opening: </{tag_name}>")
                elif tag_stack[-1].lower() != tag_lower:
                    result.add_error(f"Mismatched closing tag: </{tag_name}>, expected </{tag_stack[-1]}>")
                else:
                    tag_stack.pop()
            else:
                # Самозакрывающиеся теги не добавляем в стек
                if not text.count(f'<{tag_name}') == text.count(f'</{tag_name}'):
                    tag_stack.append(tag_name)
        
        # Проверка незакрытых тегов
        if tag_stack:
            result.add_error(f"Unclosed tags: {tag_stack}")
        
        # Проверка атрибутов ссылок
        link_pattern = r'<a\s+href\s*=\s*["\']([^"\']+)["\'][^>]*>'
        links = re.findall(link_pattern, text, re.IGNORECASE)
        for link in links:
            if not self._is_safe_url(link):
                result.add_warning(f"Potentially unsafe URL: {link}")
        
        return result
    
    def check_template_security(self, template: str) -> ValidationResult:
        """Проверка безопасности шаблона"""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # Проверка на опасные паттерны
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, template, re.IGNORECASE):
                result.add_error(f"Dangerous pattern detected: {pattern}")
        
        # Проверка на потенциальную инъекцию
        if '{{' in template and '}}' in template:
            # Проверка на попытки выполнения кода
            dangerous_jinja = [
                r'\{\{.*__.*\}\}',  # Доступ к внутренним атрибутам
                r'\{\{.*import.*\}\}',  # Импорт модулей
                r'\{\{.*exec.*\}\}',  # Выполнение кода
                r'\{\{.*eval.*\}\}',  # Оценка выражений
            ]
            
            for pattern in dangerous_jinja:
                if re.search(pattern, template, re.IGNORECASE):
                    result.add_error(f"Dangerous Jinja2 pattern: {pattern}")
        
        return result
    
    def extract_template_variables(self, template: str) -> Set[str]:
        """Извлечение переменных из Jinja2 шаблона"""
        variables = set()
        
        # Поиск переменных вида {{ variable }}
        matches = re.findall(self.JINJA_VAR_PATTERN, template)
        for match in matches:
            # Берем только первую часть для вложенных объектов (user.name -> user)
            var_name = match.split('.')[0]
            variables.add(var_name)
        
        return variables
    
    def validate_jinja_syntax(self, template: str) -> ValidationResult:
        """Проверка синтаксиса Jinja2"""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        try:
            from jinja2 import Environment, Template, TemplateSyntaxError
            env = Environment()
            env.from_string(template)
        except TemplateSyntaxError as e:
            result.add_error(f"Jinja2 syntax error: {e}")
        except ImportError:
            result.add_warning("Jinja2 not installed, skipping syntax validation")
        except Exception as e:
            result.add_error(f"Template validation error: {e}")
        
        return result
    
    def validate_button_text(self, text: str) -> ValidationResult:
        """Валидация текста кнопки"""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        if not text or not text.strip():
            result.add_error("Button text is empty")
            return result
        
        if len(text) > 64:
            result.add_error(f"Button text too long: {len(text)} characters (max 64)")
        
        if len(text) < 1:
            result.add_error("Button text too short")
        
        # Кнопки не должны содержать HTML
        if '<' in text and '>' in text:
            result.add_warning("HTML tags in button text will be displayed as plain text")
        
        return result
    
    def validate_callback_data(self, data: str) -> ValidationResult:
        """Валидация callback_data"""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        if not data:
            result.add_error("Callback data is empty")
            return result
        
        if len(data) > 64:
            result.add_error(f"Callback data too long: {len(data)} characters (max 64)")
        
        # Проверка на допустимые символы
        if not re.match(r'^[a-zA-Z0-9_\-:.]+$', data):
            result.add_warning("Callback data contains special characters")
        
        return result
    
    def _is_safe_url(self, url: str) -> bool:
        """Проверка безопасности URL"""
        safe_schemes = ['http', 'https', 'tg', 'mailto']
        
        # Простая проверка схемы
        if ':' in url:
            scheme = url.split(':', 1)[0].lower()
            return scheme in safe_schemes
        
        # Относительные URL считаем безопасными
        return not url.startswith('javascript:') and not url.startswith('data:')

class MessageTemplateModel(BaseModel):
    """Pydantic модель для валидации шаблона сообщения"""
    template: str
    variables: List[str] = []
    parse_mode: Optional[str] = 'HTML'
    max_length: int = 4096
    
    def validate_template_content(self):
        """Валидация содержимого шаблона"""
        validator = MessageValidator()
        result = validator.validate_template(
            self.template, 
            set(self.variables) if self.variables else None
        )
        
        if not result.is_valid:
            raise ValueError(f"Template validation failed: {', '.join(result.errors)}")
        
        return result