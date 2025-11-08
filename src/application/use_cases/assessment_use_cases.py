"""Assessment-related use cases."""

from uuid import uuid4
from typing import Optional

from ...domain.entities import AssessmentResponse, AssessmentType
from ...domain.repositories import IAssessmentRepository, IUserRepository
from ...domain.services import PersonalityAnalysisService
from ...domain.value_objects import TelegramId
from ..dto import CreateAssessmentDTO, SubmitAnswerDTO, AssessmentResponseDTO
from ..interfaces import IAIService, IVectorService


class CreateAssessmentUseCase:
    """Use case for creating a new assessment."""
    
    def __init__(
        self,
        assessment_repository: IAssessmentRepository,
        user_repository: IUserRepository
    ):
        self.assessment_repository = assessment_repository
        self.user_repository = user_repository
    
    async def execute(self, dto: CreateAssessmentDTO) -> AssessmentResponseDTO:
        """Create a new assessment."""
        
        telegram_id = TelegramId(dto.telegram_id)
        
        # Verify user exists
        user = await self.user_repository.get_by_telegram_id(telegram_id)
        if not user:
            raise ValueError("User not found")
        
        # Create assessment
        assessment = AssessmentResponse.create_new(
            user_id=telegram_id,
            assessment_type=AssessmentType(dto.assessment_type)
        )
        
        # Save assessment
        created_assessment = await self.assessment_repository.create(assessment)
        
        return self._to_response_dto(created_assessment)
    
    def _to_response_dto(self, assessment: AssessmentResponse) -> AssessmentResponseDTO:
        """Convert assessment entity to DTO."""
        answers_dict = {
            qid: {
                "value": answer.value,
                "confidence": answer.confidence,
                "answered_at": answer.answered_at
            }
            for qid, answer in assessment.answers.items()
        }
        
        return AssessmentResponseDTO(
            id=assessment.id,
            telegram_id=assessment.user_id.value,
            assessment_type=assessment.assessment_type.value,
            answers=answers_dict,
            completed_at=assessment.completed_at,
            completion_percentage=assessment.completion_percentage,
            vector_id=assessment.vector_id,
            insights_generated=assessment.insights_generated,
            metadata=assessment.metadata,
            created_at=assessment.created_at
        )


class SubmitAssessmentAnswerUseCase:
    """Use case for submitting assessment answers."""
    
    def __init__(self, assessment_repository: IAssessmentRepository):
        self.assessment_repository = assessment_repository
    
    async def execute(self, dto: SubmitAnswerDTO) -> AssessmentResponseDTO:
        """Submit answer to assessment."""
        
        # Get assessment
        assessment = await self.assessment_repository.get_by_id(dto.assessment_id)
        if not assessment:
            raise ValueError("Assessment not found")
        
        if assessment.is_completed:
            raise ValueError("Assessment is already completed")
        
        # Add answer
        assessment.add_answer(
            question_id=dto.question_id,
            value=dto.value,
            confidence=dto.confidence
        )
        
        # Update assessment
        updated_assessment = await self.assessment_repository.update(assessment)
        
        return self._to_response_dto(updated_assessment)
    
    def _to_response_dto(self, assessment: AssessmentResponse) -> AssessmentResponseDTO:
        """Convert assessment entity to DTO."""
        answers_dict = {
            qid: {
                "value": answer.value,
                "confidence": answer.confidence,
                "answered_at": answer.answered_at
            }
            for qid, answer in assessment.answers.items()
        }
        
        return AssessmentResponseDTO(
            id=assessment.id,
            telegram_id=assessment.user_id.value,
            assessment_type=assessment.assessment_type.value,
            answers=answers_dict,
            completed_at=assessment.completed_at,
            completion_percentage=assessment.completion_percentage,
            vector_id=assessment.vector_id,
            insights_generated=assessment.insights_generated,
            metadata=assessment.metadata,
            created_at=assessment.created_at
        )


class CompleteAssessmentUseCase:
    """Use case for completing an assessment and generating insights."""
    
    def __init__(
        self,
        assessment_repository: IAssessmentRepository,
        personality_analysis_service: PersonalityAnalysisService,
        ai_service: IAIService,
        vector_service: IVectorService
    ):
        self.assessment_repository = assessment_repository
        self.personality_analysis_service = personality_analysis_service
        self.ai_service = ai_service
        self.vector_service = vector_service
    
    async def execute(self, assessment_id: uuid4) -> AssessmentResponseDTO:
        """Complete assessment and generate personality insights."""
        
        # Get assessment
        assessment = await self.assessment_repository.get_by_id(assessment_id)
        if not assessment:
            raise ValueError("Assessment not found")
        
        if assessment.is_completed:
            raise ValueError("Assessment is already completed")
        
        # Mark as completed
        assessment.complete()
        
        # Generate personality profile from assessment
        personality_profile = self.personality_analysis_service.analyze_assessment_responses(
            assessment=assessment
        )
        
        # Store personality vector
        vector_data = personality_profile.to_vector_dict()
        vector_id = await self.vector_service.store_personality_vector(
            user_id=assessment.user_id.value,
            vector_data=vector_data,
            metadata={
                "assessment_id": str(assessment.id),
                "assessment_type": assessment.assessment_type.value,
                "confidence": personality_profile.overall_confidence
            }
        )
        
        # Mark insights as generated
        assessment.mark_insights_generated(vector_id=vector_id)
        
        # Generate AI insights
        insights = await self.ai_service.generate_insights(
            user_data={
                "personality_profile": personality_profile.to_vector_dict(),
                "assessment_answers": assessment.get_scale_answers(),
                "assessment_type": assessment.assessment_type.value
            }
        )
        
        # Add insights to metadata
        assessment.add_metadata("ai_insights", insights)
        
        # Update assessment
        updated_assessment = await self.assessment_repository.update(assessment)
        
        return self._to_response_dto(updated_assessment)
    
    def _to_response_dto(self, assessment: AssessmentResponse) -> AssessmentResponseDTO:
        """Convert assessment entity to DTO."""
        answers_dict = {
            qid: {
                "value": answer.value,
                "confidence": answer.confidence,
                "answered_at": answer.answered_at
            }
            for qid, answer in assessment.answers.items()
        }
        
        return AssessmentResponseDTO(
            id=assessment.id,
            telegram_id=assessment.user_id.value,
            assessment_type=assessment.assessment_type.value,
            answers=answers_dict,
            completed_at=assessment.completed_at,
            completion_percentage=assessment.completion_percentage,
            vector_id=assessment.vector_id,
            insights_generated=assessment.insights_generated,
            metadata=assessment.metadata,
            created_at=assessment.created_at
        )