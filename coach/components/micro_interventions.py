"""
Micro Interventions - Тонкие психологические интервенции в ответах

Добавляет психологические техники: reframing, anchoring, gentle challenge
"""
from typing import Dict, Any
import logging
import random

logger = logging.getLogger(__name__)

class MicroInterventions:
    """Инъекция тонких психологических интервенций"""

    def inject(self, response: str, context: Dict[str, Any]) -> str:
        """
        Добавляет интервенции к ответу

        Args:
            response: Базовый ответ
            context: Контекст сообщения

        Returns:
            Ответ с интервенциями
        """
        interventions = []

        # 1. Reframing негативных убеждений
        if context.get('negative_belief_detected'):
            interventions.append(self._create_reframe(context))

        # 2. Anchoring позитивных состояний
        if context.get('positive_state_detected'):
            interventions.append(self._create_anchor(context))

        # 3. Gentle challenge для выхода из зоны комфорта
        if context.get('comfort_zone_detected'):
            interventions.append(self._create_challenge(context))

        if interventions:
            intervention = random.choice(interventions)
            return f"{response}\n\n{intervention}"

        return response

    def _create_reframe(self, context: Dict[str, Any]) -> str:
        """Создает reframing негативного убеждения"""
        negative = context.get('negative_statement', 'это сложно')
        templates = [
            f"Кстати, когда вы говорите '{negative}', что если посмотреть на это как на вызов для роста?",
            f"Интересно переформулировать '{negative}' как 'пока это сложно, но я учусь'?",
        ]
        return random.choice(templates)

    def _create_anchor(self, context: Dict[str, Any]) -> str:
        """Создает якорение позитивного состояния"""
        positive = context.get('positive_state', 'уверенность')
        return f"💫 Запомните это ощущение {positive}. К нему можно возвращаться."

    def _create_challenge(self, context: Dict[str, Any]) -> str:
        """Создает мягкий вызов"""
        return "💪 А что если на 10% выйти за пределы привычного здесь?"
