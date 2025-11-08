"""
Evolution Tracker - Отслеживание эволюции личности

Отвечает за:
- Запись изменений черт в историю
- Анализ трендов развития
- Вычисление сводок эволюции
- Идентификацию значимых изменений
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from .models import TraitHistory, EvolutionSummary, PersonalityProfile, TraitAssessment
from .config import config

logger = logging.getLogger(__name__)


class EvolutionTracker:
    """
    Трекер эволюции личности

    Примеры:
        >>> tracker = EvolutionTracker()
        >>> await tracker.record_change(
        ...     user_id=123,
        ...     category="adaptive_traits",
        ...     trait_name="stress_level",
        ...     old_value=0.3,
        ...     new_value=0.7
        ... )
    """

    def __init__(self):
        self.config = config.evolution

    async def record_change(
        self,
        user_id: int,
        trait_category: str,
        trait_name: str,
        old_value: Optional[float],
        new_value: float,
        confidence: float,
        trigger: Optional[str] = None
    ) -> TraitHistory:
        """
        Записать изменение черты

        Args:
            user_id: ID пользователя
            trait_category: Категория черты
            trait_name: Имя черты
            old_value: Старое значение (None если первое)
            new_value: Новое значение
            confidence: Уверенность в новом значении
            trigger: Что вызвало изменение

        Returns:
            TraitHistory запись
        """
        history_record = TraitHistory(
            user_id=user_id,
            trait_category=trait_category,
            trait_name=trait_name,
            old_value=old_value,
            new_value=new_value,
            confidence=confidence,
            trigger=trigger
        )

        logger.debug(
            f"Recorded change for user {user_id}: "
            f"{trait_category}.{trait_name} {old_value} -> {new_value}"
        )

        return history_record

    def analyze_trait_trend(
        self,
        history: List[TraitHistory],
        period_days: Optional[int] = None
    ) -> Dict[str, any]:
        """
        Анализировать тренд изменения черты

        Args:
            history: История изменений черты
            period_days: Период для анализа (последние N дней)

        Returns:
            Словарь с анализом тренда
        """
        if not history:
            return {
                "direction": "stable",
                "magnitude": 0.0,
                "velocity": 0.0,
                "data_points": 0
            }

        # Фильтруем по периоду
        if period_days:
            cutoff_date = datetime.utcnow() - timedelta(days=period_days)
            history = [h for h in history if h.timestamp >= cutoff_date]

        if not history:
            return {
                "direction": "stable",
                "magnitude": 0.0,
                "velocity": 0.0,
                "data_points": 0
            }

        # Сортируем по времени
        sorted_history = sorted(history, key=lambda x: x.timestamp)

        # Вычисляем общее изменение
        first_value = sorted_history[0].old_value or sorted_history[0].new_value
        last_value = sorted_history[-1].new_value

        total_change = last_value - first_value

        # Вычисляем скорость изменения (изменение за день)
        time_span = (sorted_history[-1].timestamp - sorted_history[0].timestamp).days
        if time_span > 0:
            velocity = total_change / time_span
        else:
            velocity = 0.0

        # Определяем направление
        direction = self._determine_direction(total_change)

        return {
            "direction": direction,
            "magnitude": abs(total_change),
            "velocity": velocity,
            "data_points": len(history),
            "first_value": first_value,
            "last_value": last_value,
            "time_span_days": time_span
        }

    def calculate_evolution_summary(
        self,
        user_id: int,
        all_history: List[TraitHistory],
        period_days: int = 30
    ) -> EvolutionSummary:
        """
        Вычислить сводку эволюции за период

        Args:
            user_id: ID пользователя
            all_history: Вся история изменений
            period_days: Период для анализа

        Returns:
            EvolutionSummary
        """
        logger.info(f"Calculating evolution summary for user {user_id}, period {period_days} days")

        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=period_days)

        # Фильтруем по периоду
        period_history = [
            h for h in all_history
            if period_start <= h.timestamp <= period_end
        ]

        # Находим значимые изменения
        significant_changes = [
            h for h in period_history
            if self._is_significant_change(h.old_value, h.new_value)
        ]

        # Находим черты с наибольшими изменениями
        most_changed = self._find_most_changed_traits(period_history)

        # Анализируем направления по категориям
        overall_direction = self._analyze_category_directions(period_history)

        return EvolutionSummary(
            user_id=user_id,
            period_start=period_start,
            period_end=period_end,
            total_updates=len(period_history),
            significant_changes=len(significant_changes),
            most_changed_traits=most_changed,
            overall_direction=overall_direction
        )

    def compare_profiles(
        self,
        old_profile: PersonalityProfile,
        new_profile: PersonalityProfile
    ) -> Dict[str, List[Dict]]:
        """
        Сравнить два профиля и найти изменения

        Args:
            old_profile: Старый профиль
            new_profile: Новый профиль

        Returns:
            Словарь изменений по категориям
        """
        changes = {}

        for category in config.profile.TRAIT_CATEGORIES:
            old_layer = getattr(old_profile, category)
            new_layer = getattr(new_profile, category)

            category_changes = []
            traits = vars(old_layer)

            for trait_name in traits.keys():
                old_trait = getattr(old_layer, trait_name)
                new_trait = getattr(new_layer, trait_name)

                if isinstance(old_trait, TraitAssessment) and isinstance(new_trait, TraitAssessment):
                    change = new_trait.value - old_trait.value

                    if abs(change) > 0.01:  # Порог для учета изменения
                        category_changes.append({
                            "trait": trait_name,
                            "old_value": old_trait.value,
                            "new_value": new_trait.value,
                            "change": change,
                            "is_significant": self._is_significant_change(
                                old_trait.value,
                                new_trait.value
                            )
                        })

            if category_changes:
                changes[category] = category_changes

        return changes

    def get_trait_velocity(
        self,
        history: List[TraitHistory],
        window_days: int = 7
    ) -> float:
        """
        Вычислить скорость изменения черты

        Args:
            history: История изменений
            window_days: Окно для анализа

        Returns:
            Скорость изменения (изменение за день)
        """
        if len(history) < 2:
            return 0.0

        cutoff = datetime.utcnow() - timedelta(days=window_days)
        recent_history = [h for h in history if h.timestamp >= cutoff]

        if len(recent_history) < 2:
            return 0.0

        sorted_history = sorted(recent_history, key=lambda x: x.timestamp)
        first = sorted_history[0]
        last = sorted_history[-1]

        value_change = last.new_value - (first.old_value or first.new_value)
        time_diff = (last.timestamp - first.timestamp).days

        if time_diff > 0:
            return value_change / time_diff
        else:
            return 0.0

    def _determine_direction(self, change: float) -> str:
        """Определить направление изменения"""
        if abs(change) < self.config.STABLE_CHANGE_THRESHOLD:
            return "stable"
        elif change >= self.config.INCREASING_THRESHOLD:
            return "increasing"
        elif change <= self.config.DECREASING_THRESHOLD:
            return "decreasing"
        else:
            return "stable"

    def _is_significant_change(
        self,
        old_value: Optional[float],
        new_value: float
    ) -> bool:
        """Проверить, является ли изменение значимым"""
        if old_value is None:
            return False

        change = abs(new_value - old_value)
        return change >= config.scoring.SIGNIFICANT_CHANGE_THRESHOLD

    def _find_most_changed_traits(
        self,
        history: List[TraitHistory],
        top_n: int = 5
    ) -> Dict[str, float]:
        """Найти черты с наибольшими изменениями"""
        trait_changes = {}

        for record in history:
            trait_key = f"{record.trait_category}.{record.trait_name}"

            if record.old_value is not None:
                change = abs(record.new_value - record.old_value)

                if trait_key in trait_changes:
                    trait_changes[trait_key] = max(trait_changes[trait_key], change)
                else:
                    trait_changes[trait_key] = change

        # Сортируем и берем топ N
        sorted_traits = sorted(
            trait_changes.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return dict(sorted_traits[:top_n])

    def _analyze_category_directions(
        self,
        history: List[TraitHistory]
    ) -> Dict[str, str]:
        """Анализировать общие направления по категориям"""
        category_changes = {}

        # Группируем по категориям
        for record in history:
            category = record.trait_category

            if category not in category_changes:
                category_changes[category] = []

            if record.old_value is not None:
                change = record.new_value - record.old_value
                category_changes[category].append(change)

        # Вычисляем направление для каждой категории
        directions = {}

        for category, changes in category_changes.items():
            if changes:
                avg_change = sum(changes) / len(changes)
                directions[category] = self._determine_direction(avg_change)
            else:
                directions[category] = "stable"

        return directions


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def filter_history_by_period(
    history: List[TraitHistory],
    days: int
) -> List[TraitHistory]:
    """
    Фильтровать историю по периоду

    Args:
        history: История изменений
        days: Количество дней назад

    Returns:
        Отфильтрованная история
    """
    cutoff = datetime.utcnow() - timedelta(days=days)
    return [h for h in history if h.timestamp >= cutoff]


def group_history_by_trait(
    history: List[TraitHistory]
) -> Dict[Tuple[str, str], List[TraitHistory]]:
    """
    Группировать историю по чертам

    Args:
        history: История изменений

    Returns:
        Словарь {(category, trait_name): [history_records]}
    """
    grouped = {}

    for record in history:
        key = (record.trait_category, record.trait_name)

        if key not in grouped:
            grouped[key] = []

        grouped[key].append(record)

    return grouped
