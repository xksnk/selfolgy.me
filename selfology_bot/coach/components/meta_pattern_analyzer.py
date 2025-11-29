"""
Meta-Pattern Analyzer - Анализатор мета-паттернов через сессии

🔄 ЦЕЛЬ: Детекция повторяющихся паттернов на кросс-сессионном уровне
📊 МЕТРИКИ: Recurrence counting, pattern evolution tracking
🎯 ИНТЕГРАЦИЯ: Сохранение в meta_patterns (Qdrant)
"""

import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class MetaPattern:
    """Мета-паттерн (повторяющийся через сессии)"""
    pattern_id: str
    pattern_type: str  # theme, behavior, emotion, cognitive, relational
    description: str
    occurrences: int
    first_seen: str
    last_seen: str
    evidence: List[str] = field(default_factory=list)
    evolution: str = ""  # growing, stable, fading
    strength: float = 0.5  # 0.0 - 1.0


@dataclass
class PatternOccurrence:
    """Единичное проявление паттерна"""
    pattern_id: str
    timestamp: str
    evidence: str
    context: str


class MetaPatternAnalyzer:
    """
    Анализатор мета-паттернов пользователя

    Категории паттернов:
    - THEME: Повторяющиеся темы (работа, отношения, здоровье)
    - BEHAVIOR: Поведенческие паттерны (избегание, откладывание)
    - EMOTION: Эмоциональные паттерны (тревога перед событием)
    - COGNITIVE: Когнитивные паттерны (катастрофизация)
    - RELATIONAL: Паттерны отношений (границы, зависимость)
    """

    # Определения паттернов для детекции
    PATTERN_DEFINITIONS = {
        # Тематические паттерны
        "work_overwhelm": {
            "type": "theme",
            "description": "Перегруженность работой",
            "indicators": [
                r"\b(?:много|кучу|завален[аы]?)\s+(?:работы|дел|задач)\b",
                r"\bне\s+успеваю\b",
                r"\bдедлайн[аы]?\b",
                r"\bвыгор(?:аю|ел[аи]?)\b"
            ]
        },
        "relationship_anxiety": {
            "type": "theme",
            "description": "Тревога в отношениях",
            "indicators": [
                r"\bбоюсь\s+потерять\b",
                r"\bне\s+(?:уверен[аы]?|знаю)\s+в\s+(?:нём|ней|нас)\b",
                r"\bревну(?:ю|ет|ем)?\b",
                r"\bзависим(?:а|ы|ость)?\b"
            ]
        },
        "health_concern": {
            "type": "theme",
            "description": "Беспокойство о здоровье",
            "indicators": [
                r"\bболит\b",
                r"\bустал[аи]?\b",
                r"\bсон\b.*\b(?:плохой|не\s+высыпаюсь)\b",
                r"\bэнергии\s+(?:нет|мало)\b"
            ]
        },

        # Поведенческие паттерны
        "avoidance_pattern": {
            "type": "behavior",
            "description": "Паттерн избегания",
            "indicators": [
                r"\bотклады(?:ваю|вал[аи]?)\b",
                r"\bизбега(?:ю|л[аи]?)\b",
                r"\bне\s+хочу\s+(?:думать|говорить)\b",
                r"\bлучше\s+потом\b"
            ]
        },
        "perfectionism": {
            "type": "behavior",
            "description": "Перфекционизм",
            "indicators": [
                r"\b(?:должн[оа]?\s+быть\s+)?идеальн[оа]?\b",
                r"\bне\s+достаточно\s+хорош[оа]?\b",
                r"\bошибка.*недопустим[аы]?\b",
                r"\bвсё\s+или\s+ничего\b"
            ]
        },
        "people_pleasing": {
            "type": "behavior",
            "description": "Угодничество",
            "indicators": [
                r"\bне\s+могу\s+отказать\b",
                r"\bчто\s+(?:обо\s+мне\s+)?подумают\b",
                r"\bне\s+хочу\s+(?:расстроить|обидеть)\b",
                r"\bвсем\s+(?:угодить|нравиться)\b"
            ]
        },

        # Эмоциональные паттерны
        "anticipatory_anxiety": {
            "type": "emotion",
            "description": "Тревога ожидания",
            "indicators": [
                r"\bпереживаю\s+(?:заранее|о\s+будущем)\b",
                r"\bа\s+вдруг\b",
                r"\bчто\s+если\b.*\bплохо[ему]?\b",
                r"\bбоюсь\s+(?:что\s+)?будет\b"
            ]
        },
        "guilt_cycle": {
            "type": "emotion",
            "description": "Цикл вины",
            "indicators": [
                r"\bвинов(?:ат[аы]?|а)\b",
                r"\bкак\s+(?:я\s+)?мог(?:ла|у)?\b",
                r"\bне\s+должн[аоы]?\s+был[аи]?\b",
                r"\bмоя\s+вина\b"
            ]
        },
        "emotional_suppression": {
            "type": "emotion",
            "description": "Подавление эмоций",
            "indicators": [
                r"\bнельзя\s+(?:плакать|злиться)\b",
                r"\bдержу\s+в\s+себе\b",
                r"\bне\s+показываю\b",
                r"\bсдержива(?:юсь|ть)\b"
            ]
        },

        # Когнитивные паттерны
        "catastrophizing": {
            "type": "cognitive",
            "description": "Катастрофизация",
            "indicators": [
                r"\bкатастроф[аы]?\b",
                r"\bконец\s+света\b",
                r"\bвсё\s+пропало\b",
                r"\bникогда\s+не\s+(?:будет|получится)\b"
            ]
        },
        "mind_reading": {
            "type": "cognitive",
            "description": "Чтение мыслей",
            "indicators": [
                r"\bон[аи]?\s+думают?\s+что\b",
                r"\bуверен[аы]?\s+что\s+он[аи]?\b",
                r"\bточно\s+(?:считает|думает)\b",
                r"\bя\s+знаю\s+что\s+он[аи]?\b"
            ]
        },
        "black_white_thinking": {
            "type": "cognitive",
            "description": "Черно-белое мышление",
            "indicators": [
                r"\bили\s+всё\s+или\s+ничего\b",
                r"\bтолько\s+(?:хорошо|плохо)\b",
                r"\bникогда\b.*\bвсегда\b",
                r"\bполный\s+(?:провал|успех)\b"
            ]
        },

        # Паттерны отношений
        "boundary_issues": {
            "type": "relational",
            "description": "Проблемы с границами",
            "indicators": [
                r"\bне\s+(?:могу|умею)\s+(?:отказать|сказать\s+нет)\b",
                r"\bнарушают\s+(?:мои\s+)?границы\b",
                r"\bслишком\s+(?:много\s+)?позволяю\b",
                r"\bне\s+(?:защищаю|отстаиваю)\s+себя\b"
            ]
        },
        "codependency": {
            "type": "relational",
            "description": "Созависимость",
            "indicators": [
                r"\bне\s+могу\s+без\s+(?:него|неё)\b",
                r"\bмоя\s+жизнь\s+зависит\b",
                r"\bспасаю\b",
                r"\bответствен(?:на|ен)\s+за\s+(?:его|её)\s+(?:чувства|счастье)\b"
            ]
        },
        "trust_issues": {
            "type": "relational",
            "description": "Проблемы с доверием",
            "indicators": [
                r"\bне\s+(?:могу|хочу)\s+доверять\b",
                r"\bобман(?:ут|ет|ывали)\b",
                r"\bпредад(?:ут|ут)\b",
                r"\bникому\s+нельзя\s+верить\b"
            ]
        }
    }

    def __init__(self):
        """Инициализация анализатора мета-паттернов"""
        # История паттернов по пользователям
        self.user_patterns: Dict[int, Dict[str, MetaPattern]] = {}
        # История проявлений
        self.pattern_history: Dict[int, List[PatternOccurrence]] = {}

        logger.info("✅ MetaPatternAnalyzer initialized")

    def analyze(
        self,
        user_id: int,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[MetaPattern]:
        """
        Анализировать текст на мета-паттерны

        Args:
            user_id: ID пользователя
            text: Текст для анализа
            context: Дополнительный контекст

        Returns:
            Список обнаруженных/обновленных мета-паттернов
        """
        text_lower = text.lower()
        detected_patterns = []
        current_time = datetime.now().isoformat()

        for pattern_id, pattern_def in self.PATTERN_DEFINITIONS.items():
            # Проверяем индикаторы
            matches = []
            for indicator in pattern_def["indicators"]:
                match = re.search(indicator, text_lower, re.IGNORECASE)
                if match:
                    # Извлекаем контекст вокруг совпадения
                    start = max(0, match.start() - 30)
                    end = min(len(text), match.end() + 30)
                    evidence = text[start:end].strip()
                    matches.append(evidence)

            if matches:
                # Обновляем или создаём паттерн
                pattern = self._update_pattern(
                    user_id=user_id,
                    pattern_id=pattern_id,
                    pattern_type=pattern_def["type"],
                    description=pattern_def["description"],
                    evidence=matches[0],  # Первый матч как основное доказательство
                    timestamp=current_time
                )
                detected_patterns.append(pattern)

        if detected_patterns:
            logger.info(f"🔄 Detected {len(detected_patterns)} meta-patterns for user {user_id}: {[p.pattern_id for p in detected_patterns]}")

        return detected_patterns

    def _update_pattern(
        self,
        user_id: int,
        pattern_id: str,
        pattern_type: str,
        description: str,
        evidence: str,
        timestamp: str
    ) -> MetaPattern:
        """Обновить или создать мета-паттерн"""

        # Инициализируем словарь для пользователя если нужно
        if user_id not in self.user_patterns:
            self.user_patterns[user_id] = {}

        if pattern_id in self.user_patterns[user_id]:
            # Обновляем существующий паттерн
            pattern = self.user_patterns[user_id][pattern_id]
            pattern.occurrences += 1
            pattern.last_seen = timestamp
            if evidence not in pattern.evidence:
                pattern.evidence.append(evidence)
                # Храним только последние 5 доказательств
                pattern.evidence = pattern.evidence[-5:]

            # Обновляем strength на основе частоты
            pattern.strength = min(1.0, 0.3 + (pattern.occurrences / 10) * 0.7)

            # Определяем эволюцию (упрощенно)
            if pattern.occurrences > 3:
                pattern.evolution = "growing"
            elif pattern.occurrences == 1:
                pattern.evolution = "emerging"
            else:
                pattern.evolution = "stable"
        else:
            # Создаём новый паттерн
            pattern = MetaPattern(
                pattern_id=pattern_id,
                pattern_type=pattern_type,
                description=description,
                occurrences=1,
                first_seen=timestamp,
                last_seen=timestamp,
                evidence=[evidence],
                evolution="emerging",
                strength=0.3
            )
            self.user_patterns[user_id][pattern_id] = pattern

        # Сохраняем в историю проявлений
        occurrence = PatternOccurrence(
            pattern_id=pattern_id,
            timestamp=timestamp,
            evidence=evidence,
            context=""
        )
        if user_id not in self.pattern_history:
            self.pattern_history[user_id] = []
        self.pattern_history[user_id].append(occurrence)

        return pattern

    def get_user_patterns(self, user_id: int) -> List[MetaPattern]:
        """Получить все мета-паттерны пользователя"""
        if user_id not in self.user_patterns:
            return []
        return list(self.user_patterns[user_id].values())

    def get_top_patterns(
        self,
        user_id: int,
        top_n: int = 3,
        by: str = "occurrences"
    ) -> List[MetaPattern]:
        """
        Получить топ мета-паттернов пользователя

        Args:
            user_id: ID пользователя
            top_n: Количество паттернов
            by: Критерий сортировки (occurrences, strength)

        Returns:
            Список топ паттернов
        """
        if user_id not in self.user_patterns:
            return []

        patterns = list(self.user_patterns[user_id].values())

        if by == "strength":
            patterns.sort(key=lambda x: x.strength, reverse=True)
        else:
            patterns.sort(key=lambda x: x.occurrences, reverse=True)

        return patterns[:top_n]

    def get_patterns_by_type(self, user_id: int, pattern_type: str) -> List[MetaPattern]:
        """Получить паттерны определённого типа"""
        if user_id not in self.user_patterns:
            return []

        return [
            p for p in self.user_patterns[user_id].values()
            if p.pattern_type == pattern_type
        ]

    def get_pattern_summary(self, user_id: int) -> Dict[str, Any]:
        """
        Получить сводку по паттернам пользователя

        Returns:
            Dict с общей статистикой по паттернам
        """
        if user_id not in self.user_patterns:
            return {
                "total_patterns": 0,
                "by_type": {},
                "strongest_pattern": None,
                "most_frequent_pattern": None
            }

        patterns = list(self.user_patterns[user_id].values())

        # Группировка по типам
        by_type: Dict[str, int] = defaultdict(int)
        for p in patterns:
            by_type[p.pattern_type] += 1

        # Поиск сильнейшего и частейшего
        strongest = max(patterns, key=lambda x: x.strength) if patterns else None
        most_frequent = max(patterns, key=lambda x: x.occurrences) if patterns else None

        return {
            "total_patterns": len(patterns),
            "by_type": dict(by_type),
            "strongest_pattern": strongest.pattern_id if strongest else None,
            "strongest_description": strongest.description if strongest else None,
            "most_frequent_pattern": most_frequent.pattern_id if most_frequent else None,
            "most_frequent_occurrences": most_frequent.occurrences if most_frequent else 0
        }

    def get_therapeutic_insight(self, user_id: int) -> Optional[str]:
        """
        Сгенерировать терапевтический инсайт на основе паттернов

        Returns:
            Текст инсайта или None
        """
        patterns = self.get_top_patterns(user_id, top_n=2, by="strength")

        if not patterns:
            return None

        if len(patterns) == 1:
            p = patterns[0]
            return f"Замечаю повторяющийся паттерн: {p.description}. Это появлялось уже {p.occurrences} раз(а). Хотите исследовать это подробнее?"
        else:
            p1, p2 = patterns[0], patterns[1]
            return f"Вижу связь между паттернами '{p1.description}' и '{p2.description}'. Возможно, они влияют друг на друга. Что вы думаете об этом?"

    def format_for_storage(self, patterns: List[MetaPattern]) -> List[Dict[str, Any]]:
        """Форматировать паттерны для хранения"""
        return [
            {
                "pattern_id": p.pattern_id,
                "pattern_type": p.pattern_type,
                "description": p.description,
                "occurrences": p.occurrences,
                "strength": p.strength,
                "evolution": p.evolution,
                "first_seen": p.first_seen,
                "last_seen": p.last_seen,
                "evidence": p.evidence[-3:]  # Последние 3 доказательства
            }
            for p in patterns
        ]


# Singleton instance
_meta_analyzer = None


def get_meta_analyzer() -> MetaPatternAnalyzer:
    """Получить singleton экземпляр анализатора мета-паттернов"""
    global _meta_analyzer
    if _meta_analyzer is None:
        _meta_analyzer = MetaPatternAnalyzer()
    return _meta_analyzer


# === ТЕСТИРОВАНИЕ ===
if __name__ == "__main__":
    analyzer = MetaPatternAnalyzer()

    user_id = 999

    # Тест: Несколько сообщений для формирования паттернов
    print("🔄 META-PATTERN ANALYZER TEST\n" + "=" * 50)

    test_messages = [
        # Сообщение 1: Работа + избегание
        "Опять завалена работой, столько дел накопилось. Откладываю важный разговор с начальником.",

        # Сообщение 2: Работа + тревога ожидания
        "Не успеваю к дедлайну. А вдруг меня уволят? Переживаю заранее о встрече завтра.",

        # Сообщение 3: Отношения + границы
        "Он опять просит помощь, не могу отказать. Боюсь потерять его если скажу нет.",

        # Сообщение 4: Работа + перфекционизм
        "Проект должен быть идеальным. Ошибка недопустима. Снова много работы на неделе.",

        # Сообщение 5: Вина + подавление
        "Чувствую себя виноватой что отказала. Держу в себе злость, нельзя показывать."
    ]

    for i, message in enumerate(test_messages):
        print(f"\n📝 Message {i+1}: {message[:50]}...")

        patterns = analyzer.analyze(user_id, message)

        for p in patterns:
            status = "🆕" if p.occurrences == 1 else f"🔄 x{p.occurrences}"
            print(f"   {status} {p.pattern_id}: {p.description} (strength: {p.strength:.2f})")

    # Сводка
    print("\n" + "=" * 50)
    summary = analyzer.get_pattern_summary(user_id)
    print(f"📊 Summary:")
    print(f"   Total patterns: {summary['total_patterns']}")
    print(f"   By type: {summary['by_type']}")
    print(f"   Strongest: {summary['strongest_pattern']} - {summary['strongest_description']}")
    print(f"   Most frequent: {summary['most_frequent_pattern']} ({summary['most_frequent_occurrences']} times)")

    # Топ паттерны
    top = analyzer.get_top_patterns(user_id, top_n=3)
    print(f"\n🎯 Top 3 patterns:")
    for p in top:
        bar = "█" * int(p.strength * 10) + "░" * (10 - int(p.strength * 10))
        print(f"   {p.description}: {bar} {p.strength:.0%} ({p.occurrences}x)")

    # Терапевтический инсайт
    insight = analyzer.get_therapeutic_insight(user_id)
    if insight:
        print(f"\n💡 Therapeutic insight:")
        print(f"   {insight}")

    print("\n✅ Test completed!")
