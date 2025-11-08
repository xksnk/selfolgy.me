"""
Comprehensive error handling and tracking system for Selfology bot.
"""

import asyncio
import functools
import logging
import traceback
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional, Type, Union
from enum import Enum

from aiogram import types
from aiogram.fsm.context import FSMContext

from .logging import LoggerMixin, get_logger


class ErrorCode(Enum):
    """Standardized error codes for tracking and debugging"""
    
    # Bot errors
    BOT_INIT_ERROR = "BOT_001"
    BOT_UPDATE_ERROR = "BOT_002" 
    BOT_WEBHOOK_ERROR = "BOT_003"
    BOT_POLLING_ERROR = "BOT_004"
    
    # User interaction errors
    USER_NOT_FOUND = "USER_001"
    USER_STATE_ERROR = "USER_002"
    USER_PERMISSION_ERROR = "USER_003"
    USER_INPUT_INVALID = "USER_004"
    
    # AI service errors
    AI_API_ERROR = "AI_001"
    AI_TIMEOUT_ERROR = "AI_002"
    AI_QUOTA_ERROR = "AI_003"
    AI_MODEL_ERROR = "AI_004"
    AI_ROUTING_ERROR = "AI_005"
    
    # Database errors
    DB_CONNECTION_ERROR = "DB_001"
    DB_QUERY_ERROR = "DB_002"
    DB_INTEGRITY_ERROR = "DB_003"
    DB_TIMEOUT_ERROR = "DB_004"
    
    # Vector database errors
    VECTOR_CONNECTION_ERROR = "VDB_001"
    VECTOR_SEARCH_ERROR = "VDB_002"
    VECTOR_INSERT_ERROR = "VDB_003"
    
    # External service errors
    N8N_API_ERROR = "EXT_001"
    WEBHOOK_ERROR = "EXT_002"
    
    # System errors
    MEMORY_ERROR = "SYS_001"
    TIMEOUT_ERROR = "SYS_002"
    CONFIGURATION_ERROR = "SYS_003"
    UNKNOWN_ERROR = "SYS_999"


class SelfologyException(Exception):
    """Base exception class for Selfology bot"""
    
    def __init__(
        self, 
        message: str, 
        error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        user_id: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.user_id = user_id
        self.context = context or {}
        self.timestamp = datetime.now(timezone.utc)
        
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging"""
        return {
            'error_code': self.error_code.value,
            'message': self.message,
            'user_id': self.user_id,
            'context': self.context,
            'timestamp': self.timestamp.isoformat(),
            'type': self.__class__.__name__
        }


class UserError(SelfologyException):
    """User-related errors"""
    pass


class AIServiceError(SelfologyException):
    """AI service related errors"""
    pass


class DatabaseError(SelfologyException):
    """Database related errors"""
    pass


class VectorDatabaseError(SelfologyException):
    """Vector database related errors"""
    pass


class ExternalServiceError(SelfologyException):
    """External service errors"""
    pass


class ErrorTracker(LoggerMixin):
    """
    Central error tracking and handling system.
    Collects, categorizes, and reports errors with context.
    """
    
    def __init__(self):
        self.error_counts = {}
        self.error_history = []
        self.error_logger = get_logger('selfology.errors')
    
    def track_error(
        self,
        error: Exception,
        error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        user_id: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        severity: str = "ERROR"
    ):
        """Track error with full context and metrics"""
        
        error_data = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'error_code': error_code.value,
            'user_id': user_id,
            'context': context or {},
            'traceback': traceback.format_exc(),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'severity': severity
        }
        
        # Log structured error
        extra = {
            'error_code': error_code.value,
            'user_id': user_id,
            'context': context or {}
        }
        
        if severity == "CRITICAL":
            self.error_logger.critical(f"Critical error: {error}", extra=extra, exc_info=True)
        elif severity == "ERROR":
            self.error_logger.error(f"Error: {error}", extra=extra, exc_info=True)
        elif severity == "WARNING":
            self.error_logger.warning(f"Warning: {error}", extra=extra, exc_info=True)
        
        # Update error statistics
        self.error_counts[error_code.value] = self.error_counts.get(error_code.value, 0) + 1
        self.error_history.append(error_data)
        
        # Keep only recent errors in memory (last 1000)
        if len(self.error_history) > 1000:
            self.error_history = self.error_history[-1000:]
        
        return error_data
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics for monitoring"""
        return {
            'total_errors': sum(self.error_counts.values()),
            'error_counts_by_code': self.error_counts.copy(),
            'recent_errors': len([e for e in self.error_history 
                                if (datetime.now(timezone.utc) - datetime.fromisoformat(e['timestamp'])).seconds < 3600])
        }


# Global error tracker instance
error_tracker = ErrorTracker()


def handle_errors(
    error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
    user_message: str = "Произошла техническая ошибка. Попробуйте позже.",
    log_traceback: bool = True,
    severity: str = "ERROR"
):
    """
    Decorator for handling errors in bot handlers and functions.
    
    Args:
        error_code: Standardized error code
        user_message: Message to send to user
        log_traceback: Whether to log full traceback
        severity: Error severity level
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except SelfologyException as e:
                # Handle known application errors
                error_tracker.track_error(e, e.error_code, e.user_id, e.context, severity)
                await handle_user_error(args, e.message, e.user_id)
                return None
            except Exception as e:
                # Handle unknown errors
                user_id = extract_user_id_from_args(args)
                context = {'function': func.__name__, 'args': str(args)[:200]}
                
                error_tracker.track_error(e, error_code, user_id, context, severity)
                await handle_user_error(args, user_message, user_id)
                return None
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except SelfologyException as e:
                error_tracker.track_error(e, e.error_code, e.user_id, e.context, severity)
                return None
            except Exception as e:
                user_id = extract_user_id_from_args(args)
                context = {'function': func.__name__, 'args': str(args)[:200]}
                
                error_tracker.track_error(e, error_code, user_id, context, severity)
                return None
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def extract_user_id_from_args(args) -> Optional[int]:
    """Extract user ID from function arguments"""
    for arg in args:
        if isinstance(arg, (types.Message, types.CallbackQuery)):
            return arg.from_user.id
        elif hasattr(arg, 'from_user') and hasattr(arg.from_user, 'id'):
            return arg.from_user.id
    return None


async def handle_user_error(args, message: str, user_id: Optional[int] = None):
    """Send error message to user if possible"""
    try:
        for arg in args:
            if isinstance(arg, types.Message):
                await arg.answer(f"❌ {message}")
                return
            elif isinstance(arg, types.CallbackQuery):
                await arg.message.edit_text(f"❌ {message}")
                return
    except Exception as e:
        # Failed to send error message to user
        logger = get_logger('selfology.errors')
        logger.warning(f"Failed to send error message to user {user_id}: {e}")


class ErrorMonitor(LoggerMixin):
    """
    Monitor error patterns and trigger alerts when needed.
    """
    
    def __init__(self):
        self.alert_thresholds = {
            'errors_per_minute': 10,
            'critical_errors_per_hour': 5,
            'user_errors_per_user_per_hour': 20
        }
    
    async def check_error_patterns(self):
        """Check for error patterns that require attention"""
        stats = error_tracker.get_error_stats()
        
        # Check recent error rate
        if stats['recent_errors'] > self.alert_thresholds['errors_per_minute']:
            await self.trigger_alert(
                "HIGH_ERROR_RATE",
                f"High error rate detected: {stats['recent_errors']} errors in last hour"
            )
        
        # Check for specific error codes that need attention
        critical_codes = [ErrorCode.AI_API_ERROR, ErrorCode.DB_CONNECTION_ERROR]
        for code in critical_codes:
            if stats['error_counts_by_code'].get(code.value, 0) > 5:
                await self.trigger_alert(
                    "CRITICAL_ERROR_PATTERN",
                    f"Multiple {code.value} errors detected"
                )
    
    async def trigger_alert(self, alert_type: str, message: str):
        """Trigger alert for critical errors"""
        alert_logger = get_logger('selfology.alerts')
        
        extra = {
            'alert_type': alert_type,
            'context': {'error_stats': error_tracker.get_error_stats()}
        }
        
        alert_logger.critical(f"ALERT: {message}", extra=extra)
        
        # Could integrate with external alerting systems here
        # e.g., Slack, Discord, email notifications


# Global error monitor
error_monitor = ErrorMonitor()


# Convenience functions for common error scenarios
def raise_user_error(message: str, error_code: ErrorCode, user_id: int = None, **context):
    """Raise a user-facing error"""
    raise UserError(message, error_code, user_id, context)


def raise_ai_error(message: str, error_code: ErrorCode, user_id: int = None, **context):
    """Raise an AI service error"""
    raise AIServiceError(message, error_code, user_id, context)


def raise_db_error(message: str, error_code: ErrorCode, user_id: int = None, **context):
    """Raise a database error"""
    raise DatabaseError(message, error_code, user_id, context)


def raise_vector_error(message: str, error_code: ErrorCode, user_id: int = None, **context):
    """Raise a vector database error"""
    raise VectorDatabaseError(message, error_code, user_id, context)


def raise_external_error(message: str, error_code: ErrorCode, user_id: int = None, **context):
    """Raise an external service error"""
    raise ExternalServiceError(message, error_code, user_id, context)