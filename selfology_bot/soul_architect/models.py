"""
Soul Architect Models - Многослойная модель личности

Pydantic модели для всех слоев психологического профиля:
- Big Five (фундамент)
- Core Dynamics (динамическое ядро)
- Adaptive Traits (адаптивные черты)
- Domain Affinities (доменные профили)
- Unique Signature (уникальная подпись)
"""

from datetime import datetime
from typing import Dict, Optional, Literal
from pydantic import BaseModel, Field, field_validator


# ============================================================================
# БАЗОВЫЕ ТИПЫ
# ============================================================================

class TraitAssessment(BaseModel):
    """
    Оценка одной психологической черты с гибридной scoring системой

    Примеры:
        >>> trait = TraitAssessment(value=0.75, confidence=0.92, samples=5)
        >>> trait.interpretation  # "high"
        >>> trait.display_formats["percentage"]  # "75%"
    """

    # Основные метрики
    value: float = Field(ge=0.0, le=1.0, description="Значение черты от 0 до 1")
    confidence: float = Field(ge=0.0, le=1.0, description="Уверенность в оценке")
    variance: float = Field(default=0.0, ge=0.0, le=1.0, description="Разброс между ответами")
    samples: int = Field(ge=0, description="Количество ответов, на которых основана оценка")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Время последнего обновления")

    # Контекстные модификаторы
    percentile: Optional[int] = Field(default=None, ge=0, le=100, description="Позиция среди всех пользователей")
    direction: Literal["increasing", "stable", "decreasing"] = Field(
        default="stable",
        description="Тренд изменения черты"
    )
    interpretation: Literal["very_low", "low", "medium", "high", "very_high"] = Field(
        default="medium",
        description="Интерпретация значения"
    )

    # UI форматы
    display_formats: Dict[str, str] = Field(
        default_factory=dict,
        description="Форматы для отображения"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "value": 0.75,
                "confidence": 0.92,
                "variance": 0.08,
                "samples": 5,
                "percentile": 82,
                "direction": "increasing",
                "interpretation": "high",
                "display_formats": {
                    "percentage": "75%",
                    "stars": "4",
                    "label": "Развитая",
                    "color": "#4CAF50"
                }
            }
        }

    def model_post_init(self, __context):
        """Автоматически генерирует интерпретацию и форматы отображения"""
        if not self.display_formats:
            self.display_formats = self._generate_display_formats()

    def _generate_display_formats(self) -> Dict[str, str]:
        """Генерирует форматы для UI"""
        return {
            "percentage": f"{int(self.value * 100)}%",
            "stars": str(min(5, int(self.value * 5) + 1)),
            "label": self._get_label(),
            "color": self._get_color()
        }

    def _get_label(self) -> str:
        """Получить текстовый label"""
        if self.value < 0.2:
            return "Очень низкая"
        elif self.value < 0.4:
            return "Низкая"
        elif self.value < 0.6:
            return "Средняя"
        elif self.value < 0.8:
            return "Высокая"
        else:
            return "Очень высокая"

    def _get_color(self) -> str:
        """Получить цвет для UI"""
        if self.value < 0.2:
            return "#F44336"  # Red
        elif self.value < 0.4:
            return "#FF9800"  # Orange
        elif self.value < 0.6:
            return "#FFC107"  # Amber
        elif self.value < 0.8:
            return "#4CAF50"  # Green
        else:
            return "#2196F3"  # Blue


# ============================================================================
# BIG FIVE - ФУНДАМЕНТ
# ============================================================================

class BigFive(BaseModel):
    """
    Big Five - фундамент личности (OCEAN)

    Медленно меняющиеся базовые черты личности.
    """
    openness: TraitAssessment = Field(
        description="Открытость опыту - любознательность, креативность"
    )
    conscientiousness: TraitAssessment = Field(
        description="Добросовестность - организованность, ответственность"
    )
    extraversion: TraitAssessment = Field(
        description="Экстраверсия - энергичность, общительность"
    )
    agreeableness: TraitAssessment = Field(
        description="Доброжелательность - эмпатия, кооперация"
    )
    neuroticism: TraitAssessment = Field(
        description="Нейротизм - эмоциональная нестабильность"
    )


# ============================================================================
# CORE DYNAMICS - ДИНАМИЧЕСКОЕ ЯДРО
# ============================================================================

class CoreDynamics(BaseModel):
    """
    Core Dynamics - динамическое ядро личности

    Медленно меняющиеся глубинные характеристики.
    """
    resilience: TraitAssessment = Field(
        description="Способность восстанавливаться после трудностей"
    )
    authenticity: TraitAssessment = Field(
        description="Верность себе, аутентичность"
    )
    growth_mindset: TraitAssessment = Field(
        description="Установка на развитие vs фиксированное мышление"
    )
    emotional_granularity: TraitAssessment = Field(
        description="Тонкость различения эмоций"
    )
    cognitive_flexibility: TraitAssessment = Field(
        description="Гибкость мышления, адаптивность"
    )
    self_compassion: TraitAssessment = Field(
        description="Принятие себя, самосострадание"
    )
    meaning_making: TraitAssessment = Field(
        description="Способность создавать смыслы"
    )


# ============================================================================
# ADAPTIVE TRAITS - АДАПТИВНЫЕ ЧЕРТЫ
# ============================================================================

class AdaptiveTraits(BaseModel):
    """
    Adaptive Traits - быстро меняющиеся адаптивные черты

    Отражают текущее состояние, меняются от дня к дню.
    """
    current_energy: TraitAssessment = Field(
        description="Текущий уровень энергии"
    )
    stress_level: TraitAssessment = Field(
        description="Уровень стресса прямо сейчас"
    )
    openness_state: TraitAssessment = Field(
        description="Готовность открываться в данный момент"
    )
    creative_flow: TraitAssessment = Field(
        description="В потоке или нет"
    )
    social_battery: TraitAssessment = Field(
        description="Социальная энергия, заряженность для общения"
    )


# ============================================================================
# DOMAIN AFFINITIES - ДОМЕННЫЕ ПРОФИЛИ
# ============================================================================

class DomainAffinities(BaseModel):
    """
    Domain Affinities - важность 13 психологических доменов

    Показывает, какие области жизни наиболее значимы для человека.
    """
    IDENTITY: TraitAssessment = Field(
        description="Идентичность - кто я"
    )
    RELATIONSHIPS: TraitAssessment = Field(
        description="Отношения - связи с людьми"
    )
    CAREER: TraitAssessment = Field(
        description="Карьера - профессиональная самореализация"
    )
    EMOTIONS: TraitAssessment = Field(
        description="Эмоции - эмоциональный мир"
    )
    SPIRITUALITY: TraitAssessment = Field(
        description="Духовность - смыслы и ценности"
    )
    CREATIVITY: TraitAssessment = Field(
        description="Креативность - творческое самовыражение"
    )
    BODY: TraitAssessment = Field(
        description="Тело - физическое состояние"
    )
    PAST: TraitAssessment = Field(
        description="Прошлое - опыт и воспоминания"
    )
    FUTURE: TraitAssessment = Field(
        description="Будущее - планы и мечты"
    )
    PRESENT: TraitAssessment = Field(
        description="Настоящее - жизнь здесь и сейчас"
    )
    GROWTH: TraitAssessment = Field(
        description="Рост - развитие и обучение"
    )
    CHALLENGES: TraitAssessment = Field(
        description="Вызовы - трудности и препятствия"
    )
    VALUES: TraitAssessment = Field(
        description="Ценности - что важно в жизни"
    )


# ============================================================================
# UNIQUE SIGNATURE - УНИКАЛЬНАЯ ПОДПИСЬ
# ============================================================================

class UniqueSignature(BaseModel):
    """
    Unique Signature - что делает личность особенной

    Качественные характеристики, которые нельзя измерить числом.
    """
    thinking_style: str = Field(
        description="Стиль мышления (visual-metaphorical, logical-sequential, etc.)"
    )
    decision_pattern: str = Field(
        description="Паттерн принятия решений (feel-think-feel, think-feel, etc.)"
    )
    energy_rhythm: str = Field(
        description="Ритм энергии (90min_cycles, morning_person, etc.)"
    )
    learning_edge: str = Field(
        description="Граница обучения (through_experience, through_reading, etc.)"
    )
    love_language: str = Field(
        description="Язык любви (quality_time, words_of_affirmation, etc.)"
    )
    stress_response: str = Field(
        description="Реакция на стресс (withdraw_then_process, talk_it_out, etc.)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "thinking_style": "visual-metaphorical",
                "decision_pattern": "feel-think-feel",
                "energy_rhythm": "90min_cycles",
                "learning_edge": "through_experience",
                "love_language": "quality_time",
                "stress_response": "withdraw_then_process"
            }
        }


# ============================================================================
# PERSONALITY PROFILE - ПОЛНАЯ МОДЕЛЬ
# ============================================================================

class PersonalityProfile(BaseModel):
    """
    Personality Profile - многослойная модель личности

    Объединяет все слои в единый профиль пользователя.
    """
    user_id: int = Field(description="ID пользователя")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Все слои личности
    big_five: BigFive = Field(description="Big Five - фундамент")
    core_dynamics: CoreDynamics = Field(description="Динамическое ядро")
    adaptive_traits: AdaptiveTraits = Field(description="Адаптивные черты")
    domain_affinities: DomainAffinities = Field(description="Доменные профили")
    unique_signature: UniqueSignature = Field(description="Уникальная подпись")

    # Метаданные
    total_samples: int = Field(default=0, description="Общее количество ответов")
    completeness: float = Field(default=0.0, ge=0.0, le=1.0, description="Полнота профиля")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 123456,
                "total_samples": 50,
                "completeness": 0.65
            }
        }


# ============================================================================
# TRAIT HISTORY - ИСТОРИЯ ИЗМЕНЕНИЙ
# ============================================================================

class TraitHistory(BaseModel):
    """
    Trait History - запись об изменении черты

    Для отслеживания эволюции личности во времени.
    """
    user_id: int
    trait_category: Literal["big_five", "core_dynamics", "adaptive_traits", "domain_affinities"]
    trait_name: str
    old_value: Optional[float] = None
    new_value: float
    confidence: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    trigger: Optional[str] = Field(default=None, description="Что вызвало изменение")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 123456,
                "trait_category": "adaptive_traits",
                "trait_name": "stress_level",
                "old_value": 0.3,
                "new_value": 0.7,
                "confidence": 0.85,
                "trigger": "work_deadline_approaching"
            }
        }


# ============================================================================
# EVOLUTION SUMMARY - СВОДКА ИЗМЕНЕНИЙ
# ============================================================================

class EvolutionSummary(BaseModel):
    """
    Evolution Summary - сводка изменений личности за период

    Показывает, как человек изменился за определенное время.
    """
    user_id: int
    period_start: datetime
    period_end: datetime

    # Статистика изменений
    total_updates: int = Field(description="Всего обновлений")
    significant_changes: int = Field(description="Значимые изменения (>0.2)")
    most_changed_traits: Dict[str, float] = Field(
        description="Черты с наибольшими изменениями"
    )

    # Тренды
    overall_direction: Dict[str, str] = Field(
        description="Общее направление изменений по категориям"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 123456,
                "total_updates": 25,
                "significant_changes": 5,
                "most_changed_traits": {
                    "stress_level": 0.4,
                    "resilience": 0.25,
                    "social_battery": -0.3
                },
                "overall_direction": {
                    "big_five": "stable",
                    "core_dynamics": "increasing",
                    "adaptive_traits": "decreasing"
                }
            }
        }
