"""Personality repository interface."""

from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID

from ..entities import PersonalityProfile
from ..value_objects import TelegramId


class IPersonalityRepository(ABC):
    """Personality repository interface."""
    
    @abstractmethod
    async def create(self, profile: PersonalityProfile) -> PersonalityProfile:
        """Create a new personality profile."""
        pass
    
    @abstractmethod
    async def get_by_id(self, profile_id: UUID) -> Optional[PersonalityProfile]:
        """Get personality profile by ID.""" 
        pass
    
    @abstractmethod
    async def get_latest_by_user(self, user_id: TelegramId) -> Optional[PersonalityProfile]:
        """Get latest personality profile for user."""
        pass
    
    @abstractmethod
    async def get_all_by_user(self, user_id: TelegramId) -> List[PersonalityProfile]:
        """Get all personality profiles for user."""
        pass
    
    @abstractmethod
    async def update(self, profile: PersonalityProfile) -> PersonalityProfile:
        """Update personality profile."""
        pass
    
    @abstractmethod
    async def delete(self, profile_id: UUID) -> bool:
        """Delete personality profile."""
        pass
    
    @abstractmethod
    async def find_similar_profiles(
        self, 
        profile: PersonalityProfile, 
        threshold: float = 0.8,
        limit: int = 10
    ) -> List[PersonalityProfile]:
        """Find similar personality profiles."""
        pass