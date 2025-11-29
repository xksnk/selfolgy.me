"""
Attachment Style Classifier - Классификатор типов привязанности

🎯 ЦЕЛЬ: Определить тип привязанности пользователя
📚 ОСНОВА: Bowlby, Ainsworth, Bartholomew & Horowitz
🔬 ТИПЫ: Secure, Anxious, Avoidant, Disorganized
⚠️ ТОЧНОСТЬ: Target 84% (требует накопления данных)
"""

import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class AttachmentAssessment:
    """Оценка типа привязанности"""
    primary_style: str  # secure, anxious, avoidant, disorganized
    confidence: float  # 0.0 - 1.0
    style_scores: Dict[str, float]  # Scores for each style
    evidence: List[str]  # Supporting evidence from text
    anxiety_dimension: float  # -1.0 (low) to 1.0 (high)
    avoidance_dimension: float  # -1.0 (low) to 1.0 (high)
    timestamp: str


class AttachmentStyleClassifier:
    """
    Классификатор типов привязанности

    Двумерная модель (Brennan, Clark, Shaver):
    - Anxiety: страх отвержения, нужда в близости
    - Avoidance: дискомфорт от близости, самодостаточность

    4 типа (Bartholomew & Horowitz):
    - SECURE: Low Anxiety, Low Avoidance
    - ANXIOUS (Preoccupied): High Anxiety, Low Avoidance
    - AVOIDANT (Dismissive): Low Anxiety, High Avoidance
    - DISORGANIZED (Fearful): High Anxiety, High Avoidance
    """

    # === ИНДИКАТОРЫ ТРЕВОГИ ПРИВЯЗАННОСТИ (Anxiety) ===
    ANXIETY_INDICATORS = {
        "fear_of_abandonment": {
            "patterns": [
                r"\bбоюсь,?\s+что\s+(?:бросят|уйдут|оставят)\b",
                r"\bстрашно\s+(?:потерять|остаться\s+одному)\b",
                r"\bне\s+могу\s+без\s+(?:него|неё|них)\b",
                r"\bчто\s+если\s+(?:уйдёт|бросит|разлюбит)\b"
            ],
            "weight": 0.3
        },
        "need_for_reassurance": {
            "patterns": [
                r"\b(?:любишь|любит)\s+(?:ли|меня)\b",
                r"\bне\s+(?:разонравилась?|надоела?)\b",
                r"\bточно\s+(?:всё\s+хорошо|не\s+злишься)\b",
                r"\bпочему\s+(?:не\s+)?(?:написал|позвонил|ответил)\b"
            ],
            "weight": 0.25
        },
        "jealousy_possessiveness": {
            "patterns": [
                r"\bревную\b",
                r"\bс\s+кем\s+(?:был|была|общался)\b",
                r"\bпочему\s+(?:улыбался|смотрел)\s+на\b",
                r"\bне\s+нравится,?\s+когда\s+(?:общается|разговаривает)\b"
            ],
            "weight": 0.2
        },
        "hypervigilance": {
            "patterns": [
                r"\bзаметила?,?\s+что\s+(?:изменился|отдалился)\b",
                r"\bчувствую,?\s+что\s+(?:что-то\s+не\s+так|скрывает)\b",
                r"\bпостоянно\s+(?:думаю|переживаю)\b",
                r"\bне\s+могу\s+успокоиться\b"
            ],
            "weight": 0.15
        },
        "merger_wishes": {
            "patterns": [
                r"\bхочу\s+быть\s+(?:всегда\s+)?(?:рядом|вместе)\b",
                r"\bне\s+представляю\s+(?:жизни|себя)\s+без\b",
                r"\bмы\s+(?:как\s+)?одно\s+целое\b"
            ],
            "weight": 0.1
        }
    }

    # === ИНДИКАТОРЫ ИЗБЕГАНИЯ (Avoidance) ===
    AVOIDANCE_INDICATORS = {
        "discomfort_with_closeness": {
            "patterns": [
                r"\bслишком\s+(?:близко|навязчиво|много)\b",
                r"\bнужно\s+(?:личное\s+)?пространство\b",
                r"\bдушит\b",
                r"\bне\s+люблю,?\s+когда\s+(?:лезут|пристают)\b"
            ],
            "weight": 0.3
        },
        "self_sufficiency": {
            "patterns": [
                r"\bсправлюсь\s+сам[аи]?\b",
                r"\bне\s+нуждаюсь\s+в\b",
                r"\bлучше\s+(?:один|одна)\b",
                r"\bникому\s+не\s+(?:нужен|должен)\b"
            ],
            "weight": 0.25
        },
        "emotional_distance": {
            "patterns": [
                r"\bне\s+люблю\s+(?:говорить\s+о\s+)?чувствах\b",
                r"\bзачем\s+(?:это\s+)?обсуждать\b",
                r"\bне\s+вижу\s+смысла\s+в\b",
                r"\b(?:эмоции|чувства)\s+(?:мешают|лишнее)\b"
            ],
            "weight": 0.2
        },
        "commitment_fear": {
            "patterns": [
                r"\bне\s+готов[аы]?\s+к\s+(?:серьёзным|отношениям)\b",
                r"\bне\s+хочу\s+(?:привязываться|обязательств)\b",
                r"\bсвобода\s+важнее\b",
                r"\bне\s+люблю\s+(?:планировать|обещать)\b"
            ],
            "weight": 0.15
        },
        "independence_emphasis": {
            "patterns": [
                r"\bсамостоятельност(?:ь|и)\b",
                r"\bсвоя\s+жизнь\b",
                r"\bне\s+хочу\s+зависеть\b",
                r"\bкаждый\s+сам\s+за\s+себя\b"
            ],
            "weight": 0.1
        }
    }

    # === ИНДИКАТОРЫ НАДЁЖНОЙ ПРИВЯЗАННОСТИ (Secure) ===
    SECURE_INDICATORS = {
        "comfort_with_intimacy": {
            "patterns": [
                r"\bлюблю\s+(?:быть\s+)?(?:близко|рядом)\b",
                r"\bчувствую\s+себя\s+(?:комфортно|спокойно)\b",
                r"\bдоверяю\b",
                r"\bможем\s+(?:поговорить|обсудить)\b"
            ],
            "weight": 0.3
        },
        "healthy_boundaries": {
            "patterns": [
                r"\bуважаю\s+(?:его|её|их)\s+(?:границы|пространство)\b",
                r"\bкаждому\s+нужно\s+(?:время|пространство)\b",
                r"\bбаланс\b"
            ],
            "weight": 0.25
        },
        "emotional_availability": {
            "patterns": [
                r"\bготов[аы]?\s+(?:поддержать|помочь|выслушать)\b",
                r"\bмогу\s+(?:поделиться|рассказать)\b",
                r"\bоткрыт[аы]?\b"
            ],
            "weight": 0.2
        },
        "relationship_security": {
            "patterns": [
                r"\bуверен[аы]?\s+в\s+(?:нас|отношениях|нём|ней)\b",
                r"\bзнаю,?\s+что\s+(?:любит|поддержит|будет\s+рядом)\b",
                r"\bстабильн(?:ые|ость)\b"
            ],
            "weight": 0.15
        },
        "conflict_resolution": {
            "patterns": [
                r"\bможем\s+(?:решить|обсудить|договориться)\b",
                r"\bкомпромисс\b",
                r"\bважно\s+(?:слышать|понимать)\s+друг\s+друга\b"
            ],
            "weight": 0.1
        }
    }

    def __init__(self):
        """Инициализация классификатора"""
        # История оценок по пользователям
        self.assessment_history: Dict[int, List[AttachmentAssessment]] = {}
        logger.info("✅ AttachmentStyleClassifier initialized")

    def assess(
        self,
        user_id: int,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AttachmentAssessment:
        """
        Оценить тип привязанности на основе текста

        Args:
            user_id: ID пользователя
            text: Текст для анализа
            context: Дополнительный контекст

        Returns:
            AttachmentAssessment с типом и scores
        """
        text_lower = text.lower()

        # 1. Вычисляем dimensions
        anxiety_score, anxiety_evidence = self._calculate_dimension(text_lower, self.ANXIETY_INDICATORS)
        avoidance_score, avoidance_evidence = self._calculate_dimension(text_lower, self.AVOIDANCE_INDICATORS)
        secure_score, secure_evidence = self._calculate_dimension(text_lower, self.SECURE_INDICATORS)

        # 2. Корректируем на secure indicators
        if secure_score > 0.3:
            anxiety_score -= secure_score * 0.5
            avoidance_score -= secure_score * 0.5

        # 3. Нормализуем в [-1, 1]
        anxiety_dim = max(-1.0, min(1.0, anxiety_score))
        avoidance_dim = max(-1.0, min(1.0, avoidance_score))

        # 4. Определяем style scores
        style_scores = self._calculate_style_scores(anxiety_dim, avoidance_dim, secure_score)

        # 5. Определяем primary style
        primary_style = max(style_scores.items(), key=lambda x: x[1])[0]
        confidence = style_scores[primary_style]

        # 6. Собираем evidence
        all_evidence = anxiety_evidence + avoidance_evidence + secure_evidence

        # 7. Учитываем историю (EMA smoothing)
        if user_id in self.assessment_history and len(self.assessment_history[user_id]) > 0:
            prev = self.assessment_history[user_id][-1]
            alpha = 0.4  # Вес нового измерения
            for style in style_scores:
                style_scores[style] = alpha * style_scores[style] + (1 - alpha) * prev.style_scores.get(style, 0.5)

            # Пересчитываем primary style после smoothing
            primary_style = max(style_scores.items(), key=lambda x: x[1])[0]
            confidence = style_scores[primary_style]

        # 8. Создаём assessment
        assessment = AttachmentAssessment(
            primary_style=primary_style,
            confidence=round(confidence, 3),
            style_scores={k: round(v, 3) for k, v in style_scores.items()},
            evidence=all_evidence[:5],  # Top 5 evidence
            anxiety_dimension=round(anxiety_dim, 3),
            avoidance_dimension=round(avoidance_dim, 3),
            timestamp=datetime.now().isoformat()
        )

        # 9. Сохраняем в историю
        if user_id not in self.assessment_history:
            self.assessment_history[user_id] = []
        self.assessment_history[user_id].append(assessment)

        # Ограничиваем историю
        if len(self.assessment_history[user_id]) > 50:
            self.assessment_history[user_id] = self.assessment_history[user_id][-50:]

        logger.debug(f"Attachment assessment for user {user_id}: {primary_style} ({confidence:.2f})")

        return assessment

    def _calculate_dimension(
        self,
        text: str,
        indicators: Dict
    ) -> Tuple[float, List[str]]:
        """Вычислить score для dimension"""
        total_score = 0.0
        evidence = []

        for indicator_name, indicator_data in indicators.items():
            for pattern in indicator_data["patterns"]:
                if re.search(pattern, text, re.IGNORECASE):
                    total_score += indicator_data["weight"]
                    evidence.append(indicator_name)
                    break

        return total_score, evidence

    def _calculate_style_scores(
        self,
        anxiety: float,
        avoidance: float,
        secure: float
    ) -> Dict[str, float]:
        """
        Вычислить scores для каждого стиля привязанности

        Quadrant model:
        - Secure: Low Anxiety, Low Avoidance
        - Anxious: High Anxiety, Low Avoidance
        - Avoidant: Low Anxiety, High Avoidance
        - Disorganized: High Anxiety, High Avoidance
        """
        scores = {}

        # Secure: противоположность обоим dimensions + secure indicators
        scores["secure"] = max(0.1, (1 - abs(anxiety)) * (1 - abs(avoidance)) * 0.5 + secure * 0.5)

        # Anxious: high anxiety, low avoidance
        scores["anxious"] = max(0.1, (anxiety + 1) / 2 * (1 - (avoidance + 1) / 2))

        # Avoidant: low anxiety, high avoidance
        scores["avoidant"] = max(0.1, (1 - (anxiety + 1) / 2) * (avoidance + 1) / 2)

        # Disorganized: high both
        scores["disorganized"] = max(0.1, (anxiety + 1) / 2 * (avoidance + 1) / 2)

        # Normalize to sum to 1
        total = sum(scores.values())
        if total > 0:
            scores = {k: v / total for k, v in scores.items()}

        return scores

    def get_current_style(self, user_id: int) -> Tuple[str, float]:
        """
        Получить текущий тип привязанности

        Returns:
            (style, confidence)
        """
        if user_id not in self.assessment_history or len(self.assessment_history[user_id]) == 0:
            return "unknown", 0.0

        latest = self.assessment_history[user_id][-1]
        return latest.primary_style, latest.confidence

    def get_style_description(self, style: str) -> str:
        """Получить описание типа привязанности"""
        descriptions = {
            "secure": "Надёжная привязанность: комфорт с близостью и автономией, доверие к себе и другим",
            "anxious": "Тревожная привязанность: страх отвержения, потребность в подтверждении, склонность к слиянию",
            "avoidant": "Избегающая привязанность: дискомфорт с близостью, ценность независимости, эмоциональная дистанция",
            "disorganized": "Дезорганизованная привязанность: смешение тревоги и избегания, страх отношений и желание близости"
        }
        return descriptions.get(style, "Тип привязанности не определён")

    def format_for_storage(self, assessment: AttachmentAssessment) -> Dict[str, Any]:
        """Форматировать для хранения в БД"""
        return {
            "primary_style": assessment.primary_style,
            "confidence": assessment.confidence,
            "style_scores": assessment.style_scores,
            "evidence": assessment.evidence,
            "anxiety_dimension": assessment.anxiety_dimension,
            "avoidance_dimension": assessment.avoidance_dimension,
            "timestamp": assessment.timestamp
        }


# Singleton instance
_attachment_classifier = None


def get_attachment_classifier() -> AttachmentStyleClassifier:
    """Получить singleton экземпляр классификатора"""
    global _attachment_classifier
    if _attachment_classifier is None:
        _attachment_classifier = AttachmentStyleClassifier()
    return _attachment_classifier


# === ТЕСТИРОВАНИЕ ===
if __name__ == "__main__":
    classifier = AttachmentStyleClassifier()

    test_texts = [
        # Secure
        ("Люблю быть рядом с близкими, но уважаю их пространство. Доверяю партнёру, знаю что он меня любит. Если возникают проблемы, можем спокойно обсудить.", "secure"),

        # Anxious
        ("Боюсь, что он меня бросит. Постоянно думаю, любит ли он меня. Ревную когда он общается с другими. Не могу без него, мы как одно целое.", "anxious"),

        # Avoidant
        ("Лучше одна. Не люблю когда лезут в душу, зачем это обсуждать? Справлюсь сама, не нуждаюсь в помощи. Свобода важнее всего.", "avoidant"),

        # Disorganized
        ("Боюсь остаться одна, но когда он рядом - душит. Хочу близости, но не могу довериться. Он точно меня бросит, но без него не могу.", "disorganized")
    ]

    print("💜 ATTACHMENT STYLE CLASSIFIER TEST\n" + "=" * 50)

    user_id = 456

    for text, expected in test_texts:
        print(f"\n📝 Expected: {expected}")
        print(f"   Text: {text[:60]}...")

        assessment = classifier.assess(user_id, text)

        emoji = "✅" if assessment.primary_style == expected else "⚠️"
        print(f"   {emoji} Result: {assessment.primary_style} ({assessment.confidence:.2f})")
        print(f"   Scores: {assessment.style_scores}")
        print(f"   Dimensions: Anx={assessment.anxiety_dimension:.2f}, Avoid={assessment.avoidance_dimension:.2f}")
        if assessment.evidence:
            print(f"   Evidence: {', '.join(assessment.evidence[:3])}")

    print("\n" + "=" * 50)
    style, conf = classifier.get_current_style(user_id)
    print(f"📊 Final style: {style} ({conf:.2f})")
    print(f"   {classifier.get_style_description(style)}")
    print("✅ Test completed!")
