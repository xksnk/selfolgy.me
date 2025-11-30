"""
DossierValidator - Валидация и коррекция досье пользователя.

Два механизма:
1. CorrectionDetector - автодетекция коррекций в сообщениях
2. CheckInManager - периодические check-in для валидации фактов

Принцип: Коуч не должен упорствовать в ошибках.
Если пользователь говорит "это не так" - принимаем и обновляем.
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class CorrectionType(Enum):
    """Тип коррекции"""
    FACT_WRONG = "fact_wrong"           # Факт неверный
    OUTDATED = "outdated"               # Информация устарела
    MISUNDERSTOOD = "misunderstood"     # Неправильно понял
    PARTIAL = "partial"                 # Частично верно


@dataclass
class DetectedCorrection:
    """Обнаруженная коррекция"""
    detected: bool = False
    correction_type: Optional[CorrectionType] = None
    original_claim: str = ""            # Что коуч сказал
    user_correction: str = ""           # Что пользователь исправил
    confidence: float = 0.0             # Уверенность в детекции
    suggested_response: str = ""        # Рекомендуемый ответ коуча


@dataclass
class CheckInItem:
    """Элемент для check-in"""
    fact_type: str                      # goal, barrier, value, etc.
    fact_text: str                      # Текст факта
    added_at: datetime                  # Когда добавлен
    last_validated: Optional[datetime] = None
    validation_count: int = 0
    still_relevant: bool = True


@dataclass
class CheckInRequest:
    """Запрос на check-in"""
    needed: bool = False
    items: List[CheckInItem] = field(default_factory=list)
    question: str = ""
    priority: str = "normal"            # normal, high (если давно не проверяли)


class CorrectionDetector:
    """
    Детектор коррекций в сообщениях пользователя.

    Ловит:
    - "нет, на самом деле..."
    - "это не так, я..."
    - "ты ошибаешься"
    - "это было раньше, сейчас..."
    """

    # Маркеры прямой коррекции
    DIRECT_CORRECTION_MARKERS = [
        r'нет[,.]?\s*(на самом деле|это не так)',
        r'это\s+(не\s+так|неверно|неправда|ошибка)',
        r'ты\s+(ошиб|не\s*прав|путаешь)',
        r'я\s+не\s+(говорил|имел|хотел)',
        r'ты\s+меня\s+(не\s*понял|неправильно)',
    ]

    # Маркеры устаревшей информации
    OUTDATED_MARKERS = [
        r'это\s+было\s+(раньше|давно|в прошлом)',
        r'(раньше|когда-то)\s+да[,.]?\s+(но\s+)?сейчас',
        r'уже\s+(не|нет)',
        r'больше\s+не',
        r'с\s+тех\s+пор\s+(изменил|поменял)',
        r'теперь\s+(по-другому|иначе)',
    ]

    # Маркеры частичной коррекции
    PARTIAL_MARKERS = [
        r'не\s+совсем\s+(так|верно|правильно)?',
        r'частично\s+(да|верно)',
        r'в\s+целом\s+да[,.]?\s+но',
        r'скорее',
        r'точнее\s+будет',
    ]

    def __init__(self):
        # Компилируем регулярки
        self._direct_patterns = [re.compile(p, re.IGNORECASE) for p in self.DIRECT_CORRECTION_MARKERS]
        self._outdated_patterns = [re.compile(p, re.IGNORECASE) for p in self.OUTDATED_MARKERS]
        self._partial_patterns = [re.compile(p, re.IGNORECASE) for p in self.PARTIAL_MARKERS]

        logger.info("🔍 CorrectionDetector initialized")

    def detect(
        self,
        user_message: str,
        last_coach_message: Optional[str] = None
    ) -> DetectedCorrection:
        """
        Обнаружить коррекцию в сообщении пользователя.

        Args:
            user_message: Сообщение пользователя
            last_coach_message: Предыдущее сообщение коуча (для контекста)

        Returns:
            DetectedCorrection с результатами
        """
        result = DetectedCorrection()
        message_lower = user_message.lower()

        # 1. Проверяем прямую коррекцию
        for pattern in self._direct_patterns:
            if pattern.search(message_lower):
                result.detected = True
                result.correction_type = CorrectionType.FACT_WRONG
                result.confidence = 0.9
                result.user_correction = user_message
                break

        # 2. Проверяем устаревшую информацию
        if not result.detected:
            for pattern in self._outdated_patterns:
                if pattern.search(message_lower):
                    result.detected = True
                    result.correction_type = CorrectionType.OUTDATED
                    result.confidence = 0.85
                    result.user_correction = user_message
                    break

        # 3. Проверяем частичную коррекцию
        if not result.detected:
            for pattern in self._partial_patterns:
                if pattern.search(message_lower):
                    result.detected = True
                    result.correction_type = CorrectionType.PARTIAL
                    result.confidence = 0.7
                    result.user_correction = user_message
                    break

        # 4. Если обнаружена коррекция - формируем рекомендуемый ответ
        if result.detected:
            result.suggested_response = self._generate_response(result.correction_type)
            result.original_claim = last_coach_message[:200] if last_coach_message else ""

            logger.info(f"🔍 Detected correction: {result.correction_type.value}, "
                       f"confidence={result.confidence}")

        return result

    def _generate_response(self, correction_type: CorrectionType) -> str:
        """Сгенерировать рекомендуемый ответ на коррекцию"""
        responses = {
            CorrectionType.FACT_WRONG:
                "Спасибо что поправил. Расскажи, как на самом деле?",
            CorrectionType.OUTDATED:
                "Понял, ситуация изменилась. Как обстоят дела сейчас?",
            CorrectionType.MISUNDERSTOOD:
                "Прошу прощения за неточность. Помоги мне лучше понять.",
            CorrectionType.PARTIAL:
                "Понял, уточни пожалуйста.",
        }
        return responses.get(correction_type, "Понял, расскажи подробнее.")


class CheckInManager:
    """
    Менеджер периодических check-in для валидации досье.

    Логика:
    - Цели старше 30 дней → спросить "Актуально ли ещё?"
    - После 5 сессий без валидации → check-in
    - Приоритет: goals > barriers > values
    """

    # Настройки check-in
    GOAL_VALIDATION_DAYS = 30           # Проверять цели каждые 30 дней
    BARRIER_VALIDATION_DAYS = 45        # Барьеры реже (они стабильнее)
    VALUE_VALIDATION_DAYS = 90          # Ценности ещё реже
    SESSIONS_BEFORE_CHECKIN = 5         # Или после 5 сессий

    # Шаблоны вопросов
    CHECK_IN_TEMPLATES = {
        'goal': [
            'Ты упоминал цель "{text}". Это всё ещё актуально для тебя?',
            'Как продвигается "{text}"? Это по-прежнему важно?',
            'Помню, ты хотел "{text}". Что-то изменилось?',
        ],
        'barrier': [
            'Ты говорил, что мешает "{text}". Это всё ещё так?',
            'Как сейчас обстоят дела с "{text}"?',
        ],
        'value': [
            '"{text}" — это по-прежнему важная для тебя ценность?',
        ],
        'identity': [
            'Ты описывал себя как "{text}". Это актуально?',
        ],
    }

    def __init__(self, db_pool=None):
        self.db_pool = db_pool
        self._validation_history: Dict[int, Dict[str, datetime]] = {}
        self._session_counts: Dict[int, int] = {}

        logger.info("✅ CheckInManager initialized")

    def increment_session(self, user_id: int):
        """Увеличить счётчик сессий для пользователя"""
        self._session_counts[user_id] = self._session_counts.get(user_id, 0) + 1

    async def should_check_in(self, user_id: int, dossier) -> CheckInRequest:
        """
        Определить нужен ли check-in.

        Args:
            user_id: ID пользователя
            dossier: UserDossier с текущими данными

        Returns:
            CheckInRequest с информацией о необходимости check-in
        """
        request = CheckInRequest()
        items_to_check = []

        # Проверяем счётчик сессий
        sessions = self._session_counts.get(user_id, 0)
        time_based_check = sessions >= self.SESSIONS_BEFORE_CHECKIN

        if time_based_check:
            # Сбрасываем счётчик
            self._session_counts[user_id] = 0

        # Собираем элементы для проверки
        now = datetime.now()

        # Цели (приоритет высокий)
        if dossier and dossier.top_goals:
            for goal in dossier.top_goals[:2]:  # Проверяем топ-2 цели
                item = CheckInItem(
                    fact_type='goal',
                    fact_text=goal,
                    added_at=dossier.generated_at or now,
                )

                # Проверяем когда последний раз валидировали
                last_check = self._get_last_validation(user_id, 'goal', goal)
                if last_check:
                    days_since = (now - last_check).days
                    if days_since >= self.GOAL_VALIDATION_DAYS:
                        items_to_check.append(item)
                elif time_based_check:
                    items_to_check.append(item)

        # Барьеры (приоритет средний)
        if dossier and dossier.top_barriers and time_based_check:
            for barrier in dossier.top_barriers[:1]:  # Проверяем топ-1 барьер
                item = CheckInItem(
                    fact_type='barrier',
                    fact_text=barrier,
                    added_at=dossier.generated_at or now,
                )
                items_to_check.append(item)

        # Формируем запрос
        if items_to_check:
            request.needed = True
            request.items = items_to_check[:1]  # Один вопрос за раз
            request.question = self._format_check_in_question(items_to_check[0])
            request.priority = "high" if len(items_to_check) > 2 else "normal"

            logger.info(f"✅ Check-in needed for user {user_id}: {len(items_to_check)} items")

        return request

    def _get_last_validation(self, user_id: int, fact_type: str, fact_text: str) -> Optional[datetime]:
        """Получить время последней валидации факта"""
        key = f"{fact_type}:{fact_text[:50]}"
        user_history = self._validation_history.get(user_id, {})
        return user_history.get(key)

    def record_validation(self, user_id: int, fact_type: str, fact_text: str, still_relevant: bool):
        """Записать результат валидации"""
        key = f"{fact_type}:{fact_text[:50]}"

        if user_id not in self._validation_history:
            self._validation_history[user_id] = {}

        self._validation_history[user_id][key] = datetime.now()

        logger.info(f"✅ Recorded validation for user {user_id}: {fact_type} = {still_relevant}")

    def _format_check_in_question(self, item: CheckInItem) -> str:
        """Сформатировать вопрос для check-in"""
        import random

        templates = self.CHECK_IN_TEMPLATES.get(item.fact_type, ['"{text}" — это актуально?'])
        template = random.choice(templates)

        # Обрезаем текст если слишком длинный
        fact_text = item.fact_text[:80] + "..." if len(item.fact_text) > 80 else item.fact_text

        return template.format(text=fact_text)


class DossierValidator:
    """
    Главный класс валидации досье.

    Объединяет:
    - CorrectionDetector: реактивная коррекция
    - CheckInManager: проактивная валидация
    """

    def __init__(self, dossier_service=None, db_pool=None):
        self.dossier_service = dossier_service
        self.correction_detector = CorrectionDetector()
        self.check_in_manager = CheckInManager(db_pool)

        # История последних сообщений коуча (для контекста коррекций)
        self._last_coach_messages: Dict[int, str] = {}

        logger.info("🛡️ DossierValidator initialized")

    def set_last_coach_message(self, user_id: int, message: str):
        """Сохранить последнее сообщение коуча"""
        self._last_coach_messages[user_id] = message

    async def process_message(
        self,
        user_id: int,
        user_message: str,
        dossier=None
    ) -> Dict[str, Any]:
        """
        Обработать сообщение на предмет коррекций и check-in.

        Returns:
            {
                'correction_detected': bool,
                'correction': DetectedCorrection,
                'should_regenerate_dossier': bool,
                'check_in_needed': bool,
                'check_in_request': CheckInRequest,
                'response_prefix': str  # Добавить к ответу коуча
            }
        """
        result = {
            'correction_detected': False,
            'correction': None,
            'should_regenerate_dossier': False,
            'check_in_needed': False,
            'check_in_request': None,
            'response_prefix': ''
        }

        # 1. Проверяем на коррекцию
        last_coach_msg = self._last_coach_messages.get(user_id)
        correction = self.correction_detector.detect(user_message, last_coach_msg)

        if correction.detected:
            result['correction_detected'] = True
            result['correction'] = correction
            result['should_regenerate_dossier'] = True
            result['response_prefix'] = correction.suggested_response + "\n\n"

            # Инвалидируем досье
            if self.dossier_service:
                await self.dossier_service.invalidate_dossier(user_id)

        # 2. Проверяем нужен ли check-in (только если нет коррекции)
        if not correction.detected and dossier:
            check_in = await self.check_in_manager.should_check_in(user_id, dossier)
            if check_in.needed:
                result['check_in_needed'] = True
                result['check_in_request'] = check_in

        # 3. Увеличиваем счётчик сессий
        self.check_in_manager.increment_session(user_id)

        return result

    def handle_check_in_response(
        self,
        user_id: int,
        check_in_item: CheckInItem,
        user_response: str
    ) -> Tuple[bool, str]:
        """
        Обработать ответ пользователя на check-in.

        Returns:
            (still_relevant: bool, coach_response: str)
        """
        response_lower = user_response.lower()

        # Определяем ответ
        positive_markers = ['да', 'актуально', 'верно', 'так', 'конечно', 'ещё', 'всё ещё']
        negative_markers = ['нет', 'уже нет', 'изменил', 'не актуально', 'поменял', 'другое']

        still_relevant = any(m in response_lower for m in positive_markers)
        not_relevant = any(m in response_lower for m in negative_markers)

        if not_relevant:
            still_relevant = False

        # Записываем результат
        self.check_in_manager.record_validation(
            user_id,
            check_in_item.fact_type,
            check_in_item.fact_text,
            still_relevant
        )

        # Формируем ответ
        if still_relevant:
            coach_response = "Хорошо, учту что это по-прежнему актуально."
        else:
            coach_response = "Понял, обновлю информацию. Расскажи, как сейчас обстоят дела?"

        return still_relevant, coach_response
