"""
Middleware - промежуточные слои обработки

Модули:
- state_logger: Логирование FSM state transitions
"""

from .state_logger import StateLoggerMiddleware

__all__ = ["StateLoggerMiddleware"]
