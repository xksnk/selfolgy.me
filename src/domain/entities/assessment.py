"""Assessment domain entity."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional
from uuid import UUID

from ..value_objects import TelegramId


class AssessmentType(Enum):
    """Types of assessments."""
    PERSONALITY = "personality"
    VALUES = "values"
    GOALS = "goals"
    ONBOARDING = "onboarding"
    WELLBEING = "wellbeing"


@dataclass
class AssessmentQuestion:
    """Single assessment question."""
    
    id: str
    question: str
    question_type: str  # "scale", "multiple_choice", "text", "yes_no"
    options: Optional[List[str]] = None
    scale_min: Optional[int] = None
    scale_max: Optional[int] = None
    required: bool = True


@dataclass
class AssessmentAnswer:
    """Single assessment answer."""
    
    question_id: str
    value: Any
    confidence: Optional[float] = None
    answered_at: datetime = field(default_factory=datetime.utcnow)
    
    def is_scale_answer(self) -> bool:
        """Check if answer is numeric scale."""
        return isinstance(self.value, (int, float))
    
    def is_text_answer(self) -> bool:
        """Check if answer is text."""
        return isinstance(self.value, str)


@dataclass
class AssessmentResponse:
    """Complete assessment response entity."""
    
    id: UUID
    user_id: TelegramId
    assessment_type: AssessmentType
    answers: Dict[str, AssessmentAnswer] = field(default_factory=dict)
    completed_at: Optional[datetime] = None
    vector_id: Optional[str] = None
    insights_generated: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def is_completed(self) -> bool:
        """Check if assessment is completed."""
        return self.completed_at is not None
    
    @property
    def completion_percentage(self) -> float:
        """Get completion percentage."""
        if not self.answers:
            return 0.0
        
        # This would need to be calculated based on total questions
        # For now, we'll assume completion if any answers exist
        return 1.0 if self.answers else 0.0
    
    def add_answer(self, question_id: str, value: Any, confidence: Optional[float] = None) -> None:
        """Add answer to assessment."""
        answer = AssessmentAnswer(
            question_id=question_id,
            value=value,
            confidence=confidence
        )
        self.answers[question_id] = answer
    
    def get_answer(self, question_id: str) -> Optional[AssessmentAnswer]:
        """Get specific answer."""
        return self.answers.get(question_id)
    
    def get_scale_answers(self) -> Dict[str, int]:
        """Get all scale-based answers."""
        return {
            qid: answer.value 
            for qid, answer in self.answers.items()
            if answer.is_scale_answer()
        }
    
    def get_text_answers(self) -> Dict[str, str]:
        """Get all text answers."""
        return {
            qid: answer.value
            for qid, answer in self.answers.items() 
            if answer.is_text_answer()
        }
    
    def complete(self) -> None:
        """Mark assessment as completed."""
        self.completed_at = datetime.utcnow()
    
    def mark_insights_generated(self, vector_id: Optional[str] = None) -> None:
        """Mark that insights have been generated."""
        self.insights_generated = True
        if vector_id:
            self.vector_id = vector_id
    
    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata."""
        self.metadata[key] = value
    
    @classmethod
    def create_new(
        cls,
        user_id: TelegramId,
        assessment_type: AssessmentType
    ) -> "AssessmentResponse":
        """Create new assessment response."""
        return cls(
            id=UUID(),
            user_id=user_id,
            assessment_type=assessment_type
        )