"""
Profile Builder - Построение многослойного профиля личности

Отвечает за:
- Создание нового профиля
- Инициализацию всех слоев личности
- Вычисление полноты профиля
- Обновление профиля из черт
"""

import logging
from datetime import datetime
from typing import Dict, Optional

from .models import (
    PersonalityProfile,
    BigFive,
    CoreDynamics,
    AdaptiveTraits,
    DomainAffinities,
    UniqueSignature,
    TraitAssessment
)
from .trait_scorer import TraitScorer
from .config import config

logger = logging.getLogger(__name__)


class ProfileBuilder:
    """
    Построитель многослойных профилей личности

    Примеры:
        >>> builder = ProfileBuilder()
        >>> profile = builder.create_empty_profile(user_id=123456)
        >>> profile.completeness  # 0.0
    """

    def __init__(self):
        self.scorer = TraitScorer()
        self.config = config.profile

    def create_empty_profile(self, user_id: int) -> PersonalityProfile:
        """
        Создать пустой профиль со значениями по умолчанию

        Args:
            user_id: ID пользователя

        Returns:
            PersonalityProfile с инициализированными слоями
        """
        logger.info(f"Creating empty profile for user {user_id}")

        # Создаем дефолтную черту
        default_trait = self._create_default_trait()

        # Инициализируем Big Five
        big_five = BigFive(
            openness=default_trait.model_copy(),
            conscientiousness=default_trait.model_copy(),
            extraversion=default_trait.model_copy(),
            agreeableness=default_trait.model_copy(),
            neuroticism=default_trait.model_copy()
        )

        # Инициализируем Core Dynamics
        core_dynamics = CoreDynamics(
            resilience=default_trait.model_copy(),
            authenticity=default_trait.model_copy(),
            growth_mindset=default_trait.model_copy(),
            emotional_granularity=default_trait.model_copy(),
            cognitive_flexibility=default_trait.model_copy(),
            self_compassion=default_trait.model_copy(),
            meaning_making=default_trait.model_copy()
        )

        # Инициализируем Adaptive Traits
        adaptive_traits = AdaptiveTraits(
            current_energy=default_trait.model_copy(),
            stress_level=default_trait.model_copy(),
            openness_state=default_trait.model_copy(),
            creative_flow=default_trait.model_copy(),
            social_battery=default_trait.model_copy()
        )

        # Инициализируем Domain Affinities
        domain_affinities = DomainAffinities(
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
        )

        # Инициализируем Unique Signature
        unique_signature = UniqueSignature(
            thinking_style="unknown",
            decision_pattern="unknown",
            energy_rhythm="unknown",
            learning_edge="unknown",
            love_language="unknown",
            stress_response="unknown"
        )

        # Создаем профиль
        profile = PersonalityProfile(
            user_id=user_id,
            big_five=big_five,
            core_dynamics=core_dynamics,
            adaptive_traits=adaptive_traits,
            domain_affinities=domain_affinities,
            unique_signature=unique_signature,
            total_samples=0,
            completeness=0.0
        )

        logger.info(f"Empty profile created for user {user_id}")
        return profile

    def update_profile_trait(
        self,
        profile: PersonalityProfile,
        category: str,
        trait_name: str,
        new_trait: TraitAssessment
    ) -> PersonalityProfile:
        """
        Обновить конкретную черту в профиле

        Args:
            profile: Профиль для обновления
            category: Категория (big_five, core_dynamics, etc.)
            trait_name: Имя черты
            new_trait: Новая оценка черты

        Returns:
            Обновленный профиль
        """
        logger.debug(f"Updating trait {category}.{trait_name} for user {profile.user_id}")

        # Получаем слой
        layer = getattr(profile, category)

        # Обновляем черту
        setattr(layer, trait_name, new_trait)

        # Обновляем timestamp
        profile.updated_at = datetime.utcnow()

        # Пересчитываем полноту
        profile.completeness = self.calculate_completeness(profile)

        # Обновляем total_samples
        profile.total_samples = self._count_total_samples(profile)

        return profile

    def calculate_completeness(self, profile: PersonalityProfile) -> float:
        """
        Вычислить полноту профиля (0.0 - 1.0)

        Полнота зависит от:
        - Количества черт с данными (samples > 0)
        - Confidence черт

        Args:
            profile: Профиль для оценки

        Returns:
            Полнота от 0.0 до 1.0
        """
        total_traits = 0
        filled_traits = 0
        total_confidence = 0.0

        # Проверяем все категории
        for category in self.config.TRAIT_CATEGORIES:
            layer = getattr(profile, category)
            traits = vars(layer)

            for trait_name, trait in traits.items():
                if isinstance(trait, TraitAssessment):
                    total_traits += 1

                    if trait.samples > 0:
                        filled_traits += 1
                        total_confidence += trait.confidence

        if total_traits == 0:
            return 0.0

        # Вычисляем полноту
        fill_ratio = filled_traits / total_traits
        avg_confidence = total_confidence / filled_traits if filled_traits > 0 else 0.0

        # Итоговая полнота (50% fill ratio, 50% confidence)
        completeness = (fill_ratio * 0.5 + avg_confidence * 0.5)

        return round(completeness, 2)

    def build_from_trait_dict(
        self,
        user_id: int,
        trait_data: Dict[str, Dict[str, float]]
    ) -> PersonalityProfile:
        """
        Построить профиль из словаря черт

        Args:
            user_id: ID пользователя
            trait_data: Словарь {category: {trait_name: value}}

        Returns:
            Построенный профиль

        Example:
            >>> data = {
            ...     "big_five": {"openness": 0.75, "extraversion": 0.6},
            ...     "core_dynamics": {"resilience": 0.8}
            ... }
            >>> profile = builder.build_from_trait_dict(123, data)
        """
        logger.info(f"Building profile from trait dict for user {user_id}")

        # Создаем пустой профиль
        profile = self.create_empty_profile(user_id)

        # Заполняем черты из данных
        for category, traits in trait_data.items():
            if category not in self.config.TRAIT_CATEGORIES:
                logger.warning(f"Unknown category: {category}")
                continue

            layer = getattr(profile, category)

            for trait_name, value in traits.items():
                if not hasattr(layer, trait_name):
                    logger.warning(f"Unknown trait: {category}.{trait_name}")
                    continue

                # Создаем TraitAssessment
                trait = TraitAssessment(
                    value=value,
                    confidence=0.7,  # Средняя уверенность
                    variance=0.0,
                    samples=1,
                    interpretation=self.scorer._get_interpretation(value)
                )

                setattr(layer, trait_name, trait)

        # Пересчитываем метаданные
        profile.completeness = self.calculate_completeness(profile)
        profile.total_samples = self._count_total_samples(profile)

        logger.info(f"Profile built with completeness {profile.completeness}")
        return profile

    def merge_profiles(
        self,
        base_profile: PersonalityProfile,
        update_profile: PersonalityProfile,
        prefer_newer: bool = True
    ) -> PersonalityProfile:
        """
        Объединить два профиля

        Args:
            base_profile: Базовый профиль
            update_profile: Профиль с обновлениями
            prefer_newer: Предпочитать более новые черты при конфликте

        Returns:
            Объединенный профиль
        """
        logger.info(f"Merging profiles for user {base_profile.user_id}")

        merged = base_profile.model_copy(deep=True)

        # Для каждой категории
        for category in self.config.TRAIT_CATEGORIES:
            base_layer = getattr(base_profile, category)
            update_layer = getattr(update_profile, category)
            merged_layer = getattr(merged, category)

            traits = vars(base_layer)

            for trait_name in traits.keys():
                base_trait = getattr(base_layer, trait_name)
                update_trait = getattr(update_layer, trait_name)

                # Выбираем лучшую черту
                if prefer_newer and update_trait.samples > 0:
                    # Используем обновленную черту
                    setattr(merged_layer, trait_name, update_trait)
                elif base_trait.samples == 0 and update_trait.samples > 0:
                    # Используем обновленную, если базовая пустая
                    setattr(merged_layer, trait_name, update_trait)
                elif update_trait.confidence > base_trait.confidence:
                    # Используем более уверенную
                    setattr(merged_layer, trait_name, update_trait)

        # Обновляем метаданные
        merged.updated_at = datetime.utcnow()
        merged.completeness = self.calculate_completeness(merged)
        merged.total_samples = self._count_total_samples(merged)

        return merged

    def _create_default_trait(self) -> TraitAssessment:
        """Создать черту по умолчанию"""
        return TraitAssessment(
            value=self.config.DEFAULT_TRAIT_VALUE,
            confidence=self.config.DEFAULT_CONFIDENCE,
            variance=0.0,
            samples=0,
            interpretation="medium",
            direction="stable"
        )

    def _count_total_samples(self, profile: PersonalityProfile) -> int:
        """Подсчитать общее количество семплов в профиле"""
        total = 0

        for category in self.config.TRAIT_CATEGORIES:
            layer = getattr(profile, category)
            traits = vars(layer)

            for trait in traits.values():
                if isinstance(trait, TraitAssessment):
                    total += trait.samples

        return total


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def extract_trait_values(profile: PersonalityProfile, category: str) -> Dict[str, float]:
    """
    Извлечь значения всех черт категории

    Args:
        profile: Профиль
        category: Категория

    Returns:
        Словарь {trait_name: value}
    """
    result = {}
    layer = getattr(profile, category)
    traits = vars(layer)

    for trait_name, trait in traits.items():
        if isinstance(trait, TraitAssessment):
            result[trait_name] = trait.value

    return result


def get_top_traits(profile: PersonalityProfile, category: str, n: int = 5) -> Dict[str, float]:
    """
    Получить топ N самых выраженных черт категории

    Args:
        profile: Профиль
        category: Категория
        n: Количество черт

    Returns:
        Словарь {trait_name: value} (отсортированный)
    """
    values = extract_trait_values(profile, category)
    sorted_traits = sorted(values.items(), key=lambda x: x[1], reverse=True)

    return dict(sorted_traits[:n])
