"""
Unit tests for TraitScorer
"""

import pytest
from ..trait_scorer import TraitScorer, calculate_percentile, normalize_value
from ..models import TraitAssessment


class TestTraitScorer:
    """Тесты для TraitScorer"""

    @pytest.fixture
    def scorer(self):
        """Фикстура - экземпляр scorer"""
        return TraitScorer()

    def test_calculate_trait_single_value(self, scorer):
        """Тест вычисления черты из одного значения"""
        trait = scorer.calculate_trait([0.75])

        assert trait.value == 0.75
        assert trait.samples == 1
        assert trait.confidence == 0.5  # Средний confidence для 1 значения

    def test_calculate_trait_multiple_values(self, scorer):
        """Тест вычисления черты из нескольких значений"""
        values = [0.7, 0.75, 0.8]
        trait = scorer.calculate_trait(values)

        assert 0.7 <= trait.value <= 0.8
        assert trait.samples == 3
        assert trait.confidence > 0.5

    def test_calculate_trait_consistent_values(self, scorer):
        """Тест с консистентными значениями (высокий confidence)"""
        values = [0.75, 0.75, 0.75, 0.75]
        trait = scorer.calculate_trait(values)

        assert trait.value == 0.75
        assert trait.variance < 0.01  # Очень низкий разброс
        assert trait.confidence > 0.8  # Высокий confidence

    def test_calculate_trait_varying_values(self, scorer):
        """Тест с разбросанными значениями (низкий confidence)"""
        values = [0.2, 0.5, 0.8, 0.9]
        trait = scorer.calculate_trait(values)

        assert trait.variance > 0.2  # Высокий разброс
        assert trait.confidence < 0.8  # Ниже confidence

    def test_update_trait(self, scorer):
        """Тест обновления существующей черты"""
        current = TraitAssessment(
            value=0.5,
            confidence=0.6,
            variance=0.1,
            samples=3
        )

        updated = scorer.update_trait(current, new_value=0.7)

        assert updated.value > current.value
        assert updated.samples == 4
        assert updated.direction in ["increasing", "stable"]

    def test_update_trait_with_recency_weight(self, scorer):
        """Тест обновления с весом recency"""
        current = TraitAssessment(
            value=0.5,
            confidence=0.6,
            variance=0.1,
            samples=10
        )

        # Высокий recency weight - новое значение важнее
        updated = scorer.update_trait(current, new_value=0.9, recency_weight=5.0)

        assert updated.value > 0.6  # Сильно сдвинулось к новому значению

    def test_calculate_change_significance(self, scorer):
        """Тест вычисления значимости изменения"""
        # Значимое изменение
        change, is_significant = scorer.calculate_change_significance(0.3, 0.7)
        assert is_significant is True
        assert change == 0.4

        # Незначимое изменение
        change, is_significant = scorer.calculate_change_significance(0.5, 0.55)
        assert is_significant is False
        assert change == 0.05

    def test_interpretation_levels(self, scorer):
        """Тест интерпретации значений"""
        very_low = scorer.calculate_trait([0.1])
        low = scorer.calculate_trait([0.3])
        medium = scorer.calculate_trait([0.5])
        high = scorer.calculate_trait([0.7])
        very_high = scorer.calculate_trait([0.9])

        assert very_low.interpretation == "very_low"
        assert low.interpretation == "low"
        assert medium.interpretation == "medium"
        assert high.interpretation == "high"
        assert very_high.interpretation == "very_high"


class TestHelperFunctions:
    """Тесты для вспомогательных функций"""

    def test_calculate_percentile(self):
        """Тест вычисления percentile"""
        all_values = [0.2, 0.3, 0.5, 0.7, 0.8, 0.9]

        # 0.5 - медиана, должна быть ~50-й percentile
        percentile = calculate_percentile(0.5, all_values)
        assert 40 <= percentile <= 60

        # 0.9 - максимум, должна быть ~100-й percentile
        percentile = calculate_percentile(0.9, all_values)
        assert percentile >= 90

        # 0.2 - минимум, должна быть ~0-й percentile
        percentile = calculate_percentile(0.2, all_values)
        assert percentile <= 20

    def test_normalize_value(self):
        """Тест нормализации значения"""
        # Значение в середине диапазона
        normalized = normalize_value(5.0, min_val=0.0, max_val=10.0)
        assert normalized == 0.5

        # Значение на минимуме
        normalized = normalize_value(0.0, min_val=0.0, max_val=10.0)
        assert normalized == 0.0

        # Значение на максимуме
        normalized = normalize_value(10.0, min_val=0.0, max_val=10.0)
        assert normalized == 1.0

        # Значение вне диапазона (должно ограничиться)
        normalized = normalize_value(15.0, min_val=0.0, max_val=10.0)
        assert normalized == 1.0

        normalized = normalize_value(-5.0, min_val=0.0, max_val=10.0)
        assert normalized == 0.0
