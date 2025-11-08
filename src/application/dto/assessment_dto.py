"""Assessment DTOs for application layer."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID


@dataclass
class CreateAssessmentDTO:
    """DTO for creating a new assessment."""
    
    telegram_id: int
    assessment_type: str


@dataclass
class SubmitAnswerDTO:
    """DTO for submitting assessment answers."""
    
    assessment_id: UUID
    question_id: str
    value: Any
    confidence: Optional[float] = None


@dataclass
class AssessmentResponseDTO:
    """DTO for assessment response."""
    
    id: UUID
    telegram_id: int
    assessment_type: str
    answers: Dict[str, Any] = field(default_factory=dict)
    completed_at: Optional[datetime] = None
    completion_percentage: float = 0.0
    vector_id: Optional[str] = None
    insights_generated: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)