"""
Confidence Calculator - Система расчета уверенности в советах и инсайтах

Рассчитывает и объясняет, насколько AI-коуч уверен в своих предположениях и рекомендациях.
"""

from typing import Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class ConfidenceCalculator:
    """
    Рассчитывает уверенность в инсайтах и советах коуча

    Факторы уверенности:
    - Консистентность данных (data_consistency)
    - Исторические паттерны (historical_patterns)
    - Валидация пользователем (user_validation)
    - Соответствие психологической теории (psychological_theory)
    - Полнота контекста (context_completeness)
    """

    CONFIDENCE_FACTORS = {
        'data_consistency': 0.30,      # Насколько данные consistent
        'historical_patterns': 0.25,   # Есть ли подтверждение в истории
        'user_validation': 0.20,       # Подтверждал ли user похожее ранее
        'psychological_theory': 0.15,  # Соответствие теории
        'context_completeness': 0.10   # Полнота контекста
    }

    def calculate(self, insight: Dict[str, Any], user_context: Dict[str, Any]) -> Tuple[float, str]:
        """
        Рассчитывает уверенность в инсайте/совете

        Args:
            insight: Инсайт или совет для оценки
            user_context: Контекст пользователя

        Returns:
            (confidence_score, explanation)
            - confidence_score: 0.0-1.0
            - explanation: Текстовое объяснение
        """
        scores = {}

        # 1. Data consistency
        scores['data_consistency'] = self._evaluate_data_consistency(insight, user_context)

        # 2. Historical patterns
        scores['historical_patterns'] = self._evaluate_historical_patterns(insight, user_context)

        # 3. User validation
        scores['user_validation'] = self._evaluate_user_validation(insight, user_context)

        # 4. Psychological theory
        scores['psychological_theory'] = self._evaluate_theory_alignment(insight)

        # 5. Context completeness
        scores['context_completeness'] = self._evaluate_context(user_context)

        # Weighted average
        confidence = sum(
            self.CONFIDENCE_FACTORS[factor] * score
            for factor, score in scores.items()
        )

        # Generate explanation
        explanation = self._generate_explanation(confidence, scores)

        logger.info(f"Calculated confidence: {confidence:.2f} for insight type: {insight.get('type')}")

        return confidence, explanation

    def _evaluate_data_consistency(self, insight: Dict[str, Any], user_context: Dict[str, Any]) -> float:
        """Оценивает консистентность данных"""

        # Простая эвристика: есть ли противоречия в данных
        big_five = user_context.get('personality_profile', {}).get('traits', {}).get('big_five', {})

        if not big_five:
            return 0.3  # Низкая уверенность без данных

        # Проверяем полноту Big Five
        completeness = len([v for v in big_five.values() if v is not None]) / 5.0

        # Проверяем, есть ли траектория
        has_trajectory = bool(user_context.get('personality_profile', {}).get('trajectory_insights'))

        if has_trajectory:
            completeness += 0.2

        return min(completeness, 1.0)

    def _evaluate_historical_patterns(self, insight: Dict[str, Any], user_context: Dict[str, Any]) -> float:
        """Оценивает подтверждение в исторических паттернах"""

        similar_states = user_context.get('similar_states', [])

        if not similar_states:
            return 0.3  # Нет истории - низкая уверенность

        # Если есть 3+ похожих состояния - высокая уверенность
        pattern_strength = min(len(similar_states) / 5.0, 1.0)

        # Если схожесть высокая (>0.7) - еще больше уверенности
        if similar_states:
            avg_similarity = sum(s.get('similarity_score', 0) for s in similar_states) / len(similar_states)
            pattern_strength = (pattern_strength + avg_similarity) / 2

        return pattern_strength

    def _evaluate_user_validation(self, insight: Dict[str, Any], user_context: Dict[str, Any]) -> float:
        """Оценивает, подтверждал ли пользователь похожие инсайты"""

        insights_history = user_context.get('insights_history', [])

        if not insights_history:
            return 0.5  # Нейтральная оценка без истории

        # Простая эвристика: есть ли похожие инсайты в прошлом
        insight_domain = insight.get('domain', 'general')
        similar_insights = [
            i for i in insights_history
            if i.get('psychological_domain') == insight_domain
        ]

        if similar_insights:
            return 0.8  # Пользователь уже работал с этой темой

        return 0.5

    def _evaluate_theory_alignment(self, insight: Dict[str, Any]) -> float:
        """Оценивает соответствие психологической теории"""

        # В реальной реализации здесь был бы анализ соответствия
        # конкретным психологическим теориям

        # Для демо: всегда умеренная уверенность
        return 0.7

    def _evaluate_context(self, user_context: Dict[str, Any]) -> float:
        """Оценивает полноту контекста"""

        required_fields = [
            'personality_profile',
            'recent_messages',
            'current_mood'
        ]

        present_fields = sum(1 for field in required_fields if user_context.get(field))
        completeness = present_fields / len(required_fields)

        return completeness

    def _generate_explanation(self, confidence: float, scores: Dict[str, float]) -> str:
        """Генерирует текстовое объяснение уверенности"""

        if confidence >= 0.85:
            base = "Высокая уверенность (85%+):"
        elif confidence >= 0.60:
            base = "Средняя уверенность (60-84%):"
        elif confidence >= 0.40:
            base = "Это гипотеза (40-59%):"
        else:
            base = "Эксперимент (<40%):"

        # Находим самый сильный фактор
        strongest = max(scores.items(), key=lambda x: x[1])
        weakest = min(scores.items(), key=lambda x: x[1])

        explanations = []

        # Strongest factor
        if strongest[1] > 0.7:
            factor_names = {
                'data_consistency': "данные консистентны",
                'historical_patterns': "есть устойчивые паттерны в вашей истории",
                'user_validation': "вы подтверждали похожее ранее",
                'psychological_theory': "это соответствует психологической теории",
                'context_completeness': "у меня полный контекст"
            }
            explanations.append(factor_names.get(strongest[0], ""))

        # Weakest factor (если < 0.5)
        if weakest[1] < 0.5:
            weak_factors = {
                'data_consistency': "но данных пока немного",
                'historical_patterns': "но мало исторических подтверждений",
                'user_validation': "но это новая тема для вас",
                'context_completeness': "но контекст неполный"
            }
            explanations.append(weak_factors.get(weakest[0], ""))

        explanation = base + " " + ", ".join(explanations) + "."

        return explanation

    def format_with_confidence(self, statement: str, confidence: float, explanation: str) -> str:
        """
        Форматирует утверждение с указанием уверенности

        Args:
            statement: Исходное утверждение
            confidence: Уровень уверенности
            explanation: Объяснение

        Returns:
            Отформатированное утверждение с префиксом уверенности
        """
        if confidence >= 0.85:
            prefix = "Основываясь на вашей истории,"
        elif confidence >= 0.60:
            prefix = "Вероятно,"
        elif confidence >= 0.40:
            prefix = "Это предположение, но возможно,"
        else:
            prefix = "Давайте проверим гипотезу:"

        return f"{prefix} {statement}\n\n_({explanation})_"


# === ПРИМЕР ИСПОЛЬЗОВАНИЯ ===

if __name__ == "__main__":
    user_context = {
        'personality_profile': {
            'traits': {
                'big_five': {
                    'openness': 0.85,
                    'conscientiousness': 0.72,
                    'extraversion': 0.68,
                    'agreeableness': 0.79,
                    'neuroticism': 0.34
                }
            },
            'trajectory_insights': {
                'trends': {
                    'openness': {'change': 0.25}
                }
            }
        },
        'similar_states': [
            {'similarity_score': 0.8},
            {'similarity_score': 0.75},
            {'similarity_score': 0.72}
        ],
        'insights_history': [
            {'psychological_domain': 'work'},
            {'psychological_domain': 'relationships'}
        ],
        'recent_messages': [],
        'current_mood': 'neutral'
    }

    insight = {
        'type': 'pattern_observation',
        'domain': 'work',
        'text': 'Вы склонны избегать конфликтов на работе'
    }

    calculator = ConfidenceCalculator()
    confidence, explanation = calculator.calculate(insight, user_context)

    print(f"=== CONFIDENCE SCORE ===")
    print(f"Score: {confidence:.2f}")
    print(f"\nExplanation: {explanation}")

    print(f"\n=== FORMATTED STATEMENT ===")
    formatted = calculator.format_with_confidence(
        insight['text'],
        confidence,
        explanation
    )
    print(formatted)
