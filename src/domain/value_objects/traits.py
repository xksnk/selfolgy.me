"""Personality traits value objects."""

from dataclasses import dataclass
from enum import Enum
from typing import Union


class BigFiveTrait(Enum):
    """Big Five personality traits."""
    OPENNESS = "openness"
    CONSCIENTIOUSNESS = "conscientiousness"
    EXTRAVERSION = "extraversion"
    AGREEABLENESS = "agreeableness" 
    NEUROTICISM = "neuroticism"


@dataclass(frozen=True)
class PersonalityScore:
    """Value object for personality trait scores."""
    
    value: float
    confidence: float
    
    def __post_init__(self) -> None:
        """Validate personality score."""
        if not (0.0 <= self.value <= 1.0):
            raise ValueError("Personality score must be between 0.0 and 1.0")
        
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("Confidence score must be between 0.0 and 1.0")
    
    @property
    def is_high_confidence(self) -> bool:
        """Check if confidence is high (>0.7)."""
        return self.confidence > 0.7
    
    @property
    def percentage(self) -> int:
        """Get score as percentage."""
        return int(self.value * 100)
    
    @classmethod
    def from_percentage(cls, percentage: Union[int, float], confidence: float = 1.0) -> "PersonalityScore":
        """Create PersonalityScore from percentage."""
        if not (0 <= percentage <= 100):
            raise ValueError("Percentage must be between 0 and 100")
        
        return cls(value=percentage / 100.0, confidence=confidence)
    
    def __str__(self) -> str:
        """String representation."""
        return f"{self.percentage}% (confidence: {int(self.confidence * 100)}%)"