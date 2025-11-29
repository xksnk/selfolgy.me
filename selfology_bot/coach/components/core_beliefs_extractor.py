"""
Core Beliefs Extractor - Извлечение глубинных убеждений

Глубинные убеждения - это фундаментальные представления о себе,
других и мире, сформированные в детстве и определяющие восприятие.

Категории убеждений:
1. О себе (self) - "Я недостойный", "Я способный"
2. О других (others) - "Людям нельзя доверять", "Люди добрые"
3. О мире (world) - "Мир опасен", "Мир полон возможностей"

Валентность:
- Положительные (adaptive) - способствуют благополучию
- Отрицательные (maladaptive) - приводят к страданию
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import re

logger = logging.getLogger(__name__)


@dataclass
class ExtractedBelief:
    """Извлечённое глубинное убеждение"""
    belief_text: str  # Текст убеждения
    category: str  # "self", "others", "world"
    valence: float  # -1.0 (негативное) до 1.0 (позитивное)
    confidence: float  # 0.0 - 1.0
    evidence: str  # Фраза из текста
    schema_type: Optional[str] = None  # Тип схемы (Young's schemas)


class CoreBeliefsExtractor:
    """
    Извлекает глубинные убеждения из текста пользователя

    Использует паттерн-матчинг для категоризации и
    семантический анализ для определения валентности
    """

    # Паттерны глубинных убеждений на русском
    BELIEF_PATTERNS = {
        # === УБЕЖДЕНИЯ О СЕБЕ ===
        "self_worthless": {
            "category": "self",
            "valence": -0.9,
            "schema": "defectiveness",
            "patterns": [
                r"\bя\s+никчём\w*\b", r"\bя\s+бесполезн\w*\b",
                r"\bя\s+ничтожеств\w*\b", r"\bя\s+ничего\s+не\s+стою\b",
                r"\bменя\s+не\s+за\s+что\s+любить\b", r"\bя\s+дефектн\w*\b"
            ],
            "belief": "Я ничего не стою"
        },
        "self_unlovable": {
            "category": "self",
            "valence": -0.85,
            "schema": "emotional_deprivation",
            "patterns": [
                r"\bменя\s+невозможно\s+любить\b", r"\bменя\s+никто\s+не\s+любит\b",
                r"\bя\s+недостоин\w*\s+любви\b", r"\bменя\s+нельзя\s+любить\b",
                r"\bникому\s+не\s+нужен\b", r"\bникому\s+не\s+нужна\b"
            ],
            "belief": "Меня невозможно любить"
        },
        "self_incompetent": {
            "category": "self",
            "valence": -0.8,
            "schema": "failure",
            "patterns": [
                r"\bя\s+ни\s+на\s+что\s+не\s+способ\w*\b", r"\bя\s+неудачник\w*\b",
                r"\bу\s+меня\s+ничего\s+не\s+получ\w*\b", r"\bя\s+всё\s+порчу\b",
                r"\bя\s+не\s+справл\w*\b", r"\bя\s+тупой\b"
            ],
            "belief": "Я ни на что не способен"
        },
        "self_vulnerable": {
            "category": "self",
            "valence": -0.75,
            "schema": "vulnerability",
            "patterns": [
                r"\bя\s+беззащит\w*\b", r"\bсо\s+мной\s+что-то\s+случится\b",
                r"\bя\s+не\s+справлюсь\b", r"\bя\s+слаб\w*\b",
                r"\bменя\s+легко\s+обидеть\b"
            ],
            "belief": "Я беззащитен и уязвим"
        },
        "self_bad": {
            "category": "self",
            "valence": -0.85,
            "schema": "shame",
            "patterns": [
                r"\bя\s+плох\w*\s+человек\b", r"\bя\s+ужасн\w*\b",
                r"\bмне\s+стыдно\s+за\s+себя\b", r"\bя\s+виноват\w*\b",
                r"\bя\s+отвратительн\w*\b"
            ],
            "belief": "Я плохой человек"
        },
        # Позитивные о себе
        "self_worthy": {
            "category": "self",
            "valence": 0.8,
            "schema": "healthy_self",
            "patterns": [
                r"\bя\s+достоин\w*\b", r"\bя\s+ценн\w*\b",
                r"\bу\s+меня\s+получ\w*\b", r"\bя\s+справл\w*\b",
                r"\bя\s+могу\b", r"\bя\s+способ\w*\b"
            ],
            "belief": "Я достоин и способен"
        },

        # === УБЕЖДЕНИЯ О ДРУГИХ ===
        "others_untrustworthy": {
            "category": "others",
            "valence": -0.8,
            "schema": "mistrust",
            "patterns": [
                r"\bлюдям\s+нельзя\s+доверять\b", r"\bвсе\s+предают\b",
                r"\bникому\s+нельзя\s+верить\b", r"\bвсе\s+врут\b",
                r"\bменя\s+обманут\b", r"\bменя\s+используют\b"
            ],
            "belief": "Людям нельзя доверять"
        },
        "others_abandoning": {
            "category": "others",
            "valence": -0.85,
            "schema": "abandonment",
            "patterns": [
                r"\bвсе\s+меня\s+бросят\b", r"\bменя\s+оставят\b",
                r"\bя\s+останусь\s+один\b", r"\bникто\s+не\s+останется\b",
                r"\bлюди\s+уходят\b", r"\bменя\s+бросят\b"
            ],
            "belief": "Люди всегда уходят"
        },
        "others_critical": {
            "category": "others",
            "valence": -0.7,
            "schema": "social_isolation",
            "patterns": [
                r"\bвсе\s+меня\s+осуждают\b", r"\bменя\s+критикуют\b",
                r"\bлюди\s+смеются\s+надо\s+мной\b", r"\bменя\s+не\s+понимают\b",
                r"\bя\s+не\s+такой\s+как\s+все\b"
            ],
            "belief": "Люди меня осуждают"
        },
        "others_controlling": {
            "category": "others",
            "valence": -0.75,
            "schema": "subjugation",
            "patterns": [
                r"\bменя\s+контролируют\b", r"\bмной\s+манипулируют\b",
                r"\bя\s+не\s+могу\s+отказать\b", r"\bменя\s+заставляют\b",
                r"\bя\s+должен\s+подчиняться\b"
            ],
            "belief": "Другие контролируют меня"
        },
        # Позитивные о других
        "others_supportive": {
            "category": "others",
            "valence": 0.8,
            "schema": "healthy_others",
            "patterns": [
                r"\bменя\s+поддержат\b", r"\bлюди\s+добр\w*\b",
                r"\bесть\s+те\s+кто\s+любит\b", r"\bменя\s+понимают\b",
                r"\bя\s+могу\s+доверять\b"
            ],
            "belief": "Люди поддерживают меня"
        },

        # === УБЕЖДЕНИЯ О МИРЕ ===
        "world_dangerous": {
            "category": "world",
            "valence": -0.8,
            "schema": "vulnerability",
            "patterns": [
                r"\bмир\s+опас\w*\b", r"\bвезде\s+опасность\b",
                r"\bнужно\s+быть\s+осторожн\w*\b", r"\bвсё\s+плохо\s+кончится\b",
                r"\bкатастроф\w*\b", r"\bужас\w*\b"
            ],
            "belief": "Мир опасен"
        },
        "world_unfair": {
            "category": "world",
            "valence": -0.7,
            "schema": "entitlement",
            "patterns": [
                r"\bжизнь\s+несправедлив\w*\b", r"\bмир\s+несправедлив\b",
                r"\bвсё\s+против\s+меня\b", r"\bмне\s+не\s+везёт\b",
                r"\bтак\s+не\s+должно\s+быть\b"
            ],
            "belief": "Мир несправедлив"
        },
        "world_unpredictable": {
            "category": "world",
            "valence": -0.65,
            "schema": "vulnerability",
            "patterns": [
                r"\bничего\s+нельзя\s+планировать\b", r"\bвсё\s+непредсказуем\w*\b",
                r"\bне\s+знаю\s+что\s+будет\b", r"\bвсё\s+может\s+измениться\b",
                r"\bнет\s+стабильности\b"
            ],
            "belief": "Мир непредсказуем"
        },
        # Позитивные о мире
        "world_opportunities": {
            "category": "world",
            "valence": 0.75,
            "schema": "healthy_world",
            "patterns": [
                r"\bмир\s+полон\s+возможностей\b", r"\bвсё\s+будет\s+хорошо\b",
                r"\bесть\s+надежда\b", r"\bможно\s+изменить\b",
                r"\bвсё\s+получится\b"
            ],
            "belief": "Мир полон возможностей"
        }
    }

    def __init__(self):
        """Инициализация экстрактора"""
        self._compile_patterns()
        logger.info("CoreBeliefsExtractor initialized with schema-based belief detection")

    def _compile_patterns(self):
        """Компилирует regex паттерны"""
        self._compiled_patterns = {}
        for belief_id, belief_data in self.BELIEF_PATTERNS.items():
            patterns = belief_data["patterns"]
            self._compiled_patterns[belief_id] = [
                re.compile(pattern, re.IGNORECASE | re.UNICODE)
                for pattern in patterns
            ]

    def extract(self, text: str) -> List[ExtractedBelief]:
        """
        Извлекает глубинные убеждения из текста

        Args:
            text: Текст пользователя

        Returns:
            Список извлечённых убеждений
        """
        if not text or len(text) < 10:
            return []

        extracted = []
        text_lower = text.lower()

        for belief_id, compiled_patterns in self._compiled_patterns.items():
            belief_data = self.BELIEF_PATTERNS[belief_id]

            # Ищем совпадения
            matches = []
            for pattern in compiled_patterns:
                found = pattern.findall(text)
                if found:
                    matches.extend(found)

            if not matches:
                continue

            # Вычисляем confidence
            base_confidence = min(0.5 + len(matches) * 0.15, 0.9)

            # Формируем evidence
            evidence = matches[0] if isinstance(matches[0], str) else str(matches[0])

            extracted.append(ExtractedBelief(
                belief_text=belief_data["belief"],
                category=belief_data["category"],
                valence=belief_data["valence"],
                confidence=base_confidence,
                evidence=evidence,
                schema_type=belief_data.get("schema")
            ))

        # Сортируем по силе (абсолютное значение valence * confidence)
        extracted.sort(key=lambda x: abs(x.valence) * x.confidence, reverse=True)

        if extracted:
            logger.info(f"Extracted {len(extracted)} core beliefs: "
                       f"{[(b.belief_text, b.category) for b in extracted]}")

        return extracted

    def extract_with_context(self, text: str, history: List[str] = None) -> Tuple[List[ExtractedBelief], Dict[str, Any]]:
        """
        Извлекает убеждения с учётом контекста и истории

        Args:
            text: Текущий текст
            history: История предыдущих сообщений

        Returns:
            (beliefs, context_analysis)
        """
        # Базовое извлечение
        beliefs = self.extract(text)

        # Анализ контекста
        context = {
            "total_beliefs": len(beliefs),
            "negative_count": sum(1 for b in beliefs if b.valence < 0),
            "positive_count": sum(1 for b in beliefs if b.valence > 0),
            "categories": {
                "self": [b for b in beliefs if b.category == "self"],
                "others": [b for b in beliefs if b.category == "others"],
                "world": [b for b in beliefs if b.category == "world"]
            },
            "schemas_detected": list(set(b.schema_type for b in beliefs if b.schema_type)),
            "needs_attention": []
        }

        # Определяем что требует внимания
        if context["negative_count"] >= 2:
            context["needs_attention"].append("multiple_negative_beliefs")

        # Ищем повторяющиеся паттерны в истории
        if history:
            historical_beliefs = []
            for h in history[-5:]:  # Последние 5 сообщений
                historical_beliefs.extend(self.extract(h))

            # Считаем повторения
            belief_texts = [b.belief_text for b in beliefs]
            historical_texts = [b.belief_text for b in historical_beliefs]

            recurring = set(belief_texts) & set(historical_texts)
            if recurring:
                context["recurring_beliefs"] = list(recurring)
                context["needs_attention"].append("recurring_pattern")

        return beliefs, context

    def get_therapeutic_insight(self, beliefs: List[ExtractedBelief]) -> Optional[str]:
        """
        Генерирует терапевтический инсайт для пользователя

        Args:
            beliefs: Список извлечённых убеждений

        Returns:
            Мягкий терапевтический инсайт или None
        """
        if not beliefs:
            return None

        # Берём самое сильное негативное убеждение
        negative_beliefs = [b for b in beliefs if b.valence < 0]
        if not negative_beliefs:
            return None

        strongest = negative_beliefs[0]

        # Генерируем инсайт в зависимости от категории
        insights = {
            "self": f"Я заметил убеждение о себе: «{strongest.belief_text}». "
                   f"Откуда оно появилось? Что бы сказал вам близкий друг?",
            "others": f"Похоже, у вас есть убеждение о людях: «{strongest.belief_text}». "
                     f"Всегда ли это было так? Есть ли исключения?",
            "world": f"Я вижу убеждение о мире: «{strongest.belief_text}». "
                    f"Это помогает вам или мешает? Что можно изменить?"
        }

        return insights.get(strongest.category)

    def format_for_storage(self, beliefs: List[ExtractedBelief]) -> List[Dict[str, Any]]:
        """
        Форматирует убеждения для сохранения в PostgreSQL

        Args:
            beliefs: Список извлечённых убеждений

        Returns:
            Список словарей для JSONB storage
        """
        return [
            {
                "belief": b.belief_text,
                "category": b.category,
                "valence": round(b.valence, 2),
                "confidence": round(b.confidence, 2),
                "evidence": b.evidence,
                "schema": b.schema_type
            }
            for b in beliefs
        ]

    def format_for_embedding(self, beliefs: List[ExtractedBelief]) -> str:
        """
        Форматирует убеждения для embedding в psychological_constructs

        Args:
            beliefs: Список убеждений

        Returns:
            Текст для создания embedding
        """
        if not beliefs:
            return ""

        parts = []
        for b in beliefs:
            valence_word = "позитивное" if b.valence > 0 else "негативное"
            parts.append(
                f"Убеждение о {b.category}: {b.belief_text}. "
                f"Валентность: {valence_word}. Схема: {b.schema_type or 'не определена'}."
            )

        return " ".join(parts)


# Singleton instance
_extractor = None

def get_beliefs_extractor() -> CoreBeliefsExtractor:
    """Get singleton CoreBeliefsExtractor instance"""
    global _extractor
    if _extractor is None:
        _extractor = CoreBeliefsExtractor()
    return _extractor


# Пример использования
if __name__ == "__main__":
    extractor = get_beliefs_extractor()

    # Тестовые примеры
    test_texts = [
        "Я ничего не стою, меня никто не любит и никогда не полюбит",
        "Людям нельзя доверять, все меня предадут рано или поздно",
        "Мир опасен, нужно всегда быть осторожным, всё плохо кончится",
        "У меня получится, я достоин хорошей жизни",
        "Я неудачник, у меня ничего не получается, я всё порчу",
        "Меня обязательно бросят, все люди уходят в конце концов"
    ]

    for text in test_texts:
        print(f"\n{'='*60}")
        print(f"Текст: {text}")
        print(f"{'='*60}")

        beliefs = extractor.extract(text)

        if beliefs:
            for b in beliefs:
                valence_icon = "🟢" if b.valence > 0 else "🔴"
                print(f"\n{valence_icon} {b.belief_text}")
                print(f"   Категория: {b.category}, Валентность: {b.valence}")
                print(f"   Схема: {b.schema_type}, Confidence: {b.confidence:.0%}")
                print(f"   Evidence: «{b.evidence}»")

            insight = extractor.get_therapeutic_insight(beliefs)
            if insight:
                print(f"\n💭 Инсайт: {insight}")
        else:
            print("   Глубинные убеждения не обнаружены")
