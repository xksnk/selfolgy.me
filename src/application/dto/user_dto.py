"""User DTOs for application layer."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class CreateUserDTO:
    """DTO for creating a new user."""
    
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


@dataclass
class UpdateUserDTO:
    """DTO for updating user information."""
    
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    tier: Optional[str] = None
    privacy_level: Optional[str] = None
    gdpr_consent: Optional[bool] = None
    onboarding_completed: Optional[bool] = None


@dataclass
class UserResponseDTO:
    """DTO for user response data."""
    
    id: UUID
    telegram_id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    display_name: str
    tier: str
    privacy_level: str
    gdpr_consent: bool
    onboarding_completed: bool
    is_premium: bool
    is_professional: bool
    created_at: datetime
    updated_at: datetime
    last_active: Optional[datetime]