"""Personality-related use cases."""

from typing import Optional, List

from ...domain.entities import PersonalityProfile, ChatMessage
from ...domain.repositories import IPersonalityRepository, IChatRepository
from ...domain.services import PersonalityAnalysisService
from ...domain.value_objects import TelegramId
from ..dto import PersonalityProfileDTO, PersonalityTraitDTO
from ..interfaces import IVectorService


class GetPersonalityProfileUseCase:
    """Use case for getting user's personality profile."""
    
    def __init__(self, personality_repository: IPersonalityRepository):
        self.personality_repository = personality_repository
    
    async def execute(self, telegram_id: int) -> Optional[PersonalityProfileDTO]:
        """Get latest personality profile for user."""
        
        profile = await self.personality_repository.get_latest_by_user(
            user_id=TelegramId(telegram_id)
        )
        
        if not profile:
            return None
        
        return self._to_profile_dto(profile)
    
    def _to_profile_dto(self, profile: PersonalityProfile) -> PersonalityProfileDTO:
        """Convert profile entity to DTO."""
        traits_dto = {}
        
        for trait_type, trait in profile.traits.items():
            traits_dto[trait_type.value] = PersonalityTraitDTO(
                trait=trait_type.value,
                score=trait.score.value,
                confidence=trait.score.confidence,
                percentage=trait.score.percentage,
                updated_at=trait.updated_at,
                source=trait.source
            )
        
        return PersonalityProfileDTO(
            id=profile.id,
            telegram_id=profile.user_id.value,
            version=profile.version,
            traits=traits_dto,
            overall_confidence=profile.overall_confidence,
            is_complete=profile.is_complete(),
            is_high_confidence=profile.is_high_confidence(),
            dominant_traits=[trait.value for trait in profile.get_dominant_traits()],
            qdrant_point_id=profile.qdrant_point_id,
            created_at=profile.created_at,
            updated_at=profile.updated_at
        )


class AnalyzePersonalityUseCase:
    """Use case for analyzing personality from chat patterns."""
    
    def __init__(
        self,
        personality_repository: IPersonalityRepository,
        chat_repository: IChatRepository,
        personality_analysis_service: PersonalityAnalysisService,
        vector_service: IVectorService
    ):
        self.personality_repository = personality_repository
        self.chat_repository = chat_repository
        self.personality_analysis_service = personality_analysis_service
        self.vector_service = vector_service
    
    async def execute(self, telegram_id: int, message_limit: int = 50) -> Optional[PersonalityProfileDTO]:
        """Analyze personality from recent chat messages."""
        
        telegram_id_vo = TelegramId(telegram_id)
        
        # Get recent chat messages
        messages = await self.chat_repository.get_recent_messages(
            user_id=telegram_id_vo,
            limit=message_limit
        )
        
        if not messages:
            return None
        
        # Get existing personality profile
        existing_profile = await self.personality_repository.get_latest_by_user(
            user_id=telegram_id_vo
        )
        
        # Analyze chat patterns
        updated_profile = self.personality_analysis_service.analyze_chat_patterns(
            messages=messages,
            existing_profile=existing_profile
        )
        
        if not updated_profile:
            return None
        
        # Save or update personality profile
        if existing_profile:
            saved_profile = await self.personality_repository.update(updated_profile)
        else:
            saved_profile = await self.personality_repository.create(updated_profile)
        
        # Update vector storage
        if saved_profile.is_high_confidence():
            vector_data = saved_profile.to_vector_dict()
            
            if saved_profile.qdrant_point_id:
                # Update existing vector
                await self.vector_service.update_personality_vector(
                    point_id=saved_profile.qdrant_point_id,
                    vector_data=vector_data,
                    metadata={
                        "user_id": telegram_id,
                        "version": saved_profile.version,
                        "confidence": saved_profile.overall_confidence,
                        "source": "chat_analysis"
                    }
                )
            else:
                # Create new vector
                vector_id = await self.vector_service.store_personality_vector(
                    user_id=telegram_id,
                    vector_data=vector_data,
                    metadata={
                        "user_id": telegram_id,
                        "version": saved_profile.version,
                        "confidence": saved_profile.overall_confidence,
                        "source": "chat_analysis"
                    }
                )
                saved_profile.qdrant_point_id = vector_id
                saved_profile = await self.personality_repository.update(saved_profile)
        
        return self._to_profile_dto(saved_profile)
    
    def _to_profile_dto(self, profile: PersonalityProfile) -> PersonalityProfileDTO:
        """Convert profile entity to DTO."""
        traits_dto = {}
        
        for trait_type, trait in profile.traits.items():
            traits_dto[trait_type.value] = PersonalityTraitDTO(
                trait=trait_type.value,
                score=trait.score.value,
                confidence=trait.score.confidence,
                percentage=trait.score.percentage,
                updated_at=trait.updated_at,
                source=trait.source
            )
        
        return PersonalityProfileDTO(
            id=profile.id,
            telegram_id=profile.user_id.value,
            version=profile.version,
            traits=traits_dto,
            overall_confidence=profile.overall_confidence,
            is_complete=profile.is_complete(),
            is_high_confidence=profile.is_high_confidence(),
            dominant_traits=[trait.value for trait in profile.get_dominant_traits()],
            qdrant_point_id=profile.qdrant_point_id,
            created_at=profile.created_at,
            updated_at=profile.updated_at
        )


class UpdatePersonalityProfileUseCase:
    """Use case for updating personality profile."""
    
    def __init__(
        self,
        personality_repository: IPersonalityRepository,
        vector_service: IVectorService
    ):
        self.personality_repository = personality_repository
        self.vector_service = vector_service
    
    async def execute(
        self,
        telegram_id: int,
        trait_updates: dict
    ) -> Optional[PersonalityProfileDTO]:
        """Update personality profile with new trait information."""
        
        telegram_id_vo = TelegramId(telegram_id)
        
        # Get existing profile
        profile = await self.personality_repository.get_latest_by_user(
            user_id=telegram_id_vo
        )
        
        if not profile:
            return None
        
        # Apply updates (this would need more sophisticated logic in practice)
        # For now, we'll just update the vector storage if high confidence
        
        if profile.is_high_confidence():
            vector_data = profile.to_vector_dict()
            
            if profile.qdrant_point_id:
                await self.vector_service.update_personality_vector(
                    point_id=profile.qdrant_point_id,
                    vector_data=vector_data,
                    metadata={
                        "user_id": telegram_id,
                        "version": profile.version,
                        "confidence": profile.overall_confidence,
                        "last_updated": profile.updated_at.isoformat()
                    }
                )
        
        return self._to_profile_dto(profile)
    
    def _to_profile_dto(self, profile: PersonalityProfile) -> PersonalityProfileDTO:
        """Convert profile entity to DTO."""
        traits_dto = {}
        
        for trait_type, trait in profile.traits.items():
            traits_dto[trait_type.value] = PersonalityTraitDTO(
                trait=trait_type.value,
                score=trait.score.value,
                confidence=trait.score.confidence,
                percentage=trait.score.percentage,
                updated_at=trait.updated_at,
                source=trait.source
            )
        
        return PersonalityProfileDTO(
            id=profile.id,
            telegram_id=profile.user_id.value,
            version=profile.version,
            traits=traits_dto,
            overall_confidence=profile.overall_confidence,
            is_complete=profile.is_complete(),
            is_high_confidence=profile.is_high_confidence(),
            dominant_traits=[trait.value for trait in profile.get_dominant_traits()],
            qdrant_point_id=profile.qdrant_point_id,
            created_at=profile.created_at,
            updated_at=profile.updated_at
        )