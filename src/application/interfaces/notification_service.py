"""Notification service interface."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class INotificationService(ABC):
    """Interface for notification operations."""
    
    @abstractmethod
    async def send_telegram_message(
        self,
        telegram_id: int,
        text: str,
        reply_markup: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send message via Telegram bot."""
        pass
    
    @abstractmethod
    async def send_welcome_message(self, telegram_id: int, user_name: str) -> bool:
        """Send welcome message to new user."""
        pass
    
    @abstractmethod
    async def send_assessment_reminder(self, telegram_id: int) -> bool:
        """Send assessment completion reminder."""
        pass
    
    @abstractmethod
    async def send_daily_checkin(self, telegram_id: int) -> bool:
        """Send daily check-in notification."""
        pass
    
    @abstractmethod
    async def send_insights_notification(
        self,
        telegram_id: int,
        insights: Dict[str, Any]
    ) -> bool:
        """Send personality insights notification."""
        pass
    
    @abstractmethod
    async def send_tier_limit_warning(
        self,
        telegram_id: int,
        limit_type: str,
        usage_percentage: float
    ) -> bool:
        """Send tier limit warning."""
        pass