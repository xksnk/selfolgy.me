"""
Domain Events Schema for Event-Driven Architecture

Определяет все события (events) используемые в системе с Pydantic валидацией.

Features:
- Event versioning (V1, V2, ...)
- Strict schema validation
- Type safety
- Auto-generated documentation
- Backward compatibility

Events в системе:
- user.* - события пользователя
- onboarding.* - события онбординга
- analysis.* - события анализа
- profile.* - события профиля
- coach.* - события коучинга
- system.* - системные события

Usage:
    from core.domain_events import UserAnswerSubmittedEventV1

    event = UserAnswerSubmittedEventV1(
        user_id=123,
        question_id="q_001",
        answer_text="My answer",
        trace_id="req_abc"
    )

    # Publish
    await event_bus.publish(event.event_type, event.dict())
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum

from pydantic import BaseModel, Field, validator


class EventVersion(str, Enum):
    """Версии событий"""
    V1 = "v1"
    V2 = "v2"


class EventPriority(str, Enum):
    """Приоритет события"""
    CRITICAL = "critical"  # Обработать немедленно
    HIGH = "high"          # Важное событие
    NORMAL = "normal"      # Обычное событие
    LOW = "low"            # Низкий приоритет


# ============================================================================
# BASE EVENT
# ============================================================================

class BaseDomainEvent(BaseModel):
    """
    Базовый класс для всех domain events

    Каждое событие должно наследоваться от этого класса
    """
    event_type: str = Field(..., description="Тип события (user.created)")
    version: EventVersion = Field(EventVersion.V1, description="Версия события")
    timestamp: datetime = Field(default_factory=datetime.now, description="Время создания")
    trace_id: Optional[str] = Field(None, description="Trace ID для distributed tracing")
    priority: EventPriority = Field(EventPriority.NORMAL, description="Приоритет обработки")

    class Config:
        """Pydantic config"""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============================================================================
# USER EVENTS
# ============================================================================

class UserCreatedEventV1(BaseDomainEvent):
    """Событие: создан новый пользователь"""
    event_type: str = Field("user.created", const=True)
    user_id: int = Field(..., description="ID пользователя")
    telegram_id: int = Field(..., description="Telegram ID")
    username: Optional[str] = Field(None, description="Telegram username")
    first_name: Optional[str] = Field(None, description="Имя")
    language_code: Optional[str] = Field("ru", description="Язык интерфейса")


class UserUpdatedEventV1(BaseDomainEvent):
    """Событие: обновлены данные пользователя"""
    event_type: str = Field("user.updated", const=True)
    user_id: int = Field(..., description="ID пользователя")
    updated_fields: List[str] = Field(..., description="Обновленные поля")
    old_values: Dict[str, Any] = Field({}, description="Старые значения")
    new_values: Dict[str, Any] = Field(..., description="Новые значения")


# ============================================================================
# ONBOARDING EVENTS
# ============================================================================

class OnboardingStartedEventV1(BaseDomainEvent):
    """Событие: начат онбординг"""
    event_type: str = Field("onboarding.started", const=True)
    user_id: int = Field(..., description="ID пользователя")
    session_id: int = Field(..., description="ID сессии онбординга")
    strategy: str = Field(..., description="Стратегия роутинга (ENTRY, EXPLORATION, etc)")


class QuestionSelectedEventV1(BaseDomainEvent):
    """Событие: выбран следующий вопрос"""
    event_type: str = Field("onboarding.question.selected", const=True)
    user_id: int = Field(..., description="ID пользователя")
    session_id: int = Field(..., description="ID сессии")
    question_id: str = Field(..., description="ID вопроса")
    question_text: str = Field(..., description="Текст вопроса")
    domain: str = Field(..., description="Психологический домен")
    depth_level: str = Field(..., description="Уровень глубины")
    energy_type: str = Field(..., description="Энергетика вопроса")


class UserAnswerSubmittedEventV1(BaseDomainEvent):
    """Событие: пользователь отправил ответ"""
    event_type: str = Field("user.answer.submitted", const=True)
    priority: EventPriority = Field(EventPriority.HIGH, const=True)

    user_id: int = Field(..., description="ID пользователя")
    session_id: int = Field(..., description="ID сессии")
    question_id: str = Field(..., description="ID вопроса")
    answer_text: str = Field(..., description="Текст ответа")
    answer_length: int = Field(..., description="Длина ответа (символов)")
    response_time_seconds: Optional[float] = Field(None, description="Время ответа")

    @validator('answer_length', always=True)
    def set_answer_length(cls, v, values):
        """Auto-calculate answer_length"""
        if v is None and 'answer_text' in values:
            return len(values['answer_text'])
        return v


class FatigueDetectedEventV1(BaseDomainEvent):
    """Событие: обнаружена усталость пользователя"""
    event_type: str = Field("onboarding.fatigue.detected", const=True)
    priority: EventPriority = Field(EventPriority.HIGH, const=True)

    user_id: int = Field(..., description="ID пользователя")
    session_id: int = Field(..., description="ID сессии")
    fatigue_level: str = Field(..., description="Уровень усталости (MILD, MODERATE, SEVERE)")
    answers_count: int = Field(..., description="Количество ответов в сессии")
    session_duration_minutes: float = Field(..., description="Длительность сессии")
    indicators: List[str] = Field(..., description="Индикаторы усталости")


class OnboardingCompletedEventV1(BaseDomainEvent):
    """Событие: онбординг завершен"""
    event_type: str = Field("onboarding.completed", const=True)
    user_id: int = Field(..., description="ID пользователя")
    session_id: int = Field(..., description="ID сессии")
    total_questions: int = Field(..., description="Всего вопросов")
    total_answers: int = Field(..., description="Всего ответов")
    duration_minutes: float = Field(..., description="Длительность онбординга")
    completion_rate: float = Field(..., description="Процент завершения")


# ============================================================================
# ANALYSIS EVENTS
# ============================================================================

class AnalysisRequestedEventV1(BaseDomainEvent):
    """Событие: запрошен анализ ответа"""
    event_type: str = Field("analysis.requested", const=True)
    priority: EventPriority = Field(EventPriority.HIGH, const=True)

    user_id: int = Field(..., description="ID пользователя")
    answer_id: int = Field(..., description="ID ответа")
    question_id: str = Field(..., description="ID вопроса")
    answer_text: str = Field(..., description="Текст ответа")
    analysis_type: str = Field("deep", description="Тип анализа (instant/deep)")


class AnalysisCompletedEventV1(BaseDomainEvent):
    """Событие: анализ ответа завершен"""
    event_type: str = Field("analysis.completed", const=True)

    user_id: int = Field(..., description="ID пользователя")
    answer_id: int = Field(..., description="ID ответа")
    analysis_id: int = Field(..., description="ID результата анализа")

    # Извлеченные черты личности
    extracted_traits: Dict[str, float] = Field(
        ...,
        description="Извлеченные черты (trait_name → score)"
    )

    # Метрики анализа
    confidence_scores: Dict[str, float] = Field(
        {},
        description="Confidence scores для каждой черты"
    )

    analysis_duration_seconds: float = Field(..., description="Время анализа")
    ai_model_used: str = Field(..., description="Модель AI использованная для анализа")


class AnalysisFailedEventV1(BaseDomainEvent):
    """Событие: ошибка анализа"""
    event_type: str = Field("analysis.failed", const=True)
    priority: EventPriority = Field(EventPriority.CRITICAL, const=True)

    user_id: int = Field(..., description="ID пользователя")
    answer_id: int = Field(..., description="ID ответа")
    error_type: str = Field(..., description="Тип ошибки")
    error_message: str = Field(..., description="Сообщение об ошибке")
    retry_count: int = Field(0, description="Количество попыток")


# ============================================================================
# PROFILE EVENTS
# ============================================================================

class ProfileCreatedEventV1(BaseDomainEvent):
    """Событие: создан профиль личности"""
    event_type: str = Field("profile.created", const=True)
    user_id: int = Field(..., description="ID пользователя")
    profile_id: int = Field(..., description="ID профиля")
    initial_traits: Dict[str, float] = Field(..., description="Начальные черты")


class ProfileUpdatedEventV1(BaseDomainEvent):
    """Событие: обновлен профиль личности"""
    event_type: str = Field("profile.updated", const=True)

    user_id: int = Field(..., description="ID пользователя")
    profile_id: int = Field(..., description="ID профиля")

    # Какие черты изменились
    updated_traits: Dict[str, float] = Field(
        ...,
        description="Обновленные черты (trait_name → new_score)"
    )

    previous_traits: Dict[str, float] = Field(
        {},
        description="Предыдущие значения черт"
    )

    # Метаданные
    update_source: str = Field(..., description="Источник обновления (analysis/coach/manual)")
    confidence_delta: float = Field(0.0, description="Изменение уверенности")


class TraitHistoryRecordedEventV1(BaseDomainEvent):
    """Событие: записана история изменения черты"""
    event_type: str = Field("profile.trait.history", const=True)
    user_id: int = Field(..., description="ID пользователя")
    profile_id: int = Field(..., description="ID профиля")
    trait_name: str = Field(..., description="Название черты")
    old_value: float = Field(..., description="Старое значение")
    new_value: float = Field(..., description="Новое значение")
    change_reason: str = Field(..., description="Причина изменения")


# ============================================================================
# VECTOR EVENTS
# ============================================================================

class VectorUpdatedEventV1(BaseDomainEvent):
    """Событие: обновлен векторный профиль в Qdrant"""
    event_type: str = Field("vector.updated", const=True)
    user_id: int = Field(..., description="ID пользователя")
    collection_name: str = Field(..., description="Название коллекции Qdrant")
    vector_id: str = Field(..., description="ID вектора")
    dimension: int = Field(..., description="Размерность вектора")
    update_type: str = Field(..., description="Тип обновления (create/update/delete)")


# ============================================================================
# COACH EVENTS
# ============================================================================

class CoachSessionStartedEventV1(BaseDomainEvent):
    """Событие: начата сессия с AI коучем"""
    event_type: str = Field("coach.session.started", const=True)
    user_id: int = Field(..., description="ID пользователя")
    session_id: int = Field(..., description="ID сессии коучинга")
    context_loaded: bool = Field(..., description="Загружен ли контекст из Qdrant")


class CoachMessageSentEventV1(BaseDomainEvent):
    """Событие: отправлено сообщение в коучинг"""
    event_type: str = Field("coach.message.sent", const=True)
    user_id: int = Field(..., description="ID пользователя")
    session_id: int = Field(..., description="ID сессии")
    message_id: int = Field(..., description="ID сообщения")
    role: str = Field(..., description="Роль (user/assistant)")
    message_length: int = Field(..., description="Длина сообщения")


class InsightGeneratedEventV1(BaseDomainEvent):
    """Событие: сгенерирован инсайт"""
    event_type: str = Field("coach.insight.generated", const=True)
    user_id: int = Field(..., description="ID пользователя")
    insight_id: int = Field(..., description="ID инсайта")
    insight_type: str = Field(..., description="Тип инсайта")
    insight_text: str = Field(..., description="Текст инсайта")
    confidence: float = Field(..., description="Confidence score")
    based_on_traits: List[str] = Field(..., description="Черты на которых основан")


# ============================================================================
# SYSTEM EVENTS
# ============================================================================

class SystemErrorEventV1(BaseDomainEvent):
    """Событие: системная ошибка"""
    event_type: str = Field("system.error", const=True)
    priority: EventPriority = Field(EventPriority.CRITICAL, const=True)

    service_name: str = Field(..., description="Название сервиса")
    error_type: str = Field(..., description="Тип ошибки")
    error_message: str = Field(..., description="Сообщение об ошибке")
    stack_trace: Optional[str] = Field(None, description="Stack trace")
    affected_user_id: Optional[int] = Field(None, description="Затронутый пользователь")


class SystemHealthCheckEventV1(BaseDomainEvent):
    """Событие: health check системы"""
    event_type: str = Field("system.health", const=True)
    priority: EventPriority = Field(EventPriority.LOW, const=True)

    service_name: str = Field(..., description="Название сервиса")
    status: str = Field(..., description="Статус (healthy/degraded/unhealthy)")
    checks: Dict[str, str] = Field(..., description="Результаты проверок")
    metrics: Dict[str, float] = Field({}, description="Метрики")


# ============================================================================
# EVENT REGISTRY
# ============================================================================

class EventRegistry:
    """
    Реестр всех событий в системе

    Используется для:
    - Валидации событий
    - Auto-completion в IDE
    - Документации
    - Версионирование
    """

    # Маппинг event_type → Event Class
    _events = {
        # User events
        "user.created": UserCreatedEventV1,
        "user.updated": UserUpdatedEventV1,

        # Onboarding events
        "onboarding.started": OnboardingStartedEventV1,
        "onboarding.question.selected": QuestionSelectedEventV1,
        "user.answer.submitted": UserAnswerSubmittedEventV1,
        "onboarding.fatigue.detected": FatigueDetectedEventV1,
        "onboarding.completed": OnboardingCompletedEventV1,

        # Analysis events
        "analysis.requested": AnalysisRequestedEventV1,
        "analysis.completed": AnalysisCompletedEventV1,
        "analysis.failed": AnalysisFailedEventV1,

        # Profile events
        "profile.created": ProfileCreatedEventV1,
        "profile.updated": ProfileUpdatedEventV1,
        "profile.trait.history": TraitHistoryRecordedEventV1,

        # Vector events
        "vector.updated": VectorUpdatedEventV1,

        # Coach events
        "coach.session.started": CoachSessionStartedEventV1,
        "coach.message.sent": CoachMessageSentEventV1,
        "coach.insight.generated": InsightGeneratedEventV1,

        # System events
        "system.error": SystemErrorEventV1,
        "system.health": SystemHealthCheckEventV1,
    }

    @classmethod
    def get_event_class(cls, event_type: str) -> Optional[type[BaseDomainEvent]]:
        """Возвращает класс события по типу"""
        return cls._events.get(event_type)

    @classmethod
    def validate_event(cls, event_type: str, payload: Dict[str, Any]) -> BaseDomainEvent:
        """
        Валидирует и парсит событие

        Args:
            event_type: Тип события
            payload: Данные события

        Returns:
            Validated event instance

        Raises:
            ValueError: Если event_type неизвестен
            ValidationError: Если payload не валиден
        """
        event_class = cls.get_event_class(event_type)

        if event_class is None:
            raise ValueError(f"Unknown event type: {event_type}")

        return event_class(**payload)

    @classmethod
    def list_events(cls) -> List[str]:
        """Возвращает список всех event_type"""
        return list(cls._events.keys())

    @classmethod
    def get_event_schema(cls, event_type: str) -> Optional[Dict[str, Any]]:
        """Возвращает JSON schema для события"""
        event_class = cls.get_event_class(event_type)
        if event_class:
            return event_class.schema()
        return None


# Convenience functions
def create_event(event_type: str, **kwargs) -> BaseDomainEvent:
    """
    Фабричная функция для создания событий

    Args:
        event_type: Тип события
        **kwargs: Поля события

    Returns:
        Event instance

    Example:
        event = create_event(
            "user.answer.submitted",
            user_id=123,
            question_id="q_001",
            answer_text="My answer"
        )
    """
    return EventRegistry.validate_event(event_type, kwargs)


def serialize_event(event: BaseDomainEvent) -> Dict[str, Any]:
    """Сериализует событие в dict для публикации"""
    return event.dict(exclude_none=True)
