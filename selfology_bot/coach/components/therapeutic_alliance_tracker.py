"""
Therapeutic Alliance Tracker - Трекер терапевтического альянса

🎯 ЦЕЛЬ: Измерять качество рабочих отношений между AI-коучем и пользователем
📚 ОСНОВА: Working Alliance Inventory (WAI-SR) - Bordin (1979), Horvath & Greenberg
⚙️ КОМПОНЕНТЫ: Bond (связь), Task (задачи), Goal (цели)
🔒 GATING: Alliance > 0.6 для глубоких интервенций, > 0.7 для слепых зон
"""

import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class AllianceMeasurement:
    """Измерение терапевтического альянса"""
    overall_score: float  # 0.0 - 1.0
    bond_score: float  # Эмоциональная связь и доверие
    task_score: float  # Согласие по задачам сессии
    goal_score: float  # Общее понимание целей
    engagement_level: float  # Уровень вовлечённости
    disclosure_depth: float  # Глубина самораскрытия
    trust_indicators: List[str]  # Обнаруженные индикаторы доверия
    resistance_indicators: List[str]  # Обнаруженные индикаторы сопротивления
    timestamp: str


class TherapeuticAllianceTracker:
    """
    Трекер терапевтического альянса на основе WAI-SR

    Три компонента альянса:
    1. BOND - эмоциональная связь, доверие, принятие
    2. TASK - согласие по методам и задачам работы
    3. GOAL - общее понимание целей терапии

    Индикаторы:
    - Позитивные: благодарность, самораскрытие, follow-up вопросы
    - Негативные: сопротивление, формальность, избегание
    """

    # === ИНДИКАТОРЫ ДОВЕРИЯ (BOND) ===
    TRUST_INDICATORS = {
        "gratitude": {
            "patterns": [
                r"\bспасибо\b",
                r"\bблагодар(?:ю|ен|на|ны)\b",
                r"\bпомогло\b",
                r"\bценю\s+(?:это|твою|вашу)\b"
            ],
            "weight": 0.15,
            "component": "bond"
        },
        "personal_disclosure": {
            "patterns": [
                r"\bникому\s+не\s+(?:говорил|рассказывал)\b",
                r"\bвпервые\s+(?:говорю|признаюсь)\b",
                r"\bоткровенно\s+говоря\b",
                r"\bесли\s+честно\b",
                r"\bпризнаюсь\b"
            ],
            "weight": 0.2,
            "component": "bond"
        },
        "emotional_expression": {
            "patterns": [
                r"\b(?:чувствую|ощущаю)\s+(?:что|как|себя)\b",
                r"\bмне\s+(?:тяжело|больно|грустно|страшно)\b",
                r"\bпереживаю\b",
                r"\bволнует\b"
            ],
            "weight": 0.15,
            "component": "bond"
        },
        "collaborative_language": {
            "patterns": [
                r"\bмы\s+(?:с\s+тобой|вместе)\b",
                r"\bнаша\s+(?:работа|беседа)\b",
                r"\bдавай(?:те)?\s+попробуем\b",
                r"\bможем\s+(?:вместе|попробовать)\b"
            ],
            "weight": 0.1,
            "component": "task"
        },
        "follow_up": {
            "patterns": [
                r"\bа\s+(?:что|как|почему)\s+(?:если|ты|вы)\b",
                r"\bможно\s+(?:ещё|подробнее)\b",
                r"\bрасскажи(?:те)?\s+(?:больше|подробнее)\b",
                r"\bинтересно\b"
            ],
            "weight": 0.1,
            "component": "goal"
        },
        "agreement": {
            "patterns": [
                r"\bсогласен\b",
                r"\bименно\s+так\b",
                r"\bточно\b",
                r"\bда,?\s+это\s+(?:правда|так)\b",
                r"\bты\s+прав[аы]?\b"
            ],
            "weight": 0.1,
            "component": "task"
        },
        "insight_acknowledgment": {
            "patterns": [
                r"\bне\s+думал[аи]?\s+об\s+этом\s+(?:так|раньше)\b",
                r"\bинтересная\s+мысль\b",
                r"\bзаставило\s+задуматься\b",
                r"\bоткрытие\b"
            ],
            "weight": 0.15,
            "component": "goal"
        }
    }

    # === ИНДИКАТОРЫ СОПРОТИВЛЕНИЯ ===
    RESISTANCE_INDICATORS = {
        "dismissal": {
            "patterns": [
                r"\bэто\s+(?:глупость|ерунда|не\s+работает)\b",
                r"\bне\s+(?:понимаю|верю|согласен)\b",
                r"\bзачем\s+это\b",
                r"\bне\s+вижу\s+смысла\b"
            ],
            "weight": -0.15,
            "component": "task"
        },
        "avoidance": {
            "patterns": [
                r"\bне\s+хочу\s+(?:об\s+этом|говорить)\b",
                r"\bдавайте\s+(?:о\s+другом|сменим)\b",
                r"\bпропустим\b",
                r"\bне\s+готов[аы]?\b"
            ],
            "weight": -0.1,
            "component": "bond"
        },
        "minimal_response": {
            "patterns": [
                r"^(?:да|нет|ок|ладно|понятно|хорошо)\.?$",
                r"^(?:не\s+знаю)\.?$",
                r"^(?:может\s+быть)\.?$"
            ],
            "weight": -0.1,
            "component": "bond"
        },
        "hostility": {
            "patterns": [
                r"\bты\s+(?:не\s+понимаешь|не\s+прав)\b",
                r"\bхватит\b",
                r"\bнадоело\b",
                r"\bоставь(?:те)?\s+меня\b"
            ],
            "weight": -0.2,
            "component": "bond"
        },
        "formality": {
            "patterns": [
                r"\bс\s+уважением\b",
                r"\bблагодарю\s+за\s+(?:внимание|ответ)\b",
                r"\bждём?\s+(?:вашего|вашей)\b"
            ],
            "weight": -0.05,
            "component": "bond"
        }
    }

    def __init__(self):
        """Инициализация трекера альянса"""
        # История измерений по пользователям
        self.alliance_history: Dict[int, List[AllianceMeasurement]] = {}

        # Базовые весы компонентов (можно тюнить)
        self.component_weights = {
            "bond": 0.4,  # Самый важный для терапии
            "task": 0.3,
            "goal": 0.3
        }

        logger.info("✅ TherapeuticAllianceTracker initialized")

    def measure(
        self,
        user_id: int,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AllianceMeasurement:
        """
        Измерить текущий уровень терапевтического альянса

        Args:
            user_id: ID пользователя
            message: Текст сообщения пользователя
            context: Дополнительный контекст (response_time, message_count, etc.)

        Returns:
            AllianceMeasurement с scores и индикаторами
        """
        context = context or {}
        message_lower = message.lower()

        # 1. Обнаруживаем индикаторы
        trust_found = []
        resistance_found = []
        component_scores = {"bond": 0.5, "task": 0.5, "goal": 0.5}  # Базовые scores

        # Проверяем индикаторы доверия
        for indicator_name, indicator_data in self.TRUST_INDICATORS.items():
            for pattern in indicator_data["patterns"]:
                if re.search(pattern, message_lower, re.IGNORECASE):
                    trust_found.append(indicator_name)
                    component = indicator_data["component"]
                    component_scores[component] += indicator_data["weight"]
                    break

        # Проверяем индикаторы сопротивления
        for indicator_name, indicator_data in self.RESISTANCE_INDICATORS.items():
            for pattern in indicator_data["patterns"]:
                if re.search(pattern, message_lower, re.IGNORECASE):
                    resistance_found.append(indicator_name)
                    component = indicator_data["component"]
                    component_scores[component] += indicator_data["weight"]
                    break

        # 2. Анализируем engagement по мета-факторам
        engagement_level = self._calculate_engagement(message, context)
        disclosure_depth = self._calculate_disclosure_depth(message)

        # Корректируем scores на основе engagement
        for component in component_scores:
            component_scores[component] += (engagement_level - 0.5) * 0.2
            component_scores[component] += (disclosure_depth - 0.5) * 0.15

        # 3. Нормализуем scores в [0.0, 1.0]
        for component in component_scores:
            component_scores[component] = max(0.0, min(1.0, component_scores[component]))

        # 4. Учитываем историю (если есть)
        if user_id in self.alliance_history and len(self.alliance_history[user_id]) > 0:
            # Сглаживание с предыдущим измерением (EMA)
            prev = self.alliance_history[user_id][-1]
            alpha = 0.3  # Вес нового измерения
            component_scores["bond"] = alpha * component_scores["bond"] + (1 - alpha) * prev.bond_score
            component_scores["task"] = alpha * component_scores["task"] + (1 - alpha) * prev.task_score
            component_scores["goal"] = alpha * component_scores["goal"] + (1 - alpha) * prev.goal_score

        # 5. Вычисляем overall score
        overall = (
            component_scores["bond"] * self.component_weights["bond"] +
            component_scores["task"] * self.component_weights["task"] +
            component_scores["goal"] * self.component_weights["goal"]
        )

        # 6. Создаём измерение
        measurement = AllianceMeasurement(
            overall_score=round(overall, 3),
            bond_score=round(component_scores["bond"], 3),
            task_score=round(component_scores["task"], 3),
            goal_score=round(component_scores["goal"], 3),
            engagement_level=round(engagement_level, 3),
            disclosure_depth=round(disclosure_depth, 3),
            trust_indicators=trust_found,
            resistance_indicators=resistance_found,
            timestamp=datetime.now().isoformat()
        )

        # 7. Сохраняем в историю
        if user_id not in self.alliance_history:
            self.alliance_history[user_id] = []
        self.alliance_history[user_id].append(measurement)

        # Ограничиваем историю последними 50 измерениями
        if len(self.alliance_history[user_id]) > 50:
            self.alliance_history[user_id] = self.alliance_history[user_id][-50:]

        logger.debug(f"Alliance measured for user {user_id}: {overall:.2f} (B:{component_scores['bond']:.2f}, T:{component_scores['task']:.2f}, G:{component_scores['goal']:.2f})")

        return measurement

    def _calculate_engagement(self, message: str, context: Dict[str, Any]) -> float:
        """
        Расчёт уровня вовлечённости

        Факторы:
        - Длина сообщения
        - Время ответа
        - Вопросы в сообщении
        """
        score = 0.5  # Базовый

        # Длина сообщения
        word_count = len(message.split())
        if word_count > 50:
            score += 0.2
        elif word_count > 20:
            score += 0.1
        elif word_count < 5:
            score -= 0.15

        # Время ответа (если есть)
        response_time = context.get("response_time_seconds", 60)
        if response_time < 30:
            score += 0.1  # Быстрый ответ = вовлечённость
        elif response_time > 180:
            score -= 0.1  # Долгий ответ может быть негативным

        # Вопросы в сообщении
        question_count = message.count("?")
        if question_count > 0:
            score += min(0.15, question_count * 0.05)

        # Восклицания (эмоциональность)
        exclamation_count = message.count("!")
        if exclamation_count > 0:
            score += min(0.1, exclamation_count * 0.03)

        return max(0.0, min(1.0, score))

    def _calculate_disclosure_depth(self, message: str) -> float:
        """
        Расчёт глубины самораскрытия

        Факторы:
        - Личные местоимения
        - Эмоциональные слова
        - Описание чувств и переживаний
        """
        score = 0.5  # Базовый
        message_lower = message.lower()

        # Личные местоимения 1-го лица
        personal_pronouns = len(re.findall(r"\b(?:я|мне|меня|мой|моя|моё|мои)\b", message_lower))
        score += min(0.2, personal_pronouns * 0.02)

        # Эмоциональные слова
        emotional_words = [
            "чувствую", "ощущаю", "переживаю", "волнуюсь", "боюсь",
            "радуюсь", "злюсь", "грущу", "люблю", "ненавижу",
            "больно", "тяжело", "страшно", "одиноко", "счастлив"
        ]
        emotional_count = sum(1 for word in emotional_words if word in message_lower)
        score += min(0.2, emotional_count * 0.05)

        # Прошлое и детство
        past_indicators = ["раньше", "в детстве", "когда был", "помню", "давно"]
        past_count = sum(1 for word in past_indicators if word in message_lower)
        score += min(0.1, past_count * 0.05)

        return max(0.0, min(1.0, score))

    def get_current_alliance(self, user_id: int) -> float:
        """
        Получить текущий уровень альянса для пользователя

        Returns:
            float от 0.0 до 1.0
        """
        if user_id not in self.alliance_history or len(self.alliance_history[user_id]) == 0:
            return 0.3  # Начальный низкий альянс для нового пользователя

        return self.alliance_history[user_id][-1].overall_score

    def get_alliance_trend(self, user_id: int, last_n: int = 5) -> str:
        """
        Определить тренд альянса (растёт/падает/стабильно)

        Args:
            user_id: ID пользователя
            last_n: Количество последних измерений для анализа

        Returns:
            "improving" | "declining" | "stable"
        """
        if user_id not in self.alliance_history:
            return "stable"

        history = self.alliance_history[user_id]
        if len(history) < 3:
            return "stable"

        recent = [m.overall_score for m in history[-last_n:]]

        # Простой линейный тренд
        if len(recent) < 2:
            return "stable"

        first_half = sum(recent[:len(recent)//2]) / (len(recent)//2)
        second_half = sum(recent[len(recent)//2:]) / (len(recent) - len(recent)//2)

        diff = second_half - first_half

        if diff > 0.05:
            return "improving"
        elif diff < -0.05:
            return "declining"
        else:
            return "stable"

    def should_deepen_intervention(self, user_id: int) -> Tuple[bool, str]:
        """
        Определить, можно ли углублять интервенции

        Returns:
            (can_deepen: bool, reason: str)
        """
        alliance = self.get_current_alliance(user_id)
        trend = self.get_alliance_trend(user_id)

        if alliance < 0.4:
            return False, "Альянс слишком низкий (<0.4), фокус на построении доверия"

        if alliance < 0.6 and trend == "declining":
            return False, "Альянс падает, нужно укрепить связь"

        if alliance >= 0.7:
            return True, "Альянс высокий (>0.7), можно работать с глубокими темами"

        if alliance >= 0.6 and trend == "improving":
            return True, "Альянс растёт (>0.6), можно осторожно углублять"

        return False, f"Альянс {alliance:.2f}, тренд {trend} - лучше оставаться на текущей глубине"

    def format_for_storage(self, measurement: AllianceMeasurement) -> Dict[str, Any]:
        """
        Форматировать измерение для хранения в БД
        """
        return {
            "overall_score": measurement.overall_score,
            "bond_score": measurement.bond_score,
            "task_score": measurement.task_score,
            "goal_score": measurement.goal_score,
            "engagement_level": measurement.engagement_level,
            "disclosure_depth": measurement.disclosure_depth,
            "trust_indicators": measurement.trust_indicators,
            "resistance_indicators": measurement.resistance_indicators,
            "timestamp": measurement.timestamp
        }


# Singleton instance
_alliance_tracker = None


def get_alliance_tracker() -> TherapeuticAllianceTracker:
    """Получить singleton экземпляр трекера альянса"""
    global _alliance_tracker
    if _alliance_tracker is None:
        _alliance_tracker = TherapeuticAllianceTracker()
    return _alliance_tracker


# === ТЕСТИРОВАНИЕ ===
if __name__ == "__main__":
    tracker = TherapeuticAllianceTracker()

    test_messages = [
        # Высокий альянс
        ("Спасибо, это действительно помогло! Я впервые признаюсь в этом, но чувствую, что могу тебе доверять.", "high_alliance"),

        # Средний альянс
        ("Интересная мысль, не думал об этом раньше. Может попробуем разобраться вместе?", "medium_alliance"),

        # Низкий альянс
        ("Не знаю.", "low_alliance"),

        # Сопротивление
        ("Это глупость, я не вижу смысла в таких вопросах. Давайте о другом.", "resistance"),

        # Глубокое самораскрытие
        ("Мне тяжело об этом говорить, но в детстве я всегда чувствовал себя одиноким. Помню, как боялся оставаться один, переживал что меня бросят.", "deep_disclosure")
    ]

    print("🤝 THERAPEUTIC ALLIANCE TRACKER TEST\n" + "=" * 50)

    user_id = 123

    for message, expected_type in test_messages:
        print(f"\n📝 Type: {expected_type}")
        print(f"   Message: {message[:60]}...")

        measurement = tracker.measure(user_id, message)

        print(f"   Overall: {measurement.overall_score:.2f}")
        print(f"   Bond: {measurement.bond_score:.2f} | Task: {measurement.task_score:.2f} | Goal: {measurement.goal_score:.2f}")
        print(f"   Engagement: {measurement.engagement_level:.2f} | Disclosure: {measurement.disclosure_depth:.2f}")

        if measurement.trust_indicators:
            print(f"   ✅ Trust: {', '.join(measurement.trust_indicators)}")
        if measurement.resistance_indicators:
            print(f"   ⚠️ Resistance: {', '.join(measurement.resistance_indicators)}")

        can_deepen, reason = tracker.should_deepen_intervention(user_id)
        print(f"   {'✅' if can_deepen else '❌'} Can deepen: {reason}")

    print("\n" + "=" * 50)
    print(f"📈 Final alliance: {tracker.get_current_alliance(user_id):.2f}")
    print(f"📊 Trend: {tracker.get_alliance_trend(user_id)}")
    print("✅ Test completed!")
