"""
Enhanced AI Router - Умный роутинг AI моделей на основе психологического контекста
"""
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class EnhancedAIRouter:
    """Выбирает оптимальную AI модель на основе психологического контекста"""

    def route(self, message_context: Dict[str, Any]) -> str:
        """
        Выбирает модель на основе контекста

        Returns:
            'claude-3-5-sonnet' | 'gpt-4o' | 'gpt-4o-mini'
        """
        # Claude для сложных случаев
        if any([
            message_context.get('crisis_detected'),
            message_context.get('existential_question'),
            message_context.get('depth_level') == 'SHADOW',
            message_context.get('breakthrough_magnitude', 0) > 0.3,
            self._is_meaning_question(message_context.get('message', ''))
        ]):
            return 'claude-3-5-sonnet'

        # GPT-4o для обычного коучинга
        elif any([
            message_context.get('needs_action_plan'),
            message_context.get('emotional_support_needed'),
            len(message_context.get('message', '')) > 100
        ]):
            return 'gpt-4o'

        # GPT-4o-mini для простых взаимодействий
        else:
            return 'gpt-4o-mini'

    def _is_meaning_question(self, message: str) -> bool:
        """Детектит экзистенциальные вопросы"""
        meaning_keywords = ['смысл', 'зачем', 'кто я', 'предназначение', 'зачем жить']
        return any(kw in message.lower() for kw in meaning_keywords)
