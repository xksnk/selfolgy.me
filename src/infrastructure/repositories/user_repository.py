"""SQL User repository implementation."""

from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from ...domain.entities import User, UserTier, PrivacyLevel
from ...domain.repositories import IUserRepository
from ...domain.value_objects import TelegramId, Username
from ..database.models import UserModel


class SQLUserRepository(IUserRepository):
    """SQL implementation of user repository."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, user: User) -> User:
        """Create a new user."""
        
        model = UserModel(
            id=user.id,
            telegram_id=str(user.telegram_id.value),
            username=user.username.value if user.username else None,
            first_name=user.first_name,
            last_name=user.last_name,
            tier=user.tier.value,
            privacy_level=user.privacy_level.value,
            gdpr_consent=user.gdpr_consent,
            onboarding_completed=user.onboarding_completed,
            current_state=user.current_state,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_active=user.last_active
        )
        
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        
        return self._to_entity(model)
    
    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        
        return self._to_entity(model) if model else None
    
    async def get_by_telegram_id(self, telegram_id: TelegramId) -> Optional[User]:
        """Get user by Telegram ID."""
        
        stmt = select(UserModel).where(UserModel.telegram_id == str(telegram_id.value))
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        
        return self._to_entity(model) if model else None
    
    async def update(self, user: User) -> User:
        """Update user."""
        
        stmt = (
            update(UserModel)
            .where(UserModel.id == user.id)
            .values(
                username=user.username.value if user.username else None,
                first_name=user.first_name,
                last_name=user.last_name,
                tier=user.tier.value,
                privacy_level=user.privacy_level.value,
                gdpr_consent=user.gdpr_consent,
                onboarding_completed=user.onboarding_completed,
                current_state=user.current_state,
                updated_at=user.updated_at,
                last_active=user.last_active
            )
        )
        
        await self.session.execute(stmt)
        await self.session.commit()
        
        # Return updated entity
        return await self.get_by_id(user.id)
    
    async def delete(self, user_id: UUID) -> bool:
        """Delete user."""
        
        stmt = delete(UserModel).where(UserModel.id == user_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        
        return result.rowcount > 0
    
    async def get_all_by_tier(self, tier: str) -> List[User]:
        """Get all users by tier."""
        
        stmt = select(UserModel).where(UserModel.tier == tier)
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        
        return [self._to_entity(model) for model in models]
    
    async def count_total_users(self) -> int:
        """Get total user count."""
        
        stmt = select(func.count(UserModel.id))
        result = await self.session.execute(stmt)
        return result.scalar()
    
    async def get_inactive_users(self, days: int) -> List[User]:
        """Get users inactive for specified days."""
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        stmt = select(UserModel).where(
            (UserModel.last_active < cutoff_date) | 
            (UserModel.last_active.is_(None))
        )
        
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        
        return [self._to_entity(model) for model in models]
    
    def _to_entity(self, model: UserModel) -> User:
        """Convert database model to domain entity."""
        
        username = Username(model.username) if model.username else None
        
        return User(
            id=model.id,
            telegram_id=TelegramId(int(model.telegram_id)),
            username=username,
            first_name=model.first_name,
            last_name=model.last_name,
            tier=UserTier(model.tier),
            privacy_level=PrivacyLevel(model.privacy_level),
            gdpr_consent=model.gdpr_consent,
            onboarding_completed=model.onboarding_completed,
            current_state=model.current_state,
            created_at=model.created_at,
            updated_at=model.updated_at,
            last_active=model.last_active
        )