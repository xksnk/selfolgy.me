"""
Breakthrough Detector - Детектор терапевтических прорывов

🎯 ЦЕЛЬ: Обнаружить моменты инсайта и трансформации
📚 ОСНОВА: Multi-indicator approach (Kazdin, Norcross)
🎯 TARGET: F1 = 0.88
⚡ ИНДИКАТОРЫ: Insight, Emotional Release, Belief Shift, Defense Lowering
"""

import re
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class DetectedBreakthrough:
    """Обнаруженный прорыв"""
    breakthrough_type: str  # insight, emotional_release, belief_shift, defense_lowering, integration
    intensity: float  # 0.0 - 1.0
    confidence: float  # 0.0 - 1.0
    evidence: List[str]  # Фразы из текста
    description: str
    therapeutic_response: str  # Как поддержать этот прорыв


class BreakthroughDetector:
    """
    Детектор терапевтических прорывов

    5 типов прорывов:
    1. INSIGHT - новое понимание себя или ситуации
    2. EMOTIONAL_RELEASE - катарсис, выражение сдерживаемых эмоций
    3. BELIEF_SHIFT - изменение глубинного убеждения
    4. DEFENSE_LOWERING - снижение защит, открытость
    5. INTEGRATION - объединение разрозненных частей опыта

    Каждый тип требует специфической поддержки для закрепления.
    """

    # === ИНДИКАТОРЫ ИНСАЙТА (Insight) ===
    INSIGHT_INDICATORS = {
        "aha_moment": {
            "patterns": [
                r"\bвдруг\s+(?:понял|осознал|увидел)\b",
                r"\bтеперь\s+(?:понимаю|вижу|ясно)\b",
                r"\bоказывается\b",
                r"\bвот\s+оно\s+что\b",
                r"\bвот\s+почему\b"
            ],
            "weight": 0.3
        },
        "connection_making": {
            "patterns": [
                r"\bэто\s+связано\s+с\b",
                r"\bпоэтому\s+я\b",
                r"\bвот\s+откуда\b",
                r"\bтеперь\s+понятно,?\s+почему\b",
                r"\bвсё\s+(?:сходится|встаёт\s+на\s+места)\b"
            ],
            "weight": 0.25
        },
        "self_discovery": {
            "patterns": [
                r"\bя\s+(?:никогда\s+)?не\s+(?:думал|замечал|понимал)\b.*\bраньше\b",
                r"\bоткрытие\s+для\s+меня\b",
                r"\bпервый\s+раз\s+(?:понимаю|осознаю|вижу)\b"
            ],
            "weight": 0.25
        },
        "pattern_recognition": {
            "patterns": [
                r"\bвсегда\s+так\s+делаю\b",
                r"\bэто\s+мой\s+паттерн\b",
                r"\bповторяется\b",
                r"\bкак\s+и\s+(?:раньше|тогда|в\s+детстве)\b"
            ],
            "weight": 0.2
        }
    }

    # === ИНДИКАТОРЫ ЭМОЦИОНАЛЬНОГО РЕЛИЗА (Emotional Release) ===
    EMOTIONAL_RELEASE_INDICATORS = {
        "intense_emotion": {
            "patterns": [
                r"\b(?:плачу|слёзы|рыдаю)\b",
                r"\bне\s+могу\s+(?:сдержать|остановить)\b",
                r"\b(?:накрыло|прорвало|захлестнуло)\b",
                r"\bвпервые\s+(?:плачу|говорю\s+об\s+этом)\b"
            ],
            "weight": 0.35
        },
        "relief_expression": {
            "patterns": [
                r"\bкак\s+(?:гора\s+с\s+плеч|камень\s+с\s+души)\b",
                r"\bлегче\s+стало\b",
                r"\bнаконец-то\s+(?:сказал|выговорился)\b",
                r"\b(?:отпустило|освободился)\b"
            ],
            "weight": 0.3
        },
        "suppressed_content": {
            "patterns": [
                r"\bдолго\s+(?:держал|скрывал|молчал)\b",
                r"\bникому\s+не\s+(?:говорил|рассказывал)\b",
                r"\bвпервые\s+(?:признаюсь|говорю)\b"
            ],
            "weight": 0.2
        },
        "body_sensation": {
            "patterns": [
                r"\bдрожу\b",
                r"\bсердце\s+(?:колотится|бьётся)\b",
                r"\bкомок\s+в\s+горле\b",
                r"\bтяжесть\s+(?:ушла|отпустила)\b"
            ],
            "weight": 0.15
        }
    }

    # === ИНДИКАТОРЫ СДВИГА УБЕЖДЕНИЙ (Belief Shift) ===
    BELIEF_SHIFT_INDICATORS = {
        "perspective_change": {
            "patterns": [
                r"\bтеперь\s+(?:думаю|вижу|понимаю)\s+иначе\b",
                r"\bраньше\s+(?:думал|считал)\b.*\bа\s+теперь\b",
                r"\bизменил(?:ось|ась)?\s+(?:моё\s+)?(?:отношение|мнение|взгляд)\b"
            ],
            "weight": 0.35
        },
        "old_belief_questioning": {
            "patterns": [
                r"\bможет,?\s+это\s+не\s+(?:так|правда)\b",
                r"\bа\s+что\s+если\s+(?:я\s+)?(?:не\s+)?(?:был|была)\s+прав\b",
                r"\bпочему\s+я\s+(?:так\s+)?(?:думал|считал)\b"
            ],
            "weight": 0.25
        },
        "new_possibility": {
            "patterns": [
                r"\bоказывается,?\s+(?:можно|я\s+могу)\b",
                r"\bможет,?\s+(?:я\s+)?заслуживаю\b",
                r"\bимею\s+право\b",
                r"\bэто\s+(?:возможно|реально)\b"
            ],
            "weight": 0.25
        },
        "self_reframing": {
            "patterns": [
                r"\bя\s+не\s+(?:плохой|виноват|ничтожный)\b",
                r"\bэто\s+не\s+(?:моя\s+)?вина\b",
                r"\bя\s+(?:достоин|заслуживаю|способен)\b"
            ],
            "weight": 0.15
        }
    }

    # === ИНДИКАТОРЫ СНИЖЕНИЯ ЗАЩИТ (Defense Lowering) ===
    DEFENSE_LOWERING_INDICATORS = {
        "vulnerability": {
            "patterns": [
                r"\bпризнаюсь\b",
                r"\bстрашно\s+(?:говорить|признаться)\b",
                r"\bникому\s+не\s+показывал\b",
                r"\bоткрываюсь\b"
            ],
            "weight": 0.3
        },
        "honesty": {
            "patterns": [
                r"\bесли\s+честно\b",
                r"\bна\s+самом\s+деле\b",
                r"\bправда\s+в\s+том\b",
                r"\bбуду\s+честен\b"
            ],
            "weight": 0.25
        },
        "ownership": {
            "patterns": [
                r"\bэто\s+(?:я|моя)\b.*\b(?:вина|ответственность)\b",
                r"\bпризнаю,?\s+что\b",
                r"\bне\s+буду\s+(?:оправдываться|отрицать)\b"
            ],
            "weight": 0.25
        },
        "trust_expression": {
            "patterns": [
                r"\bдоверяю\s+тебе\b",
                r"\bмогу\s+(?:сказать|рассказать)\b",
                r"\bчувствую\s+себя\s+(?:в\s+)?безопасно(?:сти)?\b"
            ],
            "weight": 0.2
        }
    }

    # === ИНДИКАТОРЫ ИНТЕГРАЦИИ (Integration) ===
    INTEGRATION_INDICATORS = {
        "wholeness": {
            "patterns": [
                r"\bчасть\s+меня\b.*\bпринимаю\b",
                r"\bвсё\s+(?:это|вместе)\s+(?:имеет\s+смысл|складывается)\b",
                r"\bпринимаю\s+(?:себя|это)\b"
            ],
            "weight": 0.35
        },
        "reconciliation": {
            "patterns": [
                r"\bмогу\s+(?:принять|простить)\b",
                r"\bбольше\s+не\s+(?:злюсь|обижаюсь)\b",
                r"\bотпускаю\b"
            ],
            "weight": 0.3
        },
        "meaning_making": {
            "patterns": [
                r"\bтеперь\s+(?:это\s+)?имеет\s+смысл\b",
                r"\bвсё\s+(?:было\s+)?не\s+зря\b",
                r"\bблагодарен\s+за\s+этот\s+опыт\b"
            ],
            "weight": 0.2
        },
        "future_orientation": {
            "patterns": [
                r"\bтеперь\s+(?:я\s+)?(?:могу|смогу|готов)\b",
                r"\bхочу\s+(?:по-другому|иначе)\b",
                r"\bбуду\s+(?:работать|стараться)\b"
            ],
            "weight": 0.15
        }
    }

    # Терапевтические ответы на прорывы
    THERAPEUTIC_RESPONSES = {
        "insight": "Это очень важное осознание. Дайте себе время прочувствовать это понимание и то, как оно меняет вашу картину.",
        "emotional_release": "Спасибо, что доверились и позволили себе это выразить. Эти чувства важны и имеют право быть.",
        "belief_shift": "Это значительный сдвиг в вашем восприятии. Как это новое понимание меняет ваше отношение к себе?",
        "defense_lowering": "Я ценю вашу открытость и честность. Требуется мужество, чтобы быть настолько уязвимым.",
        "integration": "Вы собираете воедино важные части своего опыта. Это путь к целостности и принятию себя."
    }

    def __init__(self):
        """Инициализация детектора прорывов"""
        self.all_indicators = {
            "insight": self.INSIGHT_INDICATORS,
            "emotional_release": self.EMOTIONAL_RELEASE_INDICATORS,
            "belief_shift": self.BELIEF_SHIFT_INDICATORS,
            "defense_lowering": self.DEFENSE_LOWERING_INDICATORS,
            "integration": self.INTEGRATION_INDICATORS
        }
        logger.info("✅ BreakthroughDetector initialized")

    def detect(self, text: str) -> List[DetectedBreakthrough]:
        """
        Обнаружить терапевтические прорывы в тексте

        Args:
            text: Текст для анализа

        Returns:
            Список обнаруженных прорывов
        """
        if not text or len(text) < 20:
            return []

        text_lower = text.lower()
        detected = []

        for breakthrough_type, indicators in self.all_indicators.items():
            score = 0.0
            evidence = []

            for indicator_name, indicator_data in indicators.items():
                for pattern in indicator_data["patterns"]:
                    match = re.search(pattern, text_lower, re.IGNORECASE)
                    if match:
                        score += indicator_data["weight"]
                        # Extract context around match
                        start = max(0, match.start() - 30)
                        end = min(len(text), match.end() + 30)
                        evidence.append(text[start:end].strip())
                        break

            # Threshold for detection
            if score >= 0.3:
                # Intensity based on score and text length
                intensity = min(1.0, score + (len(text) / 500) * 0.2)
                confidence = min(1.0, score * 1.5)

                detected.append(DetectedBreakthrough(
                    breakthrough_type=breakthrough_type,
                    intensity=round(intensity, 3),
                    confidence=round(confidence, 3),
                    evidence=evidence[:3],  # Top 3 evidence
                    description=self._get_description(breakthrough_type),
                    therapeutic_response=self.THERAPEUTIC_RESPONSES[breakthrough_type]
                ))

        # Sort by intensity
        detected.sort(key=lambda x: x.intensity, reverse=True)

        if detected:
            logger.info(f"🌟 Detected {len(detected)} breakthroughs: {[b.breakthrough_type for b in detected]}")

        return detected

    def _get_description(self, breakthrough_type: str) -> str:
        """Получить описание типа прорыва"""
        descriptions = {
            "insight": "Момент нового понимания и осознания",
            "emotional_release": "Катарсис, выражение сдерживаемых эмоций",
            "belief_shift": "Изменение глубинного убеждения о себе или мире",
            "defense_lowering": "Снижение защит, открытость и уязвимость",
            "integration": "Объединение разрозненных частей опыта в целое"
        }
        return descriptions.get(breakthrough_type, "Терапевтический прорыв")

    def get_celebration_response(self, breakthroughs: List[DetectedBreakthrough]) -> Optional[str]:
        """
        Получить поддерживающий ответ для закрепления прорыва

        Args:
            breakthroughs: Обнаруженные прорывы

        Returns:
            Терапевтический ответ или None
        """
        if not breakthroughs:
            return None

        # Берём самый интенсивный прорыв
        top_breakthrough = max(breakthroughs, key=lambda x: x.intensity)

        return f"🌟 {top_breakthrough.therapeutic_response}"

    def format_for_storage(self, breakthroughs: List[DetectedBreakthrough]) -> List[Dict[str, Any]]:
        """Форматировать прорывы для хранения в БД"""
        return [
            {
                "breakthrough_type": b.breakthrough_type,
                "intensity": b.intensity,
                "confidence": b.confidence,
                "evidence": b.evidence,
                "description": b.description,
                "timestamp": datetime.now().isoformat()
            }
            for b in breakthroughs
        ]


# Singleton instance
_breakthrough_detector = None


def get_breakthrough_detector() -> BreakthroughDetector:
    """Получить singleton экземпляр детектора прорывов"""
    global _breakthrough_detector
    if _breakthrough_detector is None:
        _breakthrough_detector = BreakthroughDetector()
    return _breakthrough_detector


# === ТЕСТИРОВАНИЕ ===
if __name__ == "__main__":
    detector = BreakthroughDetector()

    test_texts = [
        # Insight
        "Вдруг понял, почему я всегда так делаю! Это связано с детством, теперь всё сходится. Вот откуда этот страх.",

        # Emotional Release
        "Плачу, не могу сдержать слёзы. Никому не рассказывала об этом раньше. Как камень с души, наконец-то выговорилась.",

        # Belief Shift
        "Раньше думала, что я ничего не заслуживаю. А теперь понимаю иначе. Может, я имею право на счастье. Оказывается, можно жить по-другому.",

        # Defense Lowering
        "Признаюсь, страшно это говорить. На самом деле я боюсь. Буду честен - доверяю тебе, поэтому открываюсь.",

        # Integration
        "Теперь всё это имеет смысл. Принимаю эту часть себя. Могу простить и отпустить. Благодарен за этот опыт."
    ]

    print("🌟 BREAKTHROUGH DETECTOR TEST\n" + "=" * 50)

    for text in test_texts:
        print(f"\n📝 Text: {text[:60]}...")
        breakthroughs = detector.detect(text)

        if breakthroughs:
            for b in breakthroughs:
                print(f"   ⭐ {b.breakthrough_type} (intensity: {b.intensity:.2f}, conf: {b.confidence:.2f})")
                print(f"      {b.description}")

            response = detector.get_celebration_response(breakthroughs)
            if response:
                print(f"   💬 {response}")
        else:
            print("   No breakthroughs detected")

    print("\n" + "=" * 50)
    print("✅ Test completed!")
