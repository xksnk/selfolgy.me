"""User repository interface."""

from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID

from ..entities import User
from ..value_objects import TelegramId


class IUserRepository(ABC):
    """User repository interface."""
    
    @abstractmethod
    async def create(self, user: User) -> User:
        """Create a new user."""
        pass
    
    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        pass
    
    @abstractmethod
    async def get_by_telegram_id(self, telegram_id: TelegramId) -> Optional[User]:
        """Get user by Telegram ID."""
        pass
    
    @abstractmethod
    async def update(self, user: User) -> User:
        """Update user."""
        pass
    
    @abstractmethod
    async def delete(self, user_id: UUID) -> bool:
        """Delete user."""
        pass
    
    @abstractmethod
    async def get_all_by_tier(self, tier: str) -> List[User]:
        """Get all users by tier."""
        pass
    
    @abstractmethod
    async def count_total_users(self) -> int:
        """Get total user count."""
        pass
    
    @abstractmethod
    async def get_inactive_users(self, days: int) -> List[User]:
        """Get users inactive for specified days."""
        pass