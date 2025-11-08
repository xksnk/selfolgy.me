"""
Comprehensive logging system for Selfology bot.
Provides structured logging, error tracking, and monitoring capabilities.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import traceback
from contextlib import contextmanager

from ..core.config import settings


class SelfologyFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging"""
    
    def format(self, record):
        # Create base log entry
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add extra fields if they exist
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'username'):
            log_entry['username'] = record.username
        if hasattr(record, 'chat_id'):
            log_entry['chat_id'] = record.chat_id
        if hasattr(record, 'message_type'):
            log_entry['message_type'] = record.message_type
        if hasattr(record, 'ai_model'):
            log_entry['ai_model'] = record.ai_model
        if hasattr(record, 'response_time'):
            log_entry['response_time'] = record.response_time
        if hasattr(record, 'cost'):
            log_entry['cost'] = record.cost
        if hasattr(record, 'error_code'):
            log_entry['error_code'] = record.error_code
        if hasattr(record, 'context'):
            log_entry['context'] = record.context
            
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        return json.dumps(log_entry, ensure_ascii=False, separators=(',', ':'))


class SelfologyLogger:
    """
    Centralized logging system for Selfology bot.
    
    Features:
    - Structured JSON logging
    - Multiple log levels and handlers
    - User activity tracking
    - Error monitoring
    - Performance metrics
    - Real-time alerts
    """
    
    def __init__(self):
        self.setup_logging()
        self.setup_directories()
        
    def setup_directories(self):
        """Create logging directories if they don't exist"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Create subdirectories for different log types
        (log_dir / "bot").mkdir(exist_ok=True)
        (log_dir / "errors").mkdir(exist_ok=True)
        (log_dir / "users").mkdir(exist_ok=True)
        (log_dir / "ai").mkdir(exist_ok=True)
        (log_dir / "metrics").mkdir(exist_ok=True)
    
    def setup_logging(self):
        """Setup comprehensive logging configuration"""
        
        # Root logger configuration
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG if settings.debug else logging.INFO)
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Console handler for development
        if settings.debug:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            root_logger.addHandler(console_handler)
        
        # Main application log (rotating by size)
        app_handler = RotatingFileHandler(
            "logs/selfology.log",
            maxBytes=50*1024*1024,  # 50MB
            backupCount=10,
            encoding='utf-8'
        )
        app_handler.setLevel(logging.INFO)
        app_handler.setFormatter(SelfologyFormatter())
        root_logger.addHandler(app_handler)
        
        # Error log (rotating by time)
        error_handler = TimedRotatingFileHandler(
            "logs/errors/errors.log",
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(SelfologyFormatter())
        root_logger.addHandler(error_handler)
        
        # Bot activity log
        bot_handler = TimedRotatingFileHandler(
            "logs/bot/bot_activity.log",
            when='H',  # Hourly rotation
            interval=1,
            backupCount=168,  # Keep 1 week
            encoding='utf-8'
        )
        bot_handler.setLevel(logging.INFO)
        bot_handler.setFormatter(SelfologyFormatter())
        
        # Create bot-specific logger
        bot_logger = logging.getLogger('selfology.bot')
        bot_logger.addHandler(bot_handler)
        bot_logger.setLevel(logging.INFO)
        
        # User activity log
        user_handler = TimedRotatingFileHandler(
            "logs/users/user_activity.log",
            when='midnight',
            interval=1,
            backupCount=90,  # Keep 3 months
            encoding='utf-8'
        )
        user_handler.setLevel(logging.INFO)
        user_handler.setFormatter(SelfologyFormatter())
        
        user_logger = logging.getLogger('selfology.users')
        user_logger.addHandler(user_handler)
        user_logger.setLevel(logging.INFO)
        
        # AI interactions log
        ai_handler = TimedRotatingFileHandler(
            "logs/ai/ai_interactions.log",
            when='H',
            interval=6,  # Every 6 hours
            backupCount=120,  # Keep 30 days
            encoding='utf-8'
        )
        ai_handler.setLevel(logging.INFO)
        ai_handler.setFormatter(SelfologyFormatter())
        
        ai_logger = logging.getLogger('selfology.ai')
        ai_logger.addHandler(ai_handler)
        ai_logger.setLevel(logging.INFO)
        
        # Metrics log
        metrics_handler = TimedRotatingFileHandler(
            "logs/metrics/metrics.log",
            when='H',
            interval=1,
            backupCount=48,  # Keep 48 hours
            encoding='utf-8'
        )
        metrics_handler.setLevel(logging.INFO)
        metrics_handler.setFormatter(SelfologyFormatter())
        
        metrics_logger = logging.getLogger('selfology.metrics')
        metrics_logger.addHandler(metrics_handler)
        metrics_logger.setLevel(logging.INFO)


class LoggerMixin:
    """Mixin to add logging capabilities to any class"""
    
    @property
    def logger(self):
        """Get logger instance for the class"""
        if not hasattr(self, '_logger'):
            self._logger = logging.getLogger(f'selfology.{self.__class__.__name__}')
        return self._logger
    
    def log_user_action(self, action: str, user_id: int, username: str = None, **kwargs):
        """Log user action with structured data"""
        extra = {
            'user_id': user_id,
            'username': username,
            'context': kwargs
        }
        
        user_logger = logging.getLogger('selfology.users')
        user_logger.info(f"User action: {action}", extra=extra)
    
    def log_bot_event(self, event: str, **kwargs):
        """Log bot event"""
        extra = {'context': kwargs}
        
        bot_logger = logging.getLogger('selfology.bot')
        bot_logger.info(f"Bot event: {event}", extra=extra)
    
    def log_ai_interaction(self, model: str, tokens: int = None, cost: float = None, response_time: float = None, **kwargs):
        """Log AI interaction with metrics"""
        extra = {
            'ai_model': model,
            'response_time': response_time,
            'cost': cost,
            'context': {'tokens': tokens, **kwargs}
        }
        
        ai_logger = logging.getLogger('selfology.ai')
        ai_logger.info(f"AI interaction: {model}", extra=extra)
    
    def log_error(self, error_code: str, message: str, user_id: int = None, **kwargs):
        """Log error with structured information"""
        extra = {
            'error_code': error_code,
            'user_id': user_id,
            'context': kwargs
        }
        
        self.logger.error(f"Error {error_code}: {message}", extra=extra)
    
    def log_metric(self, metric_name: str, value: Any, **kwargs):
        """Log performance metric"""
        extra = {
            'metric_name': metric_name,
            'metric_value': value,
            'context': kwargs
        }
        
        metrics_logger = logging.getLogger('selfology.metrics')
        metrics_logger.info(f"Metric: {metric_name}={value}", extra=extra)


@contextmanager
def log_performance(operation_name: str, logger_instance=None):
    """Context manager to log operation performance"""
    start_time = datetime.now()
    logger_instance = logger_instance or logging.getLogger('selfology.metrics')
    
    try:
        yield
        
        # Success case
        duration = (datetime.now() - start_time).total_seconds()
        extra = {
            'operation': operation_name,
            'response_time': duration,
            'status': 'success'
        }
        logger_instance.info(f"Operation completed: {operation_name}", extra=extra)
        
    except Exception as e:
        # Error case
        duration = (datetime.now() - start_time).total_seconds()
        extra = {
            'operation': operation_name,
            'response_time': duration,
            'status': 'error',
            'error_type': type(e).__name__,
            'error_message': str(e)
        }
        logger_instance.error(f"Operation failed: {operation_name}", extra=extra)
        raise


def setup_exception_handler():
    """Setup global exception handler"""
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        logger = logging.getLogger('selfology.errors')
        logger.critical(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_traceback),
            extra={'error_code': 'UNCAUGHT_EXCEPTION'}
        )
    
    sys.excepthook = handle_exception


# Initialize logging system
logger_system = SelfologyLogger()
setup_exception_handler()

# Export commonly used loggers
bot_logger = logging.getLogger('selfology.bot')
user_logger = logging.getLogger('selfology.users')
ai_logger = logging.getLogger('selfology.ai')
metrics_logger = logging.getLogger('selfology.metrics')
error_logger = logging.getLogger('selfology.errors')


def get_logger(name: str = 'selfology') -> logging.Logger:
    """Get logger instance by name"""
    return logging.getLogger(name)