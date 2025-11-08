"""
Trait Scorer - Гибридная система оценки психологических черт

Отвечает за:
- Вычисление значений черт из множества ответов
- Расчет confidence и variance
- Интерпретацию значений
- Обновление черт с учетом новых данных
"""

import statistics
from datetime import datetime
from typing import List, Optional, Tuple
import logging

from .models import TraitAssessment
from .config import config

logger = logging.getLogger(__name__)


class TraitScorer:
    """
    Scoring система для психологических черт

    Примеры:
        >>> scorer = TraitScorer()
        >>> trait = scorer.calculate_trait([0.7, 0.8, 0.75])
        >>> trait.value  # 0.75
        >>> trait.confidence  # 0.92
    """

    def __init__(self):
        self.config = config.scoring

    def calculate_trait(
        self,
        values: List[float],
        weights: Optional[List[float]] = None,
        percentile: Optional[int] = None
    ) -> TraitAssessment:
        """
        Вычислить черту из списка значений

        Args:
            values: Список значений (0.0 - 1.0)
            weights: Опциональные веса для значений
            percentile: Позиция среди других пользователей

        Returns:
            TraitAssessment с вычисленными метриками
        """
        if not values:
            return self._create_default_trait()

        if len(values) == 1:
            return self._create_single_value_trait(values[0], percentile)

        # Вычисляем основное значение (взвешенное среднее)
        value = self._calculate_weighted_mean(values, weights)

        # Вычисляем confidence
        confidence = self._calculate_confidence(values)

        # Вычисляем variance (разброс)
        variance = self._calculate_variance(values)

        # Определяем интерпретацию
        interpretation = self._get_interpretation(value)

        # Определяем direction (нужна история, пока stable)
        direction = "stable"

        return TraitAssessment(
            value=value,
            confidence=confidence,
            variance=variance,
            samples=len(values),
            percentile=percentile,
            direction=direction,
            interpretation=interpretation
        )

    def update_trait(
        self,
        current_trait: TraitAssessment,
        new_value: float,
        recency_weight: Optional[float] = None
    ) -> TraitAssessment:
        """
        Обновить существующую черту новым значением

        Args:
            current_trait: Текущая оценка черты
            new_value: Новое значение (0.0 - 1.0)
            recency_weight: Вес нового значения (по умолчанию из config)

        Returns:
            Обновленная TraitAssessment
        """
        if recency_weight is None:
            recency_weight = self.config.RECENCY_WEIGHT

        # Старое значение и количество семплов
        old_value = current_trait.value
        old_samples = current_trait.samples

        # Вычисляем новое значение (взвешенное среднее)
        total_weight = old_samples + recency_weight
        new_trait_value = (old_value * old_samples + new_value * recency_weight) / total_weight

        # Обновляем variance
        # Упрощенная формула: берем разницу между старым и новым
        value_diff = abs(new_value - old_value)
        new_variance = (current_trait.variance * old_samples + value_diff) / (old_samples + 1)
        new_variance = min(new_variance, 1.0)  # Ограничиваем

        # Обновляем confidence (больше семплов = выше confidence)
        new_samples = old_samples + 1
        new_confidence = self._calculate_confidence_from_samples(new_samples, new_variance)

        # Определяем direction
        direction = self._get_direction(old_value, new_trait_value)

        # Определяем интерпретацию
        interpretation = self._get_interpretation(new_trait_value)

        return TraitAssessment(
            value=new_trait_value,
            confidence=new_confidence,
            variance=new_variance,
            samples=new_samples,
            last_updated=datetime.utcnow(),
            percentile=current_trait.percentile,
            direction=direction,
            interpretation=interpretation
        )

    def calculate_change_significance(
        self,
        old_value: float,
        new_value: float
    ) -> Tuple[float, bool]:
        """
        Вычислить значимость изменения черты

        Args:
            old_value: Старое значение
            new_value: Новое значение

        Returns:
            (change_magnitude, is_significant)
        """
        change = abs(new_value - old_value)
        is_significant = change >= self.config.SIGNIFICANT_CHANGE_THRESHOLD

        return change, is_significant

    def _calculate_weighted_mean(
        self,
        values: List[float],
        weights: Optional[List[float]] = None
    ) -> float:
        """Вычислить взвешенное среднее"""
        if weights is None:
            # Даем больший вес более свежим значениям
            weights = [1 + (i * 0.1) for i in range(len(values))]

        if len(weights) != len(values):
            weights = [1.0] * len(values)

        weighted_sum = sum(v * w for v, w in zip(values, weights))
        total_weight = sum(weights)

        return weighted_sum / total_weight

    def _calculate_confidence(self, values: List[float]) -> float:
        """
        Вычислить confidence из списка значений

        Confidence зависит от:
        - Количества семплов (больше = выше)
        - Консистентности (меньше разброс = выше)
        """
        if len(values) < self.config.MIN_SAMPLES_FOR_CONFIDENCE:
            return 0.3

        # Вычисляем стандартное отклонение
        if len(values) > 1:
            std_dev = statistics.stdev(values)
        else:
            std_dev = 0.0

        # Консистентность (низкое std_dev = высокая консистентность)
        consistency = 1.0 - min(std_dev, 1.0)

        # Sample factor (больше семплов = выше)
        sample_factor = min(len(values) / 10, 1.0)

        # Итоговый confidence
        confidence = (consistency * 0.7 + sample_factor * 0.3)

        return max(self.config.MIN_CONFIDENCE_THRESHOLD, confidence)

    def _calculate_confidence_from_samples(
        self,
        samples: int,
        variance: float
    ) -> float:
        """Вычислить confidence из количества семплов и variance"""
        if samples < self.config.MIN_SAMPLES_FOR_CONFIDENCE:
            return 0.3

        # Консистентность
        consistency = 1.0 - variance

        # Sample factor
        sample_factor = min(samples / 10, 1.0)

        # Итоговый confidence
        confidence = (consistency * 0.7 + sample_factor * 0.3)

        return max(self.config.MIN_CONFIDENCE_THRESHOLD, confidence)

    def _calculate_variance(self, values: List[float]) -> float:
        """Вычислить variance (разброс)"""
        if len(values) < 2:
            return 0.0

        try:
            std_dev = statistics.stdev(values)
            return min(std_dev, 1.0)
        except statistics.StatisticsError:
            return 0.0

    def _get_interpretation(self, value: float) -> str:
        """Получить текстовую интерпретацию значения"""
        if value < self.config.VERY_LOW_THRESHOLD:
            return "very_low"
        elif value < self.config.LOW_THRESHOLD:
            return "low"
        elif value < self.config.MEDIUM_THRESHOLD:
            return "medium"
        elif value < self.config.HIGH_THRESHOLD:
            return "high"
        else:
            return "very_high"

    def _get_direction(self, old_value: float, new_value: float) -> str:
        """Определить направление изменения"""
        change = new_value - old_value

        if abs(change) < 0.05:  # Незначительное изменение
            return "stable"
        elif change > 0:
            return "increasing"
        else:
            return "decreasing"

    def _create_default_trait(self) -> TraitAssessment:
        """Создать черту со значениями по умолчанию"""
        return TraitAssessment(
            value=config.profile.DEFAULT_TRAIT_VALUE,
            confidence=config.profile.DEFAULT_CONFIDENCE,
            variance=0.0,
            samples=0,
            interpretation="medium",
            direction="stable"
        )

    def _create_single_value_trait(
        self,
        value: float,
        percentile: Optional[int] = None
    ) -> TraitAssessment:
        """Создать черту из одного значения"""
        return TraitAssessment(
            value=value,
            confidence=0.5,  # Средний confidence для одного значения
            variance=0.0,
            samples=1,
            percentile=percentile,
            interpretation=self._get_interpretation(value),
            direction="stable"
        )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_percentile(value: float, all_values: List[float]) -> int:
    """
    Вычислить percentile относительно других значений

    Args:
        value: Значение для оценки
        all_values: Все значения для сравнения

    Returns:
        Percentile (0-100)
    """
    if not all_values:
        return 50

    sorted_values = sorted(all_values)
    position = sum(1 for v in sorted_values if v <= value)
    percentile = int((position / len(sorted_values)) * 100)

    return percentile


def normalize_value(value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """
    Нормализовать значение в диапазон 0-1

    Args:
        value: Исходное значение
        min_val: Минимум диапазона
        max_val: Максимум диапазона

    Returns:
        Нормализованное значение
    """
    if max_val == min_val:
        return 0.5

    normalized = (value - min_val) / (max_val - min_val)
    return max(0.0, min(1.0, normalized))
