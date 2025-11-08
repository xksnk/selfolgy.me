"""User-related use cases."""

from uuid import uuid4
from datetime import datetime
from typing import Optional

from ...domain.entities import User, UserTier, PrivacyLevel
from ...domain.repositories import IUserRepository
from ...domain.value_objects import TelegramId, Username
from ...domain.services import UserTierService
from ..dto import CreateUserDTO, UpdateUserDTO, UserResponseDTO
from ..interfaces import INotificationService


class CreateUserUseCase:
    """Use case for creating a new user."""
    
    def __init__(
        self,
        user_repository: IUserRepository,
        notification_service: INotificationService
    ):
        self.user_repository = user_repository
        self.notification_service = notification_service
    
    async def execute(self, dto: CreateUserDTO) -> UserResponseDTO:
        """Create a new user."""
        
        telegram_id = TelegramId(dto.telegram_id)
        
        # Check if user already exists
        existing_user = await self.user_repository.get_by_telegram_id(telegram_id)
        if existing_user:
            return self._to_response_dto(existing_user)
        
        # Create username value object if provided
        username = Username(dto.username) if dto.username else None
        
        # Create new user entity
        user = User(
            id=uuid4(),
            telegram_id=telegram_id,
            username=username,
            first_name=dto.first_name,
            last_name=dto.last_name,
            tier=UserTier.FREE,
            privacy_level=PrivacyLevel.BALANCED,
            gdpr_consent=False,
            onboarding_completed=False,
            current_state=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            last_active=datetime.utcnow()
        )
        
        # Save user
        created_user = await self.user_repository.create(user)
        
        # Send welcome notification
        await self.notification_service.send_welcome_message(
            telegram_id=dto.telegram_id,
            user_name=created_user.display_name
        )
        
        return self._to_response_dto(created_user)
    
    def _to_response_dto(self, user: User) -> UserResponseDTO:
        """Convert user entity to response DTO."""
        return UserResponseDTO(
            id=user.id,
            telegram_id=user.telegram_id.value,
            username=user.username.value if user.username else None,
            first_name=user.first_name,
            last_name=user.last_name,
            display_name=user.display_name,
            tier=user.tier.value,
            privacy_level=user.privacy_level.value,
            gdpr_consent=user.gdpr_consent,
            onboarding_completed=user.onboarding_completed,
            is_premium=user.is_premium,
            is_professional=user.is_professional,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_active=user.last_active
        )


class GetUserUseCase:
    """Use case for getting user information."""
    
    def __init__(self, user_repository: IUserRepository):
        self.user_repository = user_repository
    
    async def execute(self, telegram_id: int) -> Optional[UserResponseDTO]:
        """Get user by Telegram ID."""
        
        user = await self.user_repository.get_by_telegram_id(TelegramId(telegram_id))
        
        if not user:
            return None
        
        # Update last active
        user.update_last_active()
        await self.user_repository.update(user)
        
        return self._to_response_dto(user)
    
    def _to_response_dto(self, user: User) -> UserResponseDTO:
        """Convert user entity to response DTO."""
        return UserResponseDTO(
            id=user.id,
            telegram_id=user.telegram_id.value,
            username=user.username.value if user.username else None,
            first_name=user.first_name,
            last_name=user.last_name,
            display_name=user.display_name,
            tier=user.tier.value,
            privacy_level=user.privacy_level.value,
            gdpr_consent=user.gdpr_consent,
            onboarding_completed=user.onboarding_completed,
            is_premium=user.is_premium,
            is_professional=user.is_professional,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_active=user.last_active
        )


class UpdateUserUseCase:
    """Use case for updating user information."""
    
    def __init__(
        self,
        user_repository: IUserRepository,
        user_tier_service: UserTierService
    ):
        self.user_repository = user_repository
        self.user_tier_service = user_tier_service
    
    async def execute(self, telegram_id: int, dto: UpdateUserDTO) -> Optional[UserResponseDTO]:
        """Update user information."""
        
        user = await self.user_repository.get_by_telegram_id(TelegramId(telegram_id))
        if not user:
            return None
        
        # Update fields if provided
        if dto.username is not None:
            user.username = Username(dto.username) if dto.username else None
        
        if dto.first_name is not None:
            user.first_name = dto.first_name
        
        if dto.last_name is not None:
            user.last_name = dto.last_name
        
        if dto.tier is not None:
            new_tier = UserTier(dto.tier)
            user.upgrade_tier(new_tier)
        
        if dto.privacy_level is not None:
            privacy_level = PrivacyLevel(dto.privacy_level)
            user.update_privacy_settings(privacy_level)
        
        if dto.gdpr_consent is not None:
            if dto.gdpr_consent:
                user.gdpr_consent = True
            else:
                user.revoke_consent()
        
        if dto.onboarding_completed is not None and dto.onboarding_completed:
            user.complete_onboarding()
        
        # Save updated user
        updated_user = await self.user_repository.update(user)
        
        return self._to_response_dto(updated_user)
    
    def _to_response_dto(self, user: User) -> UserResponseDTO:
        """Convert user entity to response DTO."""
        return UserResponseDTO(
            id=user.id,
            telegram_id=user.telegram_id.value,
            username=user.username.value if user.username else None,
            first_name=user.first_name,
            last_name=user.last_name,
            display_name=user.display_name,
            tier=user.tier.value,
            privacy_level=user.privacy_level.value,
            gdpr_consent=user.gdpr_consent,
            onboarding_completed=user.onboarding_completed,
            is_premium=user.is_premium,
            is_professional=user.is_professional,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_active=user.last_active
        )