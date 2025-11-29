"""
Growth Area Tracker - Трекер зон роста и прогресса

🎯 ЦЕЛЬ: Отслеживать области развития и прогресс пользователя
📊 МЕТРИКИ: Progress measurement, goal attainment scoring
🔄 ТРАЕКТОРИЯ: Визуализация направления роста
"""

import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class GrowthArea:
    """Зона роста пользователя"""
    area_id: str
    name: str
    category: str  # emotional, relational, behavioral, cognitive, self
    description: str
    current_progress: float  # 0.0 - 1.0
    target_state: str
    evidence: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


@dataclass
class GrowthMeasurement:
    """Измерение прогресса в зоне роста"""
    area_id: str
    delta: float  # Изменение (-1.0 to 1.0)
    new_progress: float
    evidence: str
    timestamp: str


class GrowthAreaTracker:
    """
    Трекер зон роста и прогресса пользователя

    Категории зон роста:
    - EMOTIONAL: управление эмоциями, принятие чувств
    - RELATIONAL: отношения, границы, близость
    - BEHAVIORAL: привычки, действия, самодисциплина
    - COGNITIVE: мышление, убеждения, паттерны
    - SELF: самооценка, идентичность, ценности
    """

    # Типичные зоны роста
    COMMON_GROWTH_AREAS = {
        "self_compassion": {
            "name": "Самосострадание",
            "category": "self",
            "description": "Доброе отношение к себе в трудные моменты",
            "target_state": "Относиться к себе с добротой и пониманием",
            "positive_indicators": [
                r"\bпрощаю\s+себя\b",
                r"\bне\s+виню\s+себя\b",
                r"\bотнесусь\s+(?:мягко|с\s+пониманием)\b",
                r"\bкаждый\s+может\s+(?:ошибиться|устать)\b"
            ],
            "negative_indicators": [
                r"\bненавижу\s+себя\b",
                r"\bя\s+(?:ужасный|никчёмный)\b",
                r"\bне\s+заслуживаю\b"
            ]
        },
        "emotional_awareness": {
            "name": "Эмоциональная осознанность",
            "category": "emotional",
            "description": "Понимание и называние своих чувств",
            "target_state": "Осознавать и принимать свои эмоции",
            "positive_indicators": [
                r"\bчувствую\s+(?:что|как|себя)\b",
                r"\bэто\s+(?:грусть|злость|страх|радость)\b",
                r"\bосознаю\s+(?:свои\s+)?(?:чувства|эмоции)\b"
            ],
            "negative_indicators": [
                r"\bне\s+знаю,?\s+что\s+чувствую\b",
                r"\bне\s+понимаю\s+(?:свои\s+)?(?:чувств|эмоций)\b"
            ]
        },
        "boundary_setting": {
            "name": "Установка границ",
            "category": "relational",
            "description": "Умение говорить нет и защищать свои границы",
            "target_state": "Уверенно устанавливать и защищать свои границы",
            "positive_indicators": [
                r"\bсказал[аи]?\s+нет\b",
                r"\bмои\s+границы\b",
                r"\bимею\s+право\b",
                r"\bне\s+буду\s+(?:терпеть|позволять)\b"
            ],
            "negative_indicators": [
                r"\bне\s+(?:могу|умею)\s+отказывать\b",
                r"\bвсегда\s+соглашаюсь\b",
                r"\bне\s+хочу\s+(?:обидеть|огорчить)\b"
            ]
        },
        "assertiveness": {
            "name": "Ассертивность",
            "category": "behavioral",
            "description": "Выражение своих потребностей и мнений",
            "target_state": "Уверенно выражать свои потребности и мнения",
            "positive_indicators": [
                r"\bскажу\s+(?:прямо|честно)\b",
                r"\bмоё\s+мнение\b",
                r"\bмне\s+нужно\b",
                r"\bя\s+хочу\b"
            ],
            "negative_indicators": [
                r"\bне\s+могу\s+(?:сказать|попросить)\b",
                r"\bмолчу\b",
                r"\bне\s+важно,?\s+что\s+я\s+(?:думаю|хочу)\b"
            ]
        },
        "vulnerability": {
            "name": "Принятие уязвимости",
            "category": "relational",
            "description": "Способность быть открытым и уязвимым",
            "target_state": "Позволять себе быть уязвимым в безопасных отношениях",
            "positive_indicators": [
                r"\bоткрываюсь\b",
                r"\bдоверяю\b",
                r"\bпоказываю\s+(?:свои\s+)?(?:чувства|слабость)\b",
                r"\bпрошу\s+(?:помощи|поддержки)\b"
            ],
            "negative_indicators": [
                r"\bне\s+(?:могу|хочу)\s+(?:показать|признать)\s+(?:слабость|уязвимость)\b",
                r"\bсправлюсь\s+сам[аи]?\b",
                r"\bникому\s+не\s+нужен\b"
            ]
        },
        "cognitive_flexibility": {
            "name": "Когнитивная гибкость",
            "category": "cognitive",
            "description": "Способность менять перспективу и рассматривать альтернативы",
            "target_state": "Гибко адаптировать мышление к новой информации",
            "positive_indicators": [
                r"\bможет\s+быть\s+(?:иначе|по-другому)\b",
                r"\bс\s+другой\s+стороны\b",
                r"\bесть\s+и\s+другие\s+варианты\b"
            ],
            "negative_indicators": [
                r"\bтолько\s+так\s+(?:и\s+)?(?:должно|может)\b",
                r"\bвсегда\s+так\b",
                r"\bникогда\s+(?:не\s+)?(?:изменится|получится)\b"
            ]
        }
    }

    def __init__(self):
        """Инициализация трекера зон роста"""
        # Зоны роста по пользователям
        self.user_growth_areas: Dict[int, Dict[str, GrowthArea]] = {}
        # История измерений
        self.measurement_history: Dict[int, List[GrowthMeasurement]] = {}

        logger.info("✅ GrowthAreaTracker initialized")

    def identify_growth_areas(
        self,
        user_id: int,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Идентифицировать зоны роста на основе текста

        Args:
            user_id: ID пользователя
            text: Текст для анализа
            context: Дополнительный контекст

        Returns:
            Список ID идентифицированных зон роста
        """
        text_lower = text.lower()
        identified = []

        for area_id, area_data in self.COMMON_GROWTH_AREAS.items():
            # Проверяем негативные индикаторы (указывают на потребность в росте)
            negative_score = 0
            for pattern in area_data["negative_indicators"]:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    negative_score += 1

            if negative_score > 0:
                # Создаём или обновляем зону роста
                if user_id not in self.user_growth_areas:
                    self.user_growth_areas[user_id] = {}

                if area_id not in self.user_growth_areas[user_id]:
                    self.user_growth_areas[user_id][area_id] = GrowthArea(
                        area_id=area_id,
                        name=area_data["name"],
                        category=area_data["category"],
                        description=area_data["description"],
                        current_progress=0.2,  # Начальный прогресс
                        target_state=area_data["target_state"],
                        created_at=datetime.now().isoformat(),
                        updated_at=datetime.now().isoformat()
                    )
                    identified.append(area_id)

        if identified:
            logger.info(f"📈 Identified {len(identified)} growth areas for user {user_id}: {identified}")

        return identified

    def measure_progress(
        self,
        user_id: int,
        text: str
    ) -> List[GrowthMeasurement]:
        """
        Измерить прогресс в зонах роста

        Args:
            user_id: ID пользователя
            text: Текст для анализа

        Returns:
            Список измерений прогресса
        """
        if user_id not in self.user_growth_areas:
            return []

        text_lower = text.lower()
        measurements = []

        for area_id, growth_area in self.user_growth_areas[user_id].items():
            area_data = self.COMMON_GROWTH_AREAS.get(area_id, {})
            if not area_data:
                continue

            # Считаем позитивные и негативные индикаторы
            positive_score = 0
            negative_score = 0
            evidence = ""

            for pattern in area_data.get("positive_indicators", []):
                match = re.search(pattern, text_lower, re.IGNORECASE)
                if match:
                    positive_score += 1
                    if not evidence:
                        start = max(0, match.start() - 20)
                        end = min(len(text), match.end() + 20)
                        evidence = text[start:end].strip()

            for pattern in area_data.get("negative_indicators", []):
                if re.search(pattern, text_lower, re.IGNORECASE):
                    negative_score += 1

            # Вычисляем delta
            if positive_score > 0 or negative_score > 0:
                delta = (positive_score - negative_score) * 0.05
                new_progress = max(0.0, min(1.0, growth_area.current_progress + delta))

                if delta != 0:
                    measurement = GrowthMeasurement(
                        area_id=area_id,
                        delta=round(delta, 3),
                        new_progress=round(new_progress, 3),
                        evidence=evidence,
                        timestamp=datetime.now().isoformat()
                    )

                    # Обновляем прогресс
                    growth_area.current_progress = new_progress
                    growth_area.updated_at = datetime.now().isoformat()

                    # Сохраняем в историю
                    if user_id not in self.measurement_history:
                        self.measurement_history[user_id] = []
                    self.measurement_history[user_id].append(measurement)

                    measurements.append(measurement)

        if measurements:
            logger.debug(f"📊 Measured progress in {len(measurements)} growth areas for user {user_id}")

        return measurements

    def get_user_growth_areas(self, user_id: int) -> List[GrowthArea]:
        """Получить все зоны роста пользователя"""
        if user_id not in self.user_growth_areas:
            return []
        return list(self.user_growth_areas[user_id].values())

    def get_progress_summary(self, user_id: int) -> Dict[str, Any]:
        """
        Получить сводку прогресса пользователя

        Returns:
            Dict с категориями и средним прогрессом
        """
        if user_id not in self.user_growth_areas:
            return {"total_areas": 0, "average_progress": 0.0, "by_category": {}}

        areas = self.user_growth_areas[user_id]

        # Группируем по категориям
        by_category: Dict[str, List[float]] = {}
        all_progress = []

        for area in areas.values():
            if area.category not in by_category:
                by_category[area.category] = []
            by_category[area.category].append(area.current_progress)
            all_progress.append(area.current_progress)

        # Средний прогресс по категориям
        category_averages = {
            cat: round(sum(progs) / len(progs), 3)
            for cat, progs in by_category.items()
        }

        return {
            "total_areas": len(areas),
            "average_progress": round(sum(all_progress) / len(all_progress), 3) if all_progress else 0.0,
            "by_category": category_averages
        }

    def get_top_growth_areas(self, user_id: int, top_n: int = 3) -> List[Tuple[str, float]]:
        """
        Получить топ зон роста требующих внимания

        Returns:
            Список (area_name, progress) отсортированный по прогрессу (низкий → высокий)
        """
        if user_id not in self.user_growth_areas:
            return []

        areas = self.user_growth_areas[user_id]
        sorted_areas = sorted(areas.values(), key=lambda x: x.current_progress)

        return [(a.name, a.current_progress) for a in sorted_areas[:top_n]]

    def format_for_storage(self, user_id: int) -> Dict[str, Any]:
        """Форматировать данные для хранения"""
        return {
            "user_id": user_id,
            "growth_areas": {
                area_id: {
                    "name": area.name,
                    "category": area.category,
                    "progress": area.current_progress,
                    "target": area.target_state
                }
                for area_id, area in self.user_growth_areas.get(user_id, {}).items()
            },
            "summary": self.get_progress_summary(user_id),
            "timestamp": datetime.now().isoformat()
        }


# Singleton instance
_growth_tracker = None


def get_growth_tracker() -> GrowthAreaTracker:
    """Получить singleton экземпляр трекера роста"""
    global _growth_tracker
    if _growth_tracker is None:
        _growth_tracker = GrowthAreaTracker()
    return _growth_tracker


# === ТЕСТИРОВАНИЕ ===
if __name__ == "__main__":
    tracker = GrowthAreaTracker()

    user_id = 789

    # Тест 1: Идентификация зон роста
    print("📈 GROWTH AREA TRACKER TEST\n" + "=" * 50)

    test_texts = [
        # Негативные индикаторы (идентификация зон роста)
        "Не знаю, что чувствую. Ненавижу себя за это. Не могу отказывать людям.",

        # Позитивные индикаторы (прогресс)
        "Сегодня сказала нет и не чувствую вины. Я имею право на свои границы.",

        # Смешанные
        "Чувствую грусть и это нормально. Хотя ещё молчу когда нужно говорить."
    ]

    for i, text in enumerate(test_texts):
        print(f"\n📝 Test {i+1}: {text[:50]}...")

        # Идентификация
        new_areas = tracker.identify_growth_areas(user_id, text)
        if new_areas:
            print(f"   🆕 New growth areas: {new_areas}")

        # Измерение прогресса
        measurements = tracker.measure_progress(user_id, text)
        for m in measurements:
            direction = "📈" if m.delta > 0 else "📉"
            print(f"   {direction} {m.area_id}: {m.delta:+.2f} → {m.new_progress:.2f}")

    # Сводка
    print("\n" + "=" * 50)
    summary = tracker.get_progress_summary(user_id)
    print(f"📊 Summary:")
    print(f"   Total areas: {summary['total_areas']}")
    print(f"   Average progress: {summary['average_progress']:.2f}")
    print(f"   By category: {summary['by_category']}")

    top_areas = tracker.get_top_growth_areas(user_id)
    print(f"\n🎯 Top growth areas:")
    for name, progress in top_areas:
        bar = "█" * int(progress * 10) + "░" * (10 - int(progress * 10))
        print(f"   {name}: {bar} {progress:.0%}")

    print("\n✅ Test completed!")
