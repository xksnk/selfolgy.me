from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from aiogram.types import User as TelegramUser
from datetime import datetime

from ..models import User, ChatMessage, PersonalityVector, Questionnaire


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_or_create_user(self, telegram_user: TelegramUser) -> User:
        """Get existing user or create new one from Telegram user object"""
        
        # Try to get existing user
        stmt = select(User).where(User.telegram_id == str(telegram_user.id))
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user:
            # Update last active timestamp
            user.last_active = datetime.utcnow()
            await self.session.commit()
            return user
        
        # Create new user
        user = User(
            telegram_id=str(telegram_user.id),
            username=telegram_user.username,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name,
            last_active=datetime.utcnow()
        )
        
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        
        return user
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID"""
        
        stmt = select(User).where(User.telegram_id == str(telegram_id))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def update_user_consent(self, telegram_id: int, gdpr_consent: bool):
        """Update user GDPR consent"""
        
        stmt = (
            update(User)
            .where(User.telegram_id == str(telegram_id))
            .values(gdpr_consent=gdpr_consent)
        )
        await self.session.execute(stmt)
        await self.session.commit()
    
    async def update_onboarding_status(self, telegram_id: int, completed: bool = True):
        """Mark user onboarding as completed"""
        
        stmt = (
            update(User)
            .where(User.telegram_id == str(telegram_id))
            .values(onboarding_completed=completed)
        )
        await self.session.execute(stmt)
        await self.session.commit()
    
    async def update_user_state(self, telegram_id: int, state: str):
        """Update user's current state"""
        
        stmt = (
            update(User)
            .where(User.telegram_id == str(telegram_id))
            .values(current_state=state)
        )
        await self.session.execute(stmt)
        await self.session.commit()
    
    async def update_user_tier(self, telegram_id: int, tier: str):
        """Update user tier (free, premium, professional)"""
        
        stmt = (
            update(User)
            .where(User.telegram_id == str(telegram_id))
            .values(tier=tier)
        )
        await self.session.execute(stmt)
        await self.session.commit()
    
    async def save_chat_message(
        self, 
        telegram_id: int, 
        content: str, 
        message_type: str = "user",
        ai_model_used: Optional[str] = None,
        insights: Optional[dict] = None
    ) -> ChatMessage:
        """Save chat message to history"""
        
        message = ChatMessage(
            user_id=str(telegram_id),
            content=content,
            message_type=message_type,
            ai_model_used=ai_model_used,
            insights=insights
        )
        
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        
        return message
    
    async def get_recent_chat_history(
        self, 
        telegram_id: int, 
        limit: int = 10
    ) -> list[ChatMessage]:
        """Get recent chat history for context"""
        
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.user_id == str(telegram_id))
            .order_by(ChatMessage.timestamp.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        messages = result.scalars().all()
        
        return list(reversed(messages))  # Return in chronological order
    
    async def save_questionnaire_response(
        self,
        telegram_id: int,
        questionnaire_type: str,
        responses: dict,
        vector_id: Optional[str] = None
    ) -> Questionnaire:
        """Save questionnaire responses"""
        
        questionnaire = Questionnaire(
            user_id=str(telegram_id),
            questionnaire_type=questionnaire_type,
            responses=responses,
            vector_id=vector_id
        )
        
        self.session.add(questionnaire)
        await self.session.commit()
        await self.session.refresh(questionnaire)
        
        return questionnaire
    
    async def save_personality_vector(
        self,
        telegram_id: int,
        traits: dict,
        confidence_score: Optional[str] = None,
        qdrant_point_id: Optional[str] = None,
        source_data: Optional[str] = None
    ) -> PersonalityVector:
        """Save personality vector data"""
        
        # Get current version number
        stmt = (
            select(PersonalityVector)
            .where(PersonalityVector.user_id == str(telegram_id))
            .order_by(PersonalityVector.vector_version.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        latest_vector = result.scalar_one_or_none()
        
        version = (latest_vector.vector_version + 1) if latest_vector else 1
        
        vector = PersonalityVector(
            user_id=str(telegram_id),
            vector_version=version,
            traits=traits,
            confidence_score=confidence_score,
            qdrant_point_id=qdrant_point_id,
            source_data=source_data
        )
        
        self.session.add(vector)
        await self.session.commit()
        await self.session.refresh(vector)
        
        return vector
    
    async def get_latest_personality_vector(
        self, 
        telegram_id: int
    ) -> Optional[PersonalityVector]:
        """Get user's latest personality vector"""
        
        stmt = (
            select(PersonalityVector)
            .where(PersonalityVector.user_id == str(telegram_id))
            .order_by(PersonalityVector.vector_version.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()