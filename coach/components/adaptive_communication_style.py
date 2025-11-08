"""
Adaptive Communication Style - Адаптивный стиль общения для AI-коуча

Этот компонент определяет оптимальный стиль ответа based on user's personality and current state.
"""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class AdaptiveCommunicationStyle:
    """
    Определяет оптимальный стиль коммуникации для каждого пользователя

    Адаптирует:
    - Глубину ответа (surface/medium/deep/profound)
    - Эмоциональный тон (neutral/warm/challenging/celebrating)
    - Структуру (bullet_points/narrative/mixed)
    - Директивность (0-1: от недирективного до очень директивного)
    - Использование метафор
    - Соотношение вопросов к утверждениям
    - Стиль примеров (abstract/personal/practical)
    """

    def determine_style(self, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Определяет оптимальный стиль ответа

        Args:
            user_context: Полный контекст пользователя

        Returns:
            Dict с параметрами стиля
        """
        big_five = user_context.get('personality_profile', {}).get('traits', {}).get('big_five', {})
        current_mood = user_context.get('current_mood', 'neutral')
        conversation_stage = user_context.get('conversation_stage', 'building_rapport')

        style = {
            "depth_level": "medium",
            "emotional_tone": "warm_supportive",
            "structure": "narrative",
            "directiveness": 0.5,
            "metaphor_usage": "moderate",
            "question_ratio": 0.3,
            "example_style": "personal"
        }

        # === АДАПТАЦИЯ ПОД BIG FIVE ===

        # Openness
        openness = big_five.get('openness', 0.5)
        if openness > 0.7:
            style["metaphor_usage"] = "frequent"
            style["example_style"] = "abstract"
            style["depth_level"] = "profound"
        elif openness < 0.3:
            style["metaphor_usage"] = "minimal"
            style["example_style"] = "practical"
            style["depth_level"] = "medium"

        # Conscientiousness
        conscientiousness = big_five.get('conscientiousness', 0.5)
        if conscientiousness > 0.7:
            style["structure"] = "bullet_points"
            style["example_style"] = "practical"
            style["directiveness"] = 0.6

        # Extraversion
        extraversion = big_five.get('extraversion', 0.5)
        if extraversion > 0.7:
            style["emotional_tone"] = "energetic_inspiring"
        elif extraversion < 0.3:
            style["emotional_tone"] = "calm_reflective"

        # Agreeableness
        agreeableness = big_five.get('agreeableness', 0.5)
        if agreeableness > 0.7:
            style["emotional_tone"] = "warm_validating"
            style["directiveness"] = 0.3  # Более мягкий подход

        # Neuroticism
        neuroticism = big_five.get('neuroticism', 0.5)
        if neuroticism > 0.6:
            style["emotional_tone"] = "reassuring_stable"
            style["depth_level"] = "medium"  # Не перегружаем

        # === АДАПТАЦИЯ ПОД ЭМОЦИОНАЛЬНОЕ СОСТОЯНИЕ ===

        if current_mood == 'crisis':
            style["emotional_tone"] = "deeply_empathetic"
            style["directiveness"] = 0.7
            style["structure"] = "clear_steps"
            style["question_ratio"] = 0.1  # Меньше вопросов, больше поддержки

        elif current_mood == 'breakthrough':
            style["emotional_tone"] = "celebrating_curious"
            style["question_ratio"] = 0.5
            style["depth_level"] = "profound"

        # === АДАПТАЦИЯ ПОД СТАДИЮ РАЗГОВОРА ===

        if conversation_stage == 'getting_acquainted':
            style["directiveness"] = 0.3
            style["depth_level"] = "surface"

        elif conversation_stage == 'deep_coaching':
            style["depth_level"] = "profound"
            style["question_ratio"] = 0.4

        return style

    def format_response(self, content: str, style: Dict[str, Any]) -> str:
        """
        Форматирует ответ согласно выбранному стилю

        Args:
            content: Базовый контент ответа
            style: Параметры стиля

        Returns:
            Отформатированный ответ
        """
        # В реальной реализации здесь бы использовались
        # специальные промпты для AI модели

        # Для демо просто добавляем префикс в зависимости от тона
        tone_prefixes = {
            "warm_supportive": "💙 ",
            "energetic_inspiring": "🚀 ",
            "celebrating_curious": "🎉 ",
            "deeply_empathetic": "🤗 ",
            "reassuring_stable": "🌱 ",
            "calm_reflective": "🧘 ",
            "warm_validating": "💚 ",
        }

        prefix = tone_prefixes.get(style["emotional_tone"], "")
        return f"{prefix}{content}"

    def get_style_guidance_for_ai(self, style: Dict[str, Any]) -> str:
        """
        Генерирует инструкции для AI модели на основе стиля

        Эти инструкции добавляются в системный промпт

        Args:
            style: Параметры стиля

        Returns:
            Текстовые инструкции для AI
        """
        guidance = []

        # Depth level
        depth_guidance = {
            "surface": "Используй простой, понятный язык. Фокусируйся на практических аспектах.",
            "medium": "Баланс между практикой и теорией. Добавляй контекст и примеры.",
            "deep": "Углубляйся в психологические механизмы. Исследуй причинно-следственные связи.",
            "profound": "Выходи на экзистенциальный уровень. Исследуй смыслы, ценности, философию."
        }
        guidance.append(depth_guidance.get(style["depth_level"], ""))

        # Emotional tone
        tone_guidance = {
            "warm_supportive": "Используй теплый, поддерживающий тон. Валидируй чувства.",
            "energetic_inspiring": "Будь энергичным и вдохновляющим. Мотивируй к действию.",
            "celebrating_curious": "Празднуй успехи. Задавай вопросы из любопытства.",
            "deeply_empathetic": "Проявляй глубокую эмпатию. Создавай безопасное пространство.",
            "reassuring_stable": "Будь спокойным якорем. Предлагай стабильность и предсказуемость.",
            "calm_reflective": "Используй спокойный, рефлексивный тон. Приглашай к самонаблюдению.",
            "warm_validating": "Тепло валидируй опыт. Подчеркивай важность чувств и отношений."
        }
        guidance.append(tone_guidance.get(style["emotional_tone"], ""))

        # Structure
        if style["structure"] == "bullet_points":
            guidance.append("Структурируй ответ четко: используй нумерацию, пункты, шаги.")
        elif style["structure"] == "narrative":
            guidance.append("Используй нарративную форму. Рассказывай истории, создавай образы.")

        # Directiveness
        if style["directiveness"] > 0.7:
            guidance.append("Будь direct и конкретным в рекомендациях. Предлагай четкие шаги.")
        elif style["directiveness"] < 0.3:
            guidance.append("Используй недирективный подход. Задавай вопросы, помогай найти собственные ответы.")

        # Metaphor usage
        if style["metaphor_usage"] == "frequent":
            guidance.append("Активно используй метафоры, аналогии, абстрактные концепции.")
        elif style["metaphor_usage"] == "minimal":
            guidance.append("Избегай метафор. Говори прямо и конкретно.")

        # Question ratio
        if style["question_ratio"] > 0.4:
            guidance.append(f"Используй много вопросов (~{int(style['question_ratio'] * 100)}% текста должны быть вопросы).")
        elif style["question_ratio"] < 0.2:
            guidance.append("Минимизируй вопросы. Фокусируйся на поддержке и информации.")

        return " ".join(guidance)


# === ПРИМЕР ИСПОЛЬЗОВАНИЯ ===

if __name__ == "__main__":
    user_context = {
        'personality_profile': {
            'traits': {
                'big_five': {
                    'openness': 0.85,
                    'conscientiousness': 0.72,
                    'extraversion': 0.45,
                    'agreeableness': 0.79,
                    'neuroticism': 0.34
                }
            }
        },
        'current_mood': 'neutral',
        'conversation_stage': 'deep_coaching'
    }

    styler = AdaptiveCommunicationStyle()
    style = styler.determine_style(user_context)

    print("=== ОПРЕДЕЛЕННЫЙ СТИЛЬ ===")
    for key, value in style.items():
        print(f"{key}: {value}")

    print("\n=== ИНСТРУКЦИИ ДЛЯ AI ===")
    print(styler.get_style_guidance_for_ai(style))

    print("\n=== ФОРМАТИРОВАННЫЙ ОТВЕТ ===")
    sample_response = "Я вижу, что вы ищете баланс между творчеством и структурой."
    formatted = styler.format_response(sample_response, style)
    print(formatted)
