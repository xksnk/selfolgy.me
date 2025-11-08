"""User domain entity."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from ..value_objects import TelegramId, Username


class UserTier(Enum):
    """User subscription tier."""
    FREE = "free"
    PREMIUM = "premium"
    PROFESSIONAL = "professional"


class PrivacyLevel(Enum):
    """Privacy level for data processing."""
    MINIMAL = "minimal"
    BALANCED = "balanced" 
    FULL = "full"


@dataclass
class User:
    """User domain entity representing a Selfology bot user."""
    
    id: UUID
    telegram_id: TelegramId
    username: Optional[Username]
    first_name: Optional[str]
    last_name: Optional[str]
    tier: UserTier
    privacy_level: PrivacyLevel
    gdpr_consent: bool
    onboarding_completed: bool
    current_state: Optional[str]
    created_at: datetime
    updated_at: datetime
    last_active: Optional[datetime]
    
    @property
    def display_name(self) -> str:
        """Get user's display name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.username:
            return f"@{self.username.value}"
        else:
            return f"User {self.telegram_id.value}"
    
    @property
    def is_premium(self) -> bool:
        """Check if user has premium features."""
        return self.tier in [UserTier.PREMIUM, UserTier.PROFESSIONAL]
    
    @property
    def is_professional(self) -> bool:
        """Check if user has professional tier."""
        return self.tier == UserTier.PROFESSIONAL
    
    def can_access_advanced_ai(self) -> bool:
        """Check if user can access advanced AI models."""
        return self.is_premium
    
    def can_export_data(self) -> bool:
        """Check if user can export their data."""
        return self.gdpr_consent
    
    def update_last_active(self) -> None:
        """Update last active timestamp."""
        self.last_active = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def complete_onboarding(self) -> None:
        """Mark onboarding as completed."""
        self.onboarding_completed = True
        self.updated_at = datetime.utcnow()
    
    def upgrade_tier(self, new_tier: UserTier) -> None:
        """Upgrade user tier."""
        if new_tier.value > self.tier.value:
            self.tier = new_tier
            self.updated_at = datetime.utcnow()
    
    def update_privacy_settings(self, privacy_level: PrivacyLevel) -> None:
        """Update privacy level."""
        self.privacy_level = privacy_level
        self.updated_at = datetime.utcnow()
    
    def revoke_consent(self) -> None:
        """Revoke GDPR consent."""
        self.gdpr_consent = False
        self.updated_at = datetime.utcnow()