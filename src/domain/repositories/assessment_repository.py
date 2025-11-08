"""Assessment repository interface."""

from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID

from ..entities import AssessmentResponse, AssessmentType
from ..value_objects import TelegramId


class IAssessmentRepository(ABC):
    """Assessment repository interface."""
    
    @abstractmethod
    async def create(self, assessment: AssessmentResponse) -> AssessmentResponse:
        """Create a new assessment response."""
        pass
    
    @abstractmethod
    async def get_by_id(self, assessment_id: UUID) -> Optional[AssessmentResponse]:
        """Get assessment by ID."""
        pass
    
    @abstractmethod
    async def get_by_user_and_type(
        self,
        user_id: TelegramId,
        assessment_type: AssessmentType
    ) -> List[AssessmentResponse]:
        """Get assessments by user and type."""
        pass
    
    @abstractmethod
    async def get_latest_by_user_and_type(
        self,
        user_id: TelegramId,
        assessment_type: AssessmentType
    ) -> Optional[AssessmentResponse]:
        """Get latest assessment by user and type."""
        pass
    
    @abstractmethod
    async def update(self, assessment: AssessmentResponse) -> AssessmentResponse:
        """Update assessment response."""
        pass
    
    @abstractmethod
    async def delete(self, assessment_id: UUID) -> bool:
        """Delete assessment response."""
        pass
    
    @abstractmethod
    async def get_completed_assessments(
        self,
        user_id: TelegramId
    ) -> List[AssessmentResponse]:
        """Get all completed assessments for user."""
        pass