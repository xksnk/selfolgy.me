"""
Question Selection Service - Microservice для выбора вопросов

Реализует Smart Mix алгоритм для интеллектуального подбора вопросов.

Features:
- 4 стратегии роутинга (ENTRY → EXPLORATION → DEEPENING → BALANCING)
- FatigueDetector для заботы о пользователе
- Управление энергетическим балансом (HEAVY → HEALING transitions)
- Trust Level Access Control
- Event-driven architecture через Event Bus
- Публикует события через Outbox Pattern

Architecture:
    user.session.started → QuestionSelectionService → question.selected

Events Consumed:
    - user.session.started
    - user.answer.submitted

Events Published:
    - question.selected
    - session.fatigue.detected
    - session.completed

Database Schema: selfology.question_selection
"""

import asyncio
import asyncpg
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
import random

from systems.base import BaseSystem, HealthStatus
from core.event_bus import EventBus
from core.outbox_pattern import OutboxPublisher
from core.domain_events import (
    QuestionSelectedEventV1,
    SessionCompletedEventV1,
    EventPriority
)

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================

class RoutingStrategy(str, Enum):
    """Стратегии выбора вопросов"""
    ENTRY = "entry"              # Начало: легкие вопросы
    EXPLORATION = "exploration"   # Исследование: разные домены
    DEEPENING = "deepening"       # Углубление: сложные вопросы
    BALANCING = "balancing"       # Баланс: mix стратегий


class EnergyLevel(str, Enum):
    """Энергетические уровни вопросов"""
    OPENING = "OPENING"      # +2 энергии
    NEUTRAL = "NEUTRAL"      # 0
    PROCESSING = "PROCESSING"  # -1
    HEAVY = "HEAVY"          # -2
    HEALING = "HEALING"      # +3


class TrustLevel(int, Enum):
    """Уровни доверия пользователя"""
    STRANGER = 0       # Только SURFACE вопросы
    ACQUAINTANCE = 1   # SURFACE + CONSCIOUS
    FRIEND = 2         # До EDGE
    TRUSTED = 3        # До SHADOW
    SOUL_MATE = 4      # Полный доступ (CORE)


# ============================================================================
# FATIGUE DETECTOR
# ============================================================================

class FatigueDetector:
    """
    Детектор усталости пользователя

    Анализирует:
    - Количество вопросов в сессии
    - Энергетический баланс
    - Скорость ответов
    - Длину ответов
    """

    def __init__(self):
        self.energy_threshold = -5  # Критический уровень усталости
        self.max_questions_per_session = 15

    async def check_fatigue(
        self,
        session_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Проверяет усталость пользователя

        Args:
            session_data: Данные сессии

        Returns:
            {
                "is_fatigued": bool,
                "reason": str,
                "recommendation": str,
                "energy_balance": int
            }
        """
        questions_answered = session_data.get("questions_answered", 0)
        energy_balance = session_data.get("energy_balance", 0)
        avg_answer_length = session_data.get("avg_answer_length", 0)

        # Проверка по количеству вопросов
        if questions_answered >= self.max_questions_per_session:
            return {
                "is_fatigued": True,
                "reason": "max_questions_reached",
                "recommendation": "Предложить завершить сессию",
                "energy_balance": energy_balance
            }

        # Проверка энергетического баланса
        if energy_balance <= self.energy_threshold:
            return {
                "is_fatigued": True,
                "reason": "low_energy",
                "recommendation": "Дать HEALING вопрос",
                "energy_balance": energy_balance
            }

        # Проверка длины ответов (усталость = короткие ответы)
        if questions_answered > 5 and avg_answer_length < 20:
            return {
                "is_fatigued": True,
                "reason": "short_answers",
                "recommendation": "Предложить паузу или HEALING вопрос",
                "energy_balance": energy_balance
            }

        return {
            "is_fatigued": False,
            "reason": None,
            "recommendation": "Продолжить нормально",
            "energy_balance": energy_balance
        }


# ============================================================================
# SMART MIX ALGORITHM
# ============================================================================

class SmartMixRouter:
    """
    Smart Mix Algorithm для выбора вопросов

    Балансирует:
    - Depth (глубина вопросов)
    - Energy (энергетическая нагрузка)
    - Domains (психологические домены)
    - Trust Level (уровень доверия)
    """

    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self.fatigue_detector = FatigueDetector()

    async def select_next_question(
        self,
        user_id: int,
        session_id: int,
        session_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Выбирает следующий вопрос по Smart Mix алгоритму

        Args:
            user_id: ID пользователя
            session_id: ID сессии
            session_data: Текущее состояние сессии

        Returns:
            Question data или None если сессия завершена
        """
        # Проверка усталости
        fatigue = await self.fatigue_detector.check_fatigue(session_data)

        if fatigue["is_fatigued"]:
            if fatigue["reason"] == "max_questions_reached":
                # Завершаем сессию
                return None

            if fatigue["reason"] == "low_energy":
                # Даем HEALING вопрос
                return await self._get_healing_question(user_id)

        # Определяем стратегию
        strategy = self._determine_strategy(session_data)

        # Выбираем вопрос по стратегии
        question = await self._select_by_strategy(
            user_id=user_id,
            strategy=strategy,
            session_data=session_data
        )

        return question

    def _determine_strategy(self, session_data: Dict[str, Any]) -> RoutingStrategy:
        """Определяет стратегию выбора вопроса"""
        questions_answered = session_data.get("questions_answered", 0)

        if questions_answered < 3:
            return RoutingStrategy.ENTRY
        elif questions_answered < 7:
            return RoutingStrategy.EXPLORATION
        elif questions_answered < 12:
            return RoutingStrategy.DEEPENING
        else:
            return RoutingStrategy.BALANCING

    async def _select_by_strategy(
        self,
        user_id: int,
        strategy: RoutingStrategy,
        session_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Выбирает вопрос по заданной стратегии"""
        trust_level = session_data.get("trust_level", TrustLevel.STRANGER.value)
        answered_questions = session_data.get("answered_question_ids", [])

        async with self.db_pool.acquire() as conn:
            if strategy == RoutingStrategy.ENTRY:
                # ENTRY: легкие SURFACE вопросы, OPENING energy
                question = await conn.fetchrow(
                    """
                    SELECT * FROM selfology.questions_metadata
                    WHERE depth_level = 'SURFACE'
                      AND energy_level = 'OPENING'
                      AND id != ALL($1::bigint[])
                      AND admin_status != 'needs_work'
                    ORDER BY RANDOM()
                    LIMIT 1
                    """,
                    answered_questions
                )

            elif strategy == RoutingStrategy.EXPLORATION:
                # EXPLORATION: разные домены, NEUTRAL/PROCESSING energy
                question = await conn.fetchrow(
                    """
                    SELECT * FROM selfology.questions_metadata
                    WHERE depth_level IN ('SURFACE', 'CONSCIOUS')
                      AND energy_level IN ('NEUTRAL', 'PROCESSING')
                      AND id != ALL($1::bigint[])
                      AND admin_status != 'needs_work'
                    ORDER BY RANDOM()
                    LIMIT 1
                    """,
                    answered_questions
                )

            elif strategy == RoutingStrategy.DEEPENING:
                # DEEPENING: глубокие вопросы с учетом trust level
                max_depth = self._get_max_depth_for_trust_level(trust_level)

                question = await conn.fetchrow(
                    """
                    SELECT * FROM selfology.questions_metadata
                    WHERE depth_level = $1
                      AND id != ALL($2::bigint[])
                      AND admin_status != 'needs_work'
                    ORDER BY RANDOM()
                    LIMIT 1
                    """,
                    max_depth,
                    answered_questions
                )

            else:  # BALANCING
                # BALANCING: mix стратегий для разнообразия
                question = await conn.fetchrow(
                    """
                    SELECT * FROM selfology.questions_metadata
                    WHERE id != ALL($1::bigint[])
                      AND admin_status != 'needs_work'
                    ORDER BY RANDOM()
                    LIMIT 1
                    """,
                    answered_questions
                )

            if question:
                return dict(question)
            else:
                # Fallback: любой вопрос
                question = await conn.fetchrow(
                    """
                    SELECT * FROM selfology.questions_metadata
                    WHERE id != ALL($1::bigint[])
                      AND admin_status != 'needs_work'
                    LIMIT 1
                    """,
                    answered_questions
                )
                return dict(question) if question else None

    async def _get_healing_question(self, user_id: int) -> Dict[str, Any]:
        """Получает HEALING вопрос для восстановления энергии"""
        async with self.db_pool.acquire() as conn:
            question = await conn.fetchrow(
                """
                SELECT * FROM selfology.questions_metadata
                WHERE energy_level = 'HEALING'
                  AND admin_status != 'needs_work'
                ORDER BY RANDOM()
                LIMIT 1
                """
            )
            return dict(question) if question else None

    def _get_max_depth_for_trust_level(self, trust_level: int) -> str:
        """Возвращает максимальную глубину для уровня доверия"""
        if trust_level >= TrustLevel.SOUL_MATE.value:
            return "CORE"
        elif trust_level >= TrustLevel.TRUSTED.value:
            return "SHADOW"
        elif trust_level >= TrustLevel.FRIEND.value:
            return "EDGE"
        elif trust_level >= TrustLevel.ACQUAINTANCE.value:
            return "CONSCIOUS"
        else:
            return "SURFACE"


# ============================================================================
# QUESTION SELECTION SERVICE
# ============================================================================

class QuestionSelectionService(BaseSystem):
    """
    Question Selection Service

    Микросервис для интеллектуального выбора вопросов.
    """

    def __init__(
        self,
        event_bus: EventBus,
        db_pool: asyncpg.Pool
    ):
        super().__init__(name="question_selection_service", event_bus=event_bus)

        self.db_pool = db_pool
        self.outbox_publisher = OutboxPublisher(schema="selfology")
        self.smart_mix_router = SmartMixRouter(db_pool)

    async def start(self):
        """Запускает Question Selection Service"""
        logger.info("Starting Question Selection Service...")

        # Event Consumers
        await self.add_event_consumer(
            event_types=["user.session.started"],
            handler=self.handle_session_started,
            consumer_name="question_selector_worker"
        )

        await self.add_event_consumer(
            event_types=["user.answer.submitted"],
            handler=self.handle_answer_submitted,
            consumer_name="answer_processor_worker"
        )

        self.state = self.state.RUNNING
        logger.info("✅ Question Selection Service started")

    async def stop(self):
        """Graceful shutdown"""
        logger.info("Stopping Question Selection Service...")
        await self.stop_all_consumers()
        logger.info("✅ Question Selection Service stopped")

    async def health_check(self) -> Dict[str, Any]:
        """Health check"""
        checks = {}

        # Database
        try:
            async with self.db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            checks["database"] = "healthy"
        except Exception:
            checks["database"] = "unhealthy"

        # Event Bus
        try:
            await self.event_bus.redis.ping()
            checks["event_bus"] = "healthy"
        except Exception:
            checks["event_bus"] = "unhealthy"

        status = HealthStatus.HEALTHY if all(
            v == "healthy" for v in checks.values()
        ) else HealthStatus.UNHEALTHY

        return {
            "status": status.value,
            "checks": checks,
            "metrics": self.get_metrics()
        }

    # ========================================================================
    # EVENT HANDLERS
    # ========================================================================

    async def handle_session_started(self, event_type: str, payload: Dict[str, Any]):
        """
        Обрабатывает начало сессии

        Выбирает первый вопрос и публикует событие question.selected
        """
        user_id = payload["user_id"]
        session_id = payload["session_id"]

        logger.info(f"Session started: user={user_id}, session={session_id}")

        # Инициализируем session_data
        session_data = {
            "questions_answered": 0,
            "energy_balance": 0,
            "trust_level": TrustLevel.STRANGER.value,
            "answered_question_ids": []
        }

        # Выбираем первый вопрос
        question = await self.smart_mix_router.select_next_question(
            user_id=user_id,
            session_id=session_id,
            session_data=session_data
        )

        if question:
            # Публикуем событие через Outbox
            await self._publish_question_selected(
                user_id=user_id,
                session_id=session_id,
                question=question,
                trace_id=payload.get("trace_id")
            )

        self.increment_metric("sessions_started")

    async def handle_answer_submitted(self, event_type: str, payload: Dict[str, Any]):
        """
        Обрабатывает ответ пользователя

        Выбирает следующий вопрос или завершает сессию
        """
        user_id = payload["user_id"]
        session_id = payload.get("session_id")

        # Загружаем session_data из БД
        session_data = await self._load_session_data(session_id)

        # Обновляем session_data
        session_data["questions_answered"] += 1
        session_data["answered_question_ids"].append(payload["question_id"])

        # Обновляем энергетический баланс
        # (Упрощенная логика - в продакшене нужно анализировать question energy)
        session_data["energy_balance"] -= 1

        # Выбираем следующий вопрос
        next_question = await self.smart_mix_router.select_next_question(
            user_id=user_id,
            session_id=session_id,
            session_data=session_data
        )

        if next_question:
            # Публикуем question.selected
            await self._publish_question_selected(
                user_id=user_id,
                session_id=session_id,
                question=next_question,
                trace_id=payload.get("trace_id")
            )

            # Сохраняем session_data
            await self._save_session_data(session_id, session_data)
        else:
            # Сессия завершена
            await self._publish_session_completed(
                user_id=user_id,
                session_id=session_id,
                trace_id=payload.get("trace_id")
            )

        self.increment_metric("answers_processed")

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    async def _publish_question_selected(
        self,
        user_id: int,
        session_id: int,
        question: Dict[str, Any],
        trace_id: Optional[str] = None
    ):
        """Публикует событие question.selected через Outbox"""
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                await self.outbox_publisher.publish(
                    conn,
                    "question.selected",
                    {
                        "user_id": user_id,
                        "session_id": session_id,
                        "question_id": question["id"],
                        "question_text": question["question_text"],
                        "depth_level": question["depth_level"],
                        "energy_level": question["energy_level"]
                    },
                    trace_id=trace_id
                )

    async def _publish_session_completed(
        self,
        user_id: int,
        session_id: int,
        trace_id: Optional[str] = None
    ):
        """Публикует событие session.completed"""
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                await self.outbox_publisher.publish(
                    conn,
                    "session.completed",
                    {
                        "user_id": user_id,
                        "session_id": session_id,
                        "completed_at": datetime.now().isoformat()
                    },
                    trace_id=trace_id
                )

    async def _load_session_data(self, session_id: int) -> Dict[str, Any]:
        """Загружает session_data из БД"""
        # Упрощенная версия - в продакшене нужна полноценная таблица
        return {
            "questions_answered": 0,
            "energy_balance": 0,
            "trust_level": TrustLevel.STRANGER.value,
            "answered_question_ids": []
        }

    async def _save_session_data(self, session_id: int, session_data: Dict[str, Any]):
        """Сохраняет session_data в БД"""
        # Упрощенная версия - в продакшене сохранять в БД
        pass
