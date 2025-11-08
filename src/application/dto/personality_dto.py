"""Personality DTOs for application layer."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional
from uuid import UUID


@dataclass
class PersonalityTraitDTO:
    """DTO for personality trait."""
    
    trait: str
    score: float
    confidence: float
    percentage: int
    updated_at: datetime
    source: str


@dataclass
class PersonalityProfileDTO:
    """DTO for personality profile response."""
    
    id: UUID
    telegram_id: int
    version: int
    traits: Dict[str, PersonalityTraitDTO] = field(default_factory=dict)
    overall_confidence: float = 0.0
    is_complete: bool = False
    is_high_confidence: bool = False
    dominant_traits: list[str] = field(default_factory=list)
    qdrant_point_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)