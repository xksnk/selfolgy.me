"""Personality domain entity."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional
from uuid import UUID

from ..value_objects import BigFiveTrait, PersonalityScore, TelegramId


@dataclass
class PersonalityTrait:
    """Individual personality trait."""
    
    trait: BigFiveTrait
    score: PersonalityScore
    updated_at: datetime
    source: str  # e.g., "questionnaire", "chat_analysis", "manual"
    
    def update_score(self, new_score: PersonalityScore, source: str) -> None:
        """Update trait score."""
        self.score = new_score
        self.updated_at = datetime.utcnow()
        self.source = source


@dataclass
class PersonalityProfile:
    """Complete personality profile for a user."""
    
    id: UUID
    user_id: TelegramId
    version: int
    traits: Dict[BigFiveTrait, PersonalityTrait] = field(default_factory=dict)
    overall_confidence: float = 0.0
    qdrant_point_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self) -> None:
        """Validate personality profile."""
        if not (0.0 <= self.overall_confidence <= 1.0):
            raise ValueError("Overall confidence must be between 0.0 and 1.0")
    
    def add_trait(self, trait: PersonalityTrait) -> None:
        """Add or update a personality trait."""
        self.traits[trait.trait] = trait
        self.updated_at = datetime.utcnow()
        self._recalculate_confidence()
    
    def get_trait_score(self, trait: BigFiveTrait) -> Optional[PersonalityScore]:
        """Get score for a specific trait."""
        trait_obj = self.traits.get(trait)
        return trait_obj.score if trait_obj else None
    
    def is_complete(self) -> bool:
        """Check if all Big Five traits are present."""
        return len(self.traits) == len(BigFiveTrait)
    
    def is_high_confidence(self) -> bool:
        """Check if overall confidence is high."""
        return self.overall_confidence > 0.7
    
    def get_dominant_traits(self, threshold: float = 0.7) -> list[BigFiveTrait]:
        """Get traits with high scores."""
        dominant = []
        for trait_type, trait in self.traits.items():
            if trait.score.value >= threshold:
                dominant.append(trait_type)
        return dominant
    
    def to_vector_dict(self) -> Dict[str, float]:
        """Convert to dictionary for vector storage."""
        return {
            trait.value: self.traits[trait].score.value 
            for trait in BigFiveTrait
            if trait in self.traits
        }
    
    def _recalculate_confidence(self) -> None:
        """Recalculate overall confidence based on individual traits."""
        if not self.traits:
            self.overall_confidence = 0.0
            return
        
        total_confidence = sum(trait.score.confidence for trait in self.traits.values())
        self.overall_confidence = total_confidence / len(self.traits)
    
    @classmethod
    def create_empty(cls, user_id: TelegramId, version: int = 1) -> "PersonalityProfile":
        """Create empty personality profile."""
        return cls(
            id=UUID(),
            user_id=user_id,
            version=version
        )