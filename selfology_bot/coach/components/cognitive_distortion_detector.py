"""
Cognitive Distortion Detector - Детектор когнитивных искажений

Обнаруживает 15 типов когнитивных искажений в тексте пользователя.
Критический компонент для работы с депрессией и тревожностью.

Типы искажений (по Beck, Burns):
1. Черно-белое мышление (All-or-Nothing)
2. Катастрофизация (Catastrophizing)
3. Обесценивание позитива (Discounting Positive)
4. Эмоциональное рассуждение (Emotional Reasoning)
5. Навешивание ярлыков (Labeling)
6. Ментальный фильтр (Mental Filter)
7. Чтение мыслей (Mind Reading)
8. Сверхобобщение (Overgeneralization)
9. Персонализация (Personalization)
10. Долженствование (Should Statements)
11. Туннельное зрение (Tunnel Vision)
12. Несправедливое сравнение (Unfair Comparison)
13. Предсказание будущего (Fortune Telling)
14. Магнификация/Минимизация (Magnification)
15. Перфекционизм (Perfectionism)
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import re

logger = logging.getLogger(__name__)


@dataclass
class DetectedDistortion:
    """Обнаруженное когнитивное искажение"""
    distortion_type: str
    confidence: float  # 0.0 - 1.0
    evidence: str  # Фраза из текста
    explanation: str  # Объяснение для пользователя
    therapeutic_response: str  # Терапевтический ответ


class CognitiveDistortionDetector:
    """
    Детектор когнитивных искажений

    Использует паттерн-матчинг + семантический анализ
    для обнаружения негативных паттернов мышления
    """

    # Паттерны когнитивных искажений на русском языке
    DISTORTION_PATTERNS = {
        "all_or_nothing": {
            "name": "Черно-белое мышление",
            "patterns": [
                r"\bникогда\b", r"\bвсегда\b", r"\bвсё\b", r"\bничего\b",
                r"\bполностью\b", r"\bабсолютно\b", r"\bкаждый раз\b",
                r"\bтотально\b", r"\bцеликом\b", r"\bна 100%\b",
                r"\bлибо\s+.*\s+либо\b", r"\bили\s+.*\s+или\b"
            ],
            "context_words": ["провал", "успех", "идеально", "ужасно"],
            "explanation": "Вы видите ситуацию только в крайностях - или всё хорошо, или всё плохо",
            "therapeutic": "Попробуйте найти середину. Какие оттенки серого есть в этой ситуации?"
        },

        "catastrophizing": {
            "name": "Катастрофизация",
            "patterns": [
                r"\bкатастроф\w*\b", r"\bужас\w*\b", r"\bкошмар\w*\b",
                r"\bконец света\b", r"\bвсё пропало\b", r"\bне переживу\b",
                r"\bэто конец\b", r"\bсамое худшее\b", r"\bнепоправим\w*\b",
                r"\bникогда не\s+\w+\s+из этого\b"
            ],
            "context_words": ["случится", "произойдёт", "будет"],
            "explanation": "Вы предполагаете худший возможный исход",
            "therapeutic": "Насколько реалистичен этот сценарий? Что случится скорее всего?"
        },

        "discounting_positive": {
            "name": "Обесценивание позитива",
            "patterns": [
                r"\bповезло\b", r"\bслучайн\w*\b", r"\bне считается\b",
                r"\bэто не\s+\w+\s+заслуга\b", r"\bлюбой бы смог\b",
                r"\bничего особенного\b", r"\bподумаешь\b",
                r"\bда ладно\b.*\bдостижени\w*\b"
            ],
            "context_words": ["но", "однако", "хотя", "всё равно"],
            "explanation": "Вы отвергаете или преуменьшаете свои достижения",
            "therapeutic": "Что если принять этот успех как заслуженный? Какие усилия вы приложили?"
        },

        "emotional_reasoning": {
            "name": "Эмоциональное рассуждение",
            "patterns": [
                r"\bчувствую\b.*\bзначит\b", r"\bраз я чувствую\b",
                r"\bмне кажется\b.*\bпоэтому\b", r"\bощущаю\b.*\bтак и есть\b",
                r"\bя\s+чувствую\s+себя\s+\w+\s*,?\s*потому что я\s+\w+\b"
            ],
            "context_words": [],
            "explanation": "Вы принимаете свои чувства за доказательство реальности",
            "therapeutic": "Чувства - не факты. Какие объективные доказательства есть?"
        },

        "labeling": {
            "name": "Навешивание ярлыков",
            "patterns": [
                r"\bя\s+[-–—]\s*\w+\b", r"\bя\s+неудачник\w*\b",
                r"\bя\s+дурак\b", r"\bя\s+лузер\b", r"\bя\s+идиот\b",
                r"\bя\s+ничтожеств\w*\b", r"\bя\s+тупой\b", r"\bя\s+бесполезн\w*\b",
                r"\bон\s+[-–—]\s*\w+\b", r"\bона\s+[-–—]\s*\w+\b"
            ],
            "context_words": ["всегда", "вечно", "типичный"],
            "explanation": "Вы используете негативные ярлыки вместо описания конкретного поведения",
            "therapeutic": "Что именно произошло? Опишите действие, а не характер человека"
        },

        "mental_filter": {
            "name": "Ментальный фильтр",
            "patterns": [
                r"\bтолько\s+плох\w*\b", r"\bвижу\s+только\b",
                r"\bодин\s+минус\b", r"\bвсё\s+плох\w*\b",
                r"\bничего\s+хорошего\b", r"\bни\s+одного\s+плюса\b"
            ],
            "context_words": ["замечаю", "вижу", "помню"],
            "explanation": "Вы фокусируетесь только на негативном, игнорируя позитивное",
            "therapeutic": "Какие три позитивных момента были в этой ситуации?"
        },

        "mind_reading": {
            "name": "Чтение мыслей",
            "patterns": [
                r"\bон\s+думает\b", r"\bона\s+думает\b", r"\bони\s+думают\b",
                r"\bвсе\s+считают\b", r"\bон\s+наверное\b.*\bдумает\b",
                r"\bточно\s+знаю\b.*\bдумает\b", r"\bуверен\w*\b.*\bсчитает\b"
            ],
            "context_words": ["про меня", "обо мне", "что я"],
            "explanation": "Вы предполагаете, что знаете мысли других без доказательств",
            "therapeutic": "Откуда вы знаете, что он/она думает именно так? Спрашивали?"
        },

        "overgeneralization": {
            "name": "Сверхобобщение",
            "patterns": [
                r"\bвсегда\s+так\b", r"\bникогда\s+не\b", r"\bкаждый\s+раз\b",
                r"\bопять\s+двадцать\s+пять\b", r"\bкак\s+обычно\b",
                r"\bвечно\b", r"\bпостоянно\b", r"\bтипичн\w*\b"
            ],
            "context_words": ["я", "мне", "у меня", "со мной"],
            "explanation": "Вы делаете глобальный вывод из одного случая",
            "therapeutic": "Это действительно происходит каждый раз? Были ли исключения?"
        },

        "personalization": {
            "name": "Персонализация",
            "patterns": [
                r"\bиз-за\s+меня\b", r"\bмоя\s+вина\b", r"\bя\s+виноват\w*\b",
                r"\bэто\s+всё\s+я\b", r"\bесли\s+бы\s+не\s+я\b",
                r"\bна\s+мне\b.*\bответственность\b"
            ],
            "context_words": ["произошло", "случилось", "сделал"],
            "explanation": "Вы берёте на себя ответственность за то, что не контролируете",
            "therapeutic": "Какие факторы повлияли на эту ситуацию помимо вас?"
        },

        "should_statements": {
            "name": "Долженствование",
            "patterns": [
                r"\bя\s+должен\b", r"\bя\s+должна\b", r"\bобязан\w*\b",
                r"\bнадо\s+было\b", r"\bнужно\s+было\b", r"\bследовало\b",
                r"\bне\s+должен\b.*\bбыл\b", r"\bкак\s+я\s+мог\b"
            ],
            "context_words": ["себя", "чувствовать", "вести"],
            "explanation": "Вы критикуете себя жёсткими правилами 'должен/обязан'",
            "therapeutic": "Замените 'должен' на 'хотел бы'. Как изменится ощущение?"
        },

        "tunnel_vision": {
            "name": "Туннельное зрение",
            "patterns": [
                r"\bвижу\s+только\b", r"\bединственн\w*\b.*\bвыход\b",
                r"\bнет\s+другого\s+способа\b", r"\bтолько\s+один\s+вариант\b",
                r"\bничего\s+не\s+поделаешь\b"
            ],
            "context_words": ["вариант", "способ", "решение"],
            "explanation": "Вы видите только один аспект ситуации",
            "therapeutic": "Какие ещё варианты есть? Что бы посоветовал друг?"
        },

        "unfair_comparison": {
            "name": "Несправедливое сравнение",
            "patterns": [
                r"\bв\s+отличие\s+от\b", r"\bу\s+всех\b.*\bа\s+у\s+меня\b",
                r"\bдругие\s+\w+\s+а\s+я\b", r"\bвсе\s+уже\b.*\bа\s+я\b",
                r"\bмне\s+не\s+дано\b", r"\bхуже\s+чем\s+у\s+других\b"
            ],
            "context_words": ["успешнее", "лучше", "красивее", "умнее"],
            "explanation": "Вы сравниваете себя с другими не в свою пользу",
            "therapeutic": "Сравнивайте себя с собой вчерашним. Какой рост вы видите?"
        },

        "fortune_telling": {
            "name": "Предсказание будущего",
            "patterns": [
                r"\bточно\s+знаю\b.*\bбудет\b", r"\bэто\s+никогда\s+не\s+\w+\b",
                r"\bничего\s+не\s+выйдет\b", r"\bне\s+получится\b",
                r"\bобречён\w*\b", r"\bбесполезно\s+пытаться\b"
            ],
            "context_words": ["завтра", "потом", "в будущем"],
            "explanation": "Вы предсказываете негативный исход без оснований",
            "therapeutic": "Какие доказательства, что именно так и будет? Были ли приятные неожиданности?"
        },

        "magnification": {
            "name": "Магнификация/Минимизация",
            "patterns": [
                r"\bэто\s+ужасно\b", r"\bневыносим\w*\b", r"\bнестерпим\w*\b",
                r"\bне\s+могу\s+вынести\b", r"\bслишком\s+\w+\b",
                r"\bэто\s+ерунда\b.*\bдостижени\w*\b"
            ],
            "context_words": [],
            "explanation": "Вы преувеличиваете негатив или преуменьшаете позитив",
            "therapeutic": "По шкале 1-10, насколько серьёзна эта проблема через год?"
        },

        "perfectionism": {
            "name": "Перфекционизм",
            "patterns": [
                r"\bидеальн\w*\b", r"\bбез\s+ошибок\b", r"\bне\s+имею\s+права\b",
                r"\bна\s+100%\b", r"\bбезупречн\w*\b", r"\bсовершенств\w*\b",
                r"\bвсё\s+или\s+ничего\b"
            ],
            "context_words": ["должен", "обязан", "необходимо"],
            "explanation": "Вы устанавливаете нереалистично высокие стандарты",
            "therapeutic": "Что достаточно хорошо? 80% - это тоже отличный результат"
        }
    }

    def __init__(self):
        """Инициализация детектора"""
        self._compile_patterns()
        logger.info("CognitiveDistortionDetector initialized with 15 distortion types")

    def _compile_patterns(self):
        """Компилирует regex паттерны для быстрого поиска"""
        self._compiled_patterns = {}
        for distortion_id, distortion_data in self.DISTORTION_PATTERNS.items():
            patterns = distortion_data["patterns"]
            # Компилируем каждый паттерн отдельно для лучшей производительности
            self._compiled_patterns[distortion_id] = [
                re.compile(pattern, re.IGNORECASE | re.UNICODE)
                for pattern in patterns
            ]

    def detect(self, text: str) -> List[DetectedDistortion]:
        """
        Обнаруживает когнитивные искажения в тексте

        Args:
            text: Текст пользователя для анализа

        Returns:
            Список обнаруженных искажений с confidence > 0.4
        """
        if not text or len(text) < 10:
            return []

        detected = []
        text_lower = text.lower()

        for distortion_id, compiled_patterns in self._compiled_patterns.items():
            distortion_data = self.DISTORTION_PATTERNS[distortion_id]

            # Ищем совпадения паттернов
            matches = []
            for pattern in compiled_patterns:
                found = pattern.findall(text)
                if found:
                    matches.extend(found)

            if not matches:
                continue

            # Вычисляем confidence на основе количества совпадений
            base_confidence = min(0.4 + len(matches) * 0.15, 0.95)

            # Повышаем confidence если есть контекстные слова
            context_words = distortion_data.get("context_words", [])
            context_boost = 0
            for word in context_words:
                if word.lower() in text_lower:
                    context_boost += 0.1

            final_confidence = min(base_confidence + context_boost, 0.98)

            # Формируем evidence - берём первое совпадение
            evidence = matches[0] if isinstance(matches[0], str) else str(matches[0])

            detected.append(DetectedDistortion(
                distortion_type=distortion_data["name"],
                confidence=final_confidence,
                evidence=evidence,
                explanation=distortion_data["explanation"],
                therapeutic_response=distortion_data["therapeutic"]
            ))

        # Сортируем по confidence
        detected.sort(key=lambda x: x.confidence, reverse=True)

        if detected:
            logger.info(f"Detected {len(detected)} cognitive distortions: "
                       f"{[d.distortion_type for d in detected]}")

        return detected

    def detect_with_ai(self, text: str, ai_analysis: Optional[Dict[str, Any]] = None) -> List[DetectedDistortion]:
        """
        Расширенная детекция с использованием AI-анализа

        Комбинирует паттерн-матчинг с результатами AI анализа
        для более точной детекции

        Args:
            text: Текст пользователя
            ai_analysis: Результат AI анализа (psychological_insights, emotional_state)

        Returns:
            Расширенный список искажений
        """
        # Базовая детекция
        distortions = self.detect(text)

        if not ai_analysis:
            return distortions

        # Усиливаем confidence на основе AI анализа
        emotional_state = ai_analysis.get("emotional_state", "")
        insights = ai_analysis.get("psychological_insights", "")

        # Негативные эмоции повышают вероятность искажений
        negative_emotions = ["тревога", "грусть", "страх", "гнев", "вина", "стыд", "отчаяние"]
        emotion_boost = 0
        for emotion in negative_emotions:
            if emotion in emotional_state.lower():
                emotion_boost = 0.1
                break

        # Обновляем confidence с учётом эмоций
        for distortion in distortions:
            distortion.confidence = min(distortion.confidence + emotion_boost, 0.99)

        return distortions

    def get_therapeutic_summary(self, distortions: List[DetectedDistortion]) -> str:
        """
        Формирует терапевтический summary для пользователя

        Args:
            distortions: Список обнаруженных искажений

        Returns:
            Мягкий, поддерживающий текст о найденных паттернах
        """
        if not distortions:
            return ""

        # Берём топ-2 искажения
        top_distortions = distortions[:2]

        summary_parts = []

        if len(top_distortions) == 1:
            d = top_distortions[0]
            summary_parts.append(
                f"Я заметил паттерн мышления: **{d.distortion_type}**. "
                f"{d.explanation}. "
                f"\n\n{d.therapeutic_response}"
            )
        else:
            summary_parts.append("Я заметил несколько паттернов в вашем мышлении:\n")
            for i, d in enumerate(top_distortions, 1):
                summary_parts.append(f"\n**{i}. {d.distortion_type}**")
                summary_parts.append(f"   {d.explanation}")
                summary_parts.append(f"   → {d.therapeutic_response}")

        return "\n".join(summary_parts)

    def format_for_storage(self, distortions: List[DetectedDistortion]) -> List[Dict[str, Any]]:
        """
        Форматирует искажения для сохранения в PostgreSQL

        Args:
            distortions: Список обнаруженных искажений

        Returns:
            Список словарей для JSONB storage
        """
        return [
            {
                "type": d.distortion_type,
                "confidence": round(d.confidence, 2),
                "evidence": d.evidence,
                "explanation": d.explanation
            }
            for d in distortions
        ]


# Singleton instance
_detector = None

def get_distortion_detector() -> CognitiveDistortionDetector:
    """Get singleton CognitiveDistortionDetector instance"""
    global _detector
    if _detector is None:
        _detector = CognitiveDistortionDetector()
    return _detector


# Пример использования
if __name__ == "__main__":
    detector = get_distortion_detector()

    # Тестовые примеры
    test_texts = [
        "Я никогда ничего не добьюсь, я полный неудачник",
        "Если я не сделаю это идеально, всё будет ужасно",
        "Он наверное думает что я тупой",
        "У всех нормальная жизнь, а я одна страдаю",
        "Это моя вина что проект провалился",
        "Я должен был знать лучше, как я мог так поступить"
    ]

    for text in test_texts:
        print(f"\n{'='*50}")
        print(f"Текст: {text}")
        print(f"{'='*50}")

        distortions = detector.detect(text)

        if distortions:
            for d in distortions:
                print(f"\n  {d.distortion_type} ({d.confidence:.0%})")
                print(f"  Evidence: {d.evidence}")
                print(f"  → {d.therapeutic_response}")
        else:
            print("  Когнитивные искажения не обнаружены")
