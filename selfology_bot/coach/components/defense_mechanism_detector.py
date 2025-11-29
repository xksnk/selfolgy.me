"""
Defense Mechanism Detector - Детектор защитных механизмов

Обнаруживает 12 основных защитных механизмов психики в тексте пользователя.
Защитные механизмы - это бессознательные стратегии избегания тревоги.

Типы механизмов (по Freud, Vaillant):
1. Отрицание (Denial) - отказ признавать реальность
2. Проекция (Projection) - приписывание своих чувств другим
3. Рационализация (Rationalization) - логическое оправдание
4. Интеллектуализация (Intellectualization) - уход в абстракции
5. Замещение (Displacement) - перенос эмоций на безопасную цель
6. Реактивное образование (Reaction Formation) - противоположное поведение
7. Регрессия (Regression) - возврат к детскому поведению
8. Подавление (Repression) - вытеснение из сознания
9. Диссоциация (Dissociation) - отключение от переживаний
10. Соматизация (Somatization) - телесные симптомы вместо эмоций
11. Пассивная агрессия (Passive Aggression) - непрямое выражение гнева
12. Избегание (Avoidance) - уклонение от неприятного
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import re

logger = logging.getLogger(__name__)


@dataclass
class DetectedDefense:
    """Обнаруженный защитный механизм"""
    mechanism_type: str
    maturity_level: str  # "primitive", "neurotic", "mature"
    confidence: float  # 0.0 - 1.0
    evidence: str  # Фраза из текста
    explanation: str  # Объяснение механизма
    awareness_prompt: str  # Мягкий вопрос для осознания


class DefenseMechanismDetector:
    """
    Детектор защитных механизмов психики

    Использует паттерн-матчинг + контекстный анализ
    для обнаружения бессознательных защит
    """

    # Паттерны защитных механизмов на русском языке
    MECHANISM_PATTERNS = {
        "denial": {
            "name": "Отрицание",
            "maturity": "primitive",
            "patterns": [
                r"\bэто\s+неправда\b", r"\bне\s+может\s+быть\b",
                r"\bя\s+не\s+верю\b", r"\bэтого\s+не\s+было\b",
                r"\bне\s+хочу\s+об\s+этом\b", r"\bвсё\s+нормально\b",
                r"\bничего\s+страшного\b", r"\bне\s+проблема\b",
                r"\bне\s+имеет\s+значения\b"
            ],
            "context_indicators": ["но", "хотя", "на самом деле"],
            "explanation": "Вы отказываетесь признавать реальность ситуации",
            "awareness": "Если бы это было правдой - что бы вы чувствовали?"
        },

        "projection": {
            "name": "Проекция",
            "maturity": "primitive",
            "patterns": [
                r"\bон\s+меня\s+ненавидит\b", r"\bона\s+меня\s+осуждает\b",
                r"\bони\s+все\s+против\b", r"\bон\s+злится\b",
                r"\bона\s+думает\s+плохо\b", r"\bвсе\s+меня\s+считают\b",
                r"\bона\s+завидует\b", r"\bон\s+ревнует\b"
            ],
            "context_indicators": ["потому что", "уверен", "знаю"],
            "explanation": "Вы приписываете другим свои собственные чувства",
            "awareness": "А что вы сами чувствуете по отношению к нему/ней?"
        },

        "rationalization": {
            "name": "Рационализация",
            "maturity": "neurotic",
            "patterns": [
                r"\bна\s+самом\s+деле\s+это\s+к\s+лучшему\b",
                r"\bзначит\s+так\s+надо\b", r"\bэто\s+логично\b",
                r"\bвсё\s+равно\s+не\s+хотел\b", r"\bслишком\s+сложно\b",
                r"\bне\s+стоило\s+и\s+пытаться\b",
                r"\bи\s+так\s+бы\s+не\s+получилось\b"
            ],
            "context_indicators": ["поэтому", "следовательно", "значит"],
            "explanation": "Вы находите логичные объяснения для эмоционально сложных решений",
            "awareness": "Какие чувства стоят за этим объяснением?"
        },

        "intellectualization": {
            "name": "Интеллектуализация",
            "maturity": "neurotic",
            "patterns": [
                r"\bс\s+точки\s+зрения\b", r"\bстатистически\b",
                r"\bтеоретически\b", r"\bобъективно\s+говоря\b",
                r"\bесли\s+разобраться\b", r"\bнаучно\s+доказано\b",
                r"\bсогласно\s+\w+\b"
            ],
            "context_indicators": ["анализ", "факты", "данные"],
            "explanation": "Вы уходите в абстрактные рассуждения, избегая чувств",
            "awareness": "Отложим анализ - что вы чувствуете прямо сейчас?"
        },

        "displacement": {
            "name": "Замещение",
            "maturity": "neurotic",
            "patterns": [
                r"\bбесит\b.*\b(?:кот|собака|муж|жена|ребёнок)\b",
                r"\bсрываюсь\s+на\b", r"\bраздражает\s+\w+\b",
                r"\bзлюсь\s+на\s+\w+\s+из-за\b",
                r"\bненавижу\b.*\bмелочи\b"
            ],
            "context_indicators": ["почему-то", "вдруг", "странно"],
            "explanation": "Вы переносите эмоции с реального источника на безопасную цель",
            "awareness": "На кого или что вы на самом деле злитесь?"
        },

        "reaction_formation": {
            "name": "Реактивное образование",
            "maturity": "neurotic",
            "patterns": [
                r"\bобожаю\b.*\bна\s+самом\s+деле\b",
                r"\bсовсем\s+не\s+волнует\b", r"\bабсолютно\s+спокоен\b",
                r"\bмне\s+всё\s+равно\b", r"\bплевать\b",
                r"\bочень\s+рад\b.*\bза\b"
            ],
            "context_indicators": ["совершенно", "абсолютно", "полностью"],
            "explanation": "Вы демонстрируете противоположные чувства",
            "awareness": "Что если всё наоборот - что бы вы чувствовали?"
        },

        "regression": {
            "name": "Регрессия",
            "maturity": "primitive",
            "patterns": [
                r"\bне\s+хочу\s+взрослеть\b", r"\bхочу\s+к\s+маме\b",
                r"\bкак\s+ребёнок\b", r"\bне\s+могу\s+справиться\b",
                r"\bпусть\s+кто-то\s+решит\b", r"\bне\s+мои\s+проблемы\b",
                # Расширенные patterns (более общие)
                r"\bпусть\s+\w+\s+(?:решит|решает|займётся|занимается)\b",
                r"\bчтобы\s+\w+\s+(?:решал|занимался)\b.*\b(?:проблем|вопрос)\b",
                r"\bхочу\s+(?:расслабиться|расслабится|отдохнуть|не\s+думать)\b",
                r"\bбыл[аи]?\s+сильн(?:ым|ой).*теперь\s+хочу\b"
            ],
            "context_indicators": ["не могу", "не хочу", "боюсь"],
            "explanation": "Вы возвращаетесь к более раннему способу реагирования",
            "awareness": "Какая часть вас сейчас говорит - взрослый или ребёнок?"
        },

        "repression": {
            "name": "Вытеснение",
            "maturity": "neurotic",
            "patterns": [
                r"\bне\s+помню\b", r"\bзабыл\w*\b",
                r"\bне\s+хочу\s+вспоминать\b", r"\bпрошло\s+и\s+забыто\b",
                r"\bне\s+думаю\s+об\s+этом\b", r"\bзачем\s+ворошить\b"
            ],
            "context_indicators": ["давно", "когда-то", "раньше"],
            "explanation": "Вы вытесняете болезненные воспоминания из сознания",
            "awareness": "Если бы тело могло говорить - что бы оно сказало?"
        },

        "dissociation": {
            "name": "Диссоциация",
            "maturity": "primitive",
            "patterns": [
                r"\bкак\s+будто\s+не\s+со\s+мной\b", r"\bсо\s+стороны\b",
                r"\bничего\s+не\s+чувствую\b", r"\bоцепене\w*\b",
                r"\bкак\s+в\s+тумане\b", r"\bавтопилот\b",
                r"\bотключи\w*\b"
            ],
            "context_indicators": ["словно", "как будто", "ощущение"],
            "explanation": "Вы отключаетесь от своих переживаний",
            "awareness": "Если бы вы могли что-то почувствовать - что бы это было?"
        },

        "somatization": {
            "name": "Соматизация",
            "maturity": "primitive",
            "patterns": [
                r"\bболит\s+голова\b", r"\bживот\s+крутит\b",
                r"\bсердце\s+колотится\b", r"\bне\s+могу\s+дышать\b",
                r"\bтошнит\b", r"\bслабость\b", r"\bусталость\b",
                r"\bбессонница\b"
            ],
            "context_indicators": ["когда", "от", "из-за", "стресс"],
            "explanation": "Ваше тело выражает то, что не может выразить психика",
            "awareness": "Если бы тело могло говорить словами - что бы оно сказало?"
        },

        "passive_aggression": {
            "name": "Пассивная агрессия",
            "maturity": "neurotic",
            "patterns": [
                r"\bзабыл\w*\b.*\bслучайно\b", r"\bопоздал\w*\b.*\bне\s+специально\b",
                r"\bне\s+успел\w*\b", r"\bпрокрастинир\w*\b",
                r"\bпотом\s+сделаю\b", r"\bне\s+заметил\w*\b",
                r"\bне\s+понял\w*\b"
            ],
            "context_indicators": ["нечаянно", "случайно", "как-то"],
            "explanation": "Вы выражаете гнев непрямыми способами",
            "awareness": "Что вы на самом деле хотите сказать напрямую?"
        },

        "avoidance": {
            "name": "Избегание",
            "maturity": "neurotic",
            "patterns": [
                r"\bпотом\s+разберусь\b", r"\bне\s+сейчас\b",
                r"\bизбегаю\b", r"\bне\s+хочу\s+думать\b",
                r"\bотложу\b", r"\bпока\s+не\s+готов\b",
                r"\bслишком\s+рано\b", r"\bеще\s+не\s+время\b"
            ],
            "context_indicators": ["потом", "позже", "когда-нибудь"],
            "explanation": "Вы уклоняетесь от неприятной реальности",
            "awareness": "Что произойдёт, если вы посмотрите на это прямо сейчас?"
        }
    }

    def __init__(self):
        """Инициализация детектора"""
        self._compile_patterns()
        logger.info("DefenseMechanismDetector initialized with 12 mechanism types")

    def _compile_patterns(self):
        """Компилирует regex паттерны для быстрого поиска"""
        self._compiled_patterns = {}
        for mechanism_id, mechanism_data in self.MECHANISM_PATTERNS.items():
            patterns = mechanism_data["patterns"]
            self._compiled_patterns[mechanism_id] = [
                re.compile(pattern, re.IGNORECASE | re.UNICODE)
                for pattern in patterns
            ]

    def detect(self, text: str) -> List[DetectedDefense]:
        """
        Обнаруживает защитные механизмы в тексте

        Args:
            text: Текст пользователя для анализа

        Returns:
            Список обнаруженных механизмов с confidence > 0.35
        """
        if not text or len(text) < 10:
            return []

        detected = []
        text_lower = text.lower()

        for mechanism_id, compiled_patterns in self._compiled_patterns.items():
            mechanism_data = self.MECHANISM_PATTERNS[mechanism_id]

            # Ищем совпадения паттернов
            matches = []
            for pattern in compiled_patterns:
                found = pattern.findall(text)
                if found:
                    matches.extend(found)

            if not matches:
                continue

            # Вычисляем confidence
            base_confidence = min(0.35 + len(matches) * 0.2, 0.9)

            # Повышаем confidence если есть контекстные индикаторы
            context_indicators = mechanism_data.get("context_indicators", [])
            context_boost = 0
            for indicator in context_indicators:
                if indicator.lower() in text_lower:
                    context_boost += 0.1

            final_confidence = min(base_confidence + context_boost, 0.95)

            # Формируем evidence
            evidence = matches[0] if isinstance(matches[0], str) else str(matches[0])

            detected.append(DetectedDefense(
                mechanism_type=mechanism_data["name"],
                maturity_level=mechanism_data["maturity"],
                confidence=final_confidence,
                evidence=evidence,
                explanation=mechanism_data["explanation"],
                awareness_prompt=mechanism_data["awareness"]
            ))

        # Сортируем по confidence
        detected.sort(key=lambda x: x.confidence, reverse=True)

        if detected:
            logger.info(f"Detected {len(detected)} defense mechanisms: "
                       f"{[d.mechanism_type for d in detected]}")

        return detected

    def get_awareness_summary(self, defenses: List[DetectedDefense], alliance_level: float = 0.5) -> Optional[str]:
        """
        Формирует мягкое осознание для пользователя

        ВАЖНО: Защитные механизмы озвучиваются только при достаточном терапевтическом альянсе

        Args:
            defenses: Список обнаруженных механизмов
            alliance_level: Уровень доверия (0.0-1.0)

        Returns:
            Мягкий текст или None если альянс недостаточен
        """
        if not defenses:
            return None

        # Проверяем альянс - примитивные защиты требуют высокого доверия
        top_defense = defenses[0]

        # Примитивные защиты (отрицание, проекция, диссоциация) - деликатная тема
        if top_defense.maturity_level == "primitive" and alliance_level < 0.6:
            logger.info(f"Skipping primitive defense awareness (alliance: {alliance_level})")
            return None

        # Невротические защиты можно озвучивать раньше
        if top_defense.maturity_level == "neurotic" and alliance_level < 0.4:
            return None

        # Формируем мягкое осознание
        return (
            f"_Мне показалось интересным..._\n\n"
            f"{top_defense.awareness_prompt}"
        )

    def format_for_storage(self, defenses: List[DetectedDefense]) -> List[Dict[str, Any]]:
        """
        Форматирует механизмы для сохранения в PostgreSQL

        Args:
            defenses: Список обнаруженных механизмов

        Returns:
            Список словарей для JSONB storage
        """
        return [
            {
                "type": d.mechanism_type,
                "maturity": d.maturity_level,
                "confidence": round(d.confidence, 2),
                "evidence": d.evidence
            }
            for d in defenses
        ]


# Singleton instance
_detector = None

def get_defense_detector() -> DefenseMechanismDetector:
    """Get singleton DefenseMechanismDetector instance"""
    global _detector
    if _detector is None:
        _detector = DefenseMechanismDetector()
    return _detector


# Пример использования
if __name__ == "__main__":
    detector = get_defense_detector()

    # Тестовые примеры
    test_texts = [
        "Всё нормально, ничего страшного не произошло, это не проблема",
        "Он меня ненавидит, я это точно знаю",
        "На самом деле это к лучшему, значит так надо было",
        "Статистически это маловероятно, если разобраться объективно",
        "Не помню, когда это было, забыл давно",
        "Как будто не со мной происходит, я словно со стороны наблюдаю",
        "У меня болит голова от этого стресса",
        "Потом разберусь, сейчас не время"
    ]

    for text in test_texts:
        print(f"\n{'='*50}")
        print(f"Текст: {text}")
        print(f"{'='*50}")

        defenses = detector.detect(text)

        if defenses:
            for d in defenses:
                print(f"\n  {d.mechanism_type} [{d.maturity_level}] ({d.confidence:.0%})")
                print(f"  Evidence: {d.evidence}")
                print(f"  → {d.awareness_prompt}")
        else:
            print("  Защитные механизмы не обнаружены")
