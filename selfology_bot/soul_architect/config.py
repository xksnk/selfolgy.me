"""
Soul Architect Configuration

Все настройки системы Soul-Architect в одном месте.
Изолированная конфигурация, не зависит от других модулей.
"""

from typing import Dict, List
from dataclasses import dataclass


@dataclass
class ScoringConfig:
    """Настройки scoring системы"""

    # Минимальные значения для надежной оценки
    MIN_SAMPLES_FOR_CONFIDENCE: int = 3
    MIN_CONFIDENCE_THRESHOLD: float = 0.5

    # Пороги для интерпретации
    VERY_LOW_THRESHOLD: float = 0.2
    LOW_THRESHOLD: float = 0.4
    MEDIUM_THRESHOLD: float = 0.6
    HIGH_THRESHOLD: float = 0.8

    # Значимые изменения
    SIGNIFICANT_CHANGE_THRESHOLD: float = 0.2

    # Веса для усреднения (если нужны)
    RECENCY_WEIGHT: float = 1.5  # Более свежие ответы важнее


@dataclass
class ProfileConfig:
    """Настройки профиля личности"""

    # Начальные значения для новых черт
    DEFAULT_TRAIT_VALUE: float = 0.5
    DEFAULT_CONFIDENCE: float = 0.3

    # Пороги полноты профиля
    MIN_COMPLETENESS_FOR_INSIGHTS: float = 0.3
    FULL_PROFILE_COMPLETENESS: float = 0.8

    # Категории черт
    TRAIT_CATEGORIES: List[str] = None

    def __post_init__(self):
        if self.TRAIT_CATEGORIES is None:
            self.TRAIT_CATEGORIES = [
                "big_five",
                "core_dynamics",
                "adaptive_traits",
                "domain_affinities"
            ]


@dataclass
class DatabaseConfig:
    """Настройки базы данных"""

    # Схема для всех таблиц Soul-Architect
    SCHEMA: str = "selfology"

    # Имена таблиц
    PERSONALITY_PROFILES_TABLE: str = "personality_profiles"
    TRAIT_HISTORY_TABLE: str = "trait_history"
    UNIQUE_SIGNATURES_TABLE: str = "unique_signatures"

    # Настройки истории
    HISTORY_RETENTION_DAYS: int = 365  # Хранить историю год
    MAX_HISTORY_RECORDS_PER_USER: int = 1000


@dataclass
class EvolutionConfig:
    """Настройки отслеживания эволюции"""

    # Периоды для анализа
    SHORT_PERIOD_DAYS: int = 7
    MEDIUM_PERIOD_DAYS: int = 30
    LONG_PERIOD_DAYS: int = 90

    # Тренды
    STABLE_CHANGE_THRESHOLD: float = 0.1
    INCREASING_THRESHOLD: float = 0.15
    DECREASING_THRESHOLD: float = -0.15


@dataclass
class DomainMapping:
    """Маппинг доменов из Intelligent Question Core"""

    # 13 доменов из intelligent_question_core
    DOMAINS: Dict[str, str] = None

    def __post_init__(self):
        if self.DOMAINS is None:
            self.DOMAINS = {
                "IDENTITY": "Идентичность",
                "RELATIONSHIPS": "Отношения",
                "CAREER": "Карьера",
                "EMOTIONS": "Эмоции",
                "SPIRITUALITY": "Духовность",
                "CREATIVITY": "Креативность",
                "BODY": "Тело",
                "PAST": "Прошлое",
                "FUTURE": "Будущее",
                "PRESENT": "Настоящее",
                "GROWTH": "Рост",
                "CHALLENGES": "Вызовы",
                "VALUES": "Ценности"
            }


@dataclass
class BigFiveMapping:
    """Маппинг Big Five черт"""

    TRAITS: Dict[str, str] = None

    def __post_init__(self):
        if self.TRAITS is None:
            self.TRAITS = {
                "openness": "Открытость опыту",
                "conscientiousness": "Добросовестность",
                "extraversion": "Экстраверсия",
                "agreeableness": "Доброжелательность",
                "neuroticism": "Нейротизм"
            }


@dataclass
class CoreDynamicsMapping:
    """Маппинг динамических черт"""

    TRAITS: Dict[str, str] = None

    def __post_init__(self):
        if self.TRAITS is None:
            self.TRAITS = {
                "resilience": "Устойчивость",
                "authenticity": "Аутентичность",
                "growth_mindset": "Установка на рост",
                "emotional_granularity": "Эмоциональная гранулярность",
                "cognitive_flexibility": "Когнитивная гибкость",
                "self_compassion": "Самосострадание",
                "meaning_making": "Создание смыслов"
            }


@dataclass
class AdaptiveTraitsMapping:
    """Маппинг адаптивных черт"""

    TRAITS: Dict[str, str] = None

    def __post_init__(self):
        if self.TRAITS is None:
            self.TRAITS = {
                "current_energy": "Текущая энергия",
                "stress_level": "Уровень стресса",
                "openness_state": "Готовность открываться",
                "creative_flow": "Творческий поток",
                "social_battery": "Социальная батарея"
            }


# ============================================================================
# ГЛОБАЛЬНЫЕ НАСТРОЙКИ
# ============================================================================

class SoulArchitectConfig:
    """
    Главная конфигурация Soul-Architect

    Используется:
        >>> from soul_architect.config import config
        >>> config.scoring.MIN_CONFIDENCE_THRESHOLD
        0.5
    """

    def __init__(self):
        self.scoring = ScoringConfig()
        self.profile = ProfileConfig()
        self.database = DatabaseConfig()
        self.evolution = EvolutionConfig()
        self.domains = DomainMapping()
        self.big_five = BigFiveMapping()
        self.core_dynamics = CoreDynamicsMapping()
        self.adaptive_traits = AdaptiveTraitsMapping()

    def get_trait_name_ru(self, category: str, trait: str) -> str:
        """
        Получить русское название черты

        Args:
            category: Категория (big_five, core_dynamics, etc.)
            trait: Английское имя черты

        Returns:
            Русское название или исходное имя
        """
        if category == "big_five":
            return self.big_five.TRAITS.get(trait, trait)
        elif category == "core_dynamics":
            return self.core_dynamics.TRAITS.get(trait, trait)
        elif category == "adaptive_traits":
            return self.adaptive_traits.TRAITS.get(trait, trait)
        elif category == "domain_affinities":
            return self.domains.DOMAINS.get(trait, trait)
        else:
            return trait

    def get_all_traits_for_category(self, category: str) -> List[str]:
        """
        Получить все черты для категории

        Args:
            category: Категория

        Returns:
            Список имен черт
        """
        if category == "big_five":
            return list(self.big_five.TRAITS.keys())
        elif category == "core_dynamics":
            return list(self.core_dynamics.TRAITS.keys())
        elif category == "adaptive_traits":
            return list(self.adaptive_traits.TRAITS.keys())
        elif category == "domain_affinities":
            return list(self.domains.DOMAINS.keys())
        else:
            return []


# Глобальный инстанс конфигурации
config = SoulArchitectConfig()
