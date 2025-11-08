"""
Lifecycle Management - управление жизненным циклом бота

Модули:
- instance_lock: Redis-based distributed lock для предотвращения дублей
- bot_lifecycle: Инициализация, запуск, graceful shutdown
"""

from .instance_lock import BotInstanceLock
from .bot_lifecycle import BotLifecycle

__all__ = ["BotInstanceLock", "BotLifecycle"]
