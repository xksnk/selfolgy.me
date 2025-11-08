"""
Unit tests for Soul Architect models
"""

import pytest
from datetime import datetime
from ..models import (
    TraitAssessment,
    BigFive,
    CoreDynamics,
    AdaptiveTraits,
    DomainAffinities,
    UniqueSignature,
    PersonalityProfile
)


class TestTraitAssessment:
    """Тесты для TraitAssessment"""

    def test_create_trait_assessment(self):
        """Тест создания TraitAssessment"""
        trait = TraitAssessment(
            value=0.75,
            confidence=0.85,
            variance=0.1,
            samples=5
        )

        assert trait.value == 0.75
        assert trait.confidence == 0.85
        assert trait.samples == 5
        assert trait.interpretation in ["high", "very_high"]
        assert trait.direction == "stable"

    def test_trait_display_formats(self):
        """Тест генерации форматов отображения"""
        trait = TraitAssessment(
            value=0.75,
            confidence=0.85,
            variance=0.1,
            samples=5
        )

        assert "percentage" in trait.display_formats
        assert "stars" in trait.display_formats
        assert "label" in trait.display_formats
        assert "color" in trait.display_formats

    def test_trait_interpretation_levels(self):
        """Тест интерпретации разных уровней"""
        very_low = TraitAssessment(value=0.1, confidence=0.5, samples=1)
        low = TraitAssessment(value=0.3, confidence=0.5, samples=1)
        medium = TraitAssessment(value=0.5, confidence=0.5, samples=1)
        high = TraitAssessment(value=0.7, confidence=0.5, samples=1)
        very_high = TraitAssessment(value=0.9, confidence=0.5, samples=1)

        assert very_low.interpretation == "very_low"
        assert low.interpretation == "low"
        assert medium.interpretation == "medium"
        assert high.interpretation == "high"
        assert very_high.interpretation == "very_high"


class TestPersonalityProfile:
    """Тесты для PersonalityProfile"""

    def test_create_empty_profile(self):
        """Тест создания пустого профиля"""
        # Создаем дефолтную черту
        default_trait = TraitAssessment(
            value=0.5,
            confidence=0.3,
            samples=0
        )

        # Создаем профиль
        profile = PersonalityProfile(
            user_id=123456,
            big_five=BigFive(
                openness=default_trait.model_copy(),
                conscientiousness=default_trait.model_copy(),
                extraversion=default_trait.model_copy(),
                agreeableness=default_trait.model_copy(),
                neuroticism=default_trait.model_copy()
            ),
            core_dynamics=CoreDynamics(
                resilience=default_trait.model_copy(),
                authenticity=default_trait.model_copy(),
                growth_mindset=default_trait.model_copy(),
                emotional_granularity=default_trait.model_copy(),
                cognitive_flexibility=default_trait.model_copy(),
                self_compassion=default_trait.model_copy(),
                meaning_making=default_trait.model_copy()
            ),
            adaptive_traits=AdaptiveTraits(
                current_energy=default_trait.model_copy(),
                stress_level=default_trait.model_copy(),
                openness_state=default_trait.model_copy(),
                creative_flow=default_trait.model_copy(),
                social_battery=default_trait.model_copy()
            ),
            domain_affinities=DomainAffinities(
                IDENTITY=default_trait.model_copy(),
                RELATIONSHIPS=default_trait.model_copy(),
                CAREER=default_trait.model_copy(),
                EMOTIONS=default_trait.model_copy(),
                SPIRITUALITY=default_trait.model_copy(),
                CREATIVITY=default_trait.model_copy(),
                BODY=default_trait.model_copy(),
                PAST=default_trait.model_copy(),
                FUTURE=default_trait.model_copy(),
                PRESENT=default_trait.model_copy(),
                GROWTH=default_trait.model_copy(),
                CHALLENGES=default_trait.model_copy(),
                VALUES=default_trait.model_copy()
            ),
            unique_signature=UniqueSignature(
                thinking_style="unknown",
                decision_pattern="unknown",
                energy_rhythm="unknown",
                learning_edge="unknown",
                love_language="unknown",
                stress_response="unknown"
            )
        )

        assert profile.user_id == 123456
        assert profile.total_samples == 0
        assert profile.completeness == 0.0

    def test_profile_serialization(self):
        """Тест сериализации профиля"""
        default_trait = TraitAssessment(value=0.5, confidence=0.3, samples=0)

        profile = PersonalityProfile(
            user_id=123456,
            big_five=BigFive(
                openness=default_trait.model_copy(),
                conscientiousness=default_trait.model_copy(),
                extraversion=default_trait.model_copy(),
                agreeableness=default_trait.model_copy(),
                neuroticism=default_trait.model_copy()
            ),
            core_dynamics=CoreDynamics(
                resilience=default_trait.model_copy(),
                authenticity=default_trait.model_copy(),
                growth_mindset=default_trait.model_copy(),
                emotional_granularity=default_trait.model_copy(),
                cognitive_flexibility=default_trait.model_copy(),
                self_compassion=default_trait.model_copy(),
                meaning_making=default_trait.model_copy()
            ),
            adaptive_traits=AdaptiveTraits(
                current_energy=default_trait.model_copy(),
                stress_level=default_trait.model_copy(),
                openness_state=default_trait.model_copy(),
                creative_flow=default_trait.model_copy(),
                social_battery=default_trait.model_copy()
            ),
            domain_affinities=DomainAffinities(
                IDENTITY=default_trait.model_copy(),
                RELATIONSHIPS=default_trait.model_copy(),
                CAREER=default_trait.model_copy(),
                EMOTIONS=default_trait.model_copy(),
                SPIRITUALITY=default_trait.model_copy(),
                CREATIVITY=default_trait.model_copy(),
                BODY=default_trait.model_copy(),
                PAST=default_trait.model_copy(),
                FUTURE=default_trait.model_copy(),
                PRESENT=default_trait.model_copy(),
                GROWTH=default_trait.model_copy(),
                CHALLENGES=default_trait.model_copy(),
                VALUES=default_trait.model_copy()
            ),
            unique_signature=UniqueSignature(
                thinking_style="visual-metaphorical",
                decision_pattern="feel-think-feel",
                energy_rhythm="90min_cycles",
                learning_edge="through_experience",
                love_language="quality_time",
                stress_response="withdraw_then_process"
            )
        )

        # Сериализация
        json_data = profile.model_dump_json()
        assert isinstance(json_data, str)

        # Десериализация
        restored = PersonalityProfile.model_validate_json(json_data)
        assert restored.user_id == profile.user_id
        assert restored.unique_signature.thinking_style == "visual-metaphorical"
