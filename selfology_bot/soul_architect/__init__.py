"""
Soul Architect - Многослойная система моделирования личности

Изолированная система для работы с психологическими профилями.

Публичный API:
- SoulArchitectService - главный сервис
- PersonalityProfile - модель профиля
- TraitAssessment - модель черты
- EvolutionSummary - сводка эволюции

Примеры использования:
    >>> from selfology_bot.soul_architect import SoulArchitectService
    >>> from selfology_bot.database.service import DatabaseService
    >>>
    >>> db = DatabaseService(...)
    >>> await db.initialize()
    >>>
    >>> soul = SoulArchitectService(db)
    >>> await soul.initialize()
    >>>
    >>> # Создать профиль
    >>> profile = await soul.create_profile(user_id=123456)
    >>>
    >>> # Обновить черту
    >>> profile = await soul.update_trait(
    ...     user_id=123456,
    ...     category="big_five",
    ...     trait_name="openness",
    ...     value=0.75,
    ...     confidence=0.85
    ... )
    >>>
    >>> # Получить эволюцию
    >>> evolution = await soul.get_evolution(user_id=123456, days=30)
"""

from .service import SoulArchitectService
from .models import (
    PersonalityProfile,
    TraitAssessment,
    BigFive,
    CoreDynamics,
    AdaptiveTraits,
    DomainAffinities,
    UniqueSignature,
    TraitHistory,
    EvolutionSummary
)

# Версия системы
__version__ = "1.0.0"

# Публичный API
__all__ = [
    # Главный сервис
    "SoulArchitectService",

    # Основные модели
    "PersonalityProfile",
    "TraitAssessment",

    # Слои личности
    "BigFive",
    "CoreDynamics",
    "AdaptiveTraits",
    "DomainAffinities",
    "UniqueSignature",

    # Эволюция
    "TraitHistory",
    "EvolutionSummary",
]
