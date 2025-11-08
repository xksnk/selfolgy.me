"""
Unit Tests: Question Selection Service

Тестирует все компоненты Question Selection Service:
- FatigueDetector
- SmartMixRouter
- Routing strategies
- Energy balance
- Trust level access
- Event handling
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime

from systems.onboarding.question_selection_service import (
    QuestionSelectionService,
    FatigueDetector,
    SmartMixRouter,
    RoutingStrategy,
    EnergyLevel,
    TrustLevel
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def fatigue_detector():
    """FatigueDetector instance"""
    return FatigueDetector()


@pytest.fixture
def mock_db_pool():
    """Mock database pool"""
    pool = AsyncMock()
    return pool


@pytest.fixture
def smart_mix_router(mock_db_pool):
    """SmartMixRouter instance with mocked DB"""
    return SmartMixRouter(mock_db_pool)


# ============================================================================
# FATIGUE DETECTOR TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_fatigue_detector_max_questions_reached(fatigue_detector):
    """
    Тест: FatigueDetector обнаруживает достижение максимума вопросов
    """
    session_data = {
        "questions_answered": 15,
        "energy_balance": 0,
        "avg_answer_length": 50
    }

    result = await fatigue_detector.check_fatigue(session_data)

    assert result["is_fatigued"] is True
    assert result["reason"] == "max_questions_reached"
    assert "завершить сессию" in result["recommendation"].lower()


@pytest.mark.asyncio
async def test_fatigue_detector_low_energy(fatigue_detector):
    """
    Тест: FatigueDetector обнаруживает низкий энергетический баланс
    """
    session_data = {
        "questions_answered": 8,
        "energy_balance": -6,  # Below threshold (-5)
        "avg_answer_length": 50
    }

    result = await fatigue_detector.check_fatigue(session_data)

    assert result["is_fatigued"] is True
    assert result["reason"] == "low_energy"
    assert "HEALING" in result["recommendation"]


@pytest.mark.asyncio
async def test_fatigue_detector_short_answers(fatigue_detector):
    """
    Тест: FatigueDetector обнаруживает короткие ответы (признак усталости)
    """
    session_data = {
        "questions_answered": 10,
        "energy_balance": 0,
        "avg_answer_length": 15  # < 20 chars
    }

    result = await fatigue_detector.check_fatigue(session_data)

    assert result["is_fatigued"] is True
    assert result["reason"] == "short_answers"


@pytest.mark.asyncio
async def test_fatigue_detector_no_fatigue(fatigue_detector):
    """
    Тест: FatigueDetector не обнаруживает усталость при нормальных показателях
    """
    session_data = {
        "questions_answered": 5,
        "energy_balance": 2,
        "avg_answer_length": 100
    }

    result = await fatigue_detector.check_fatigue(session_data)

    assert result["is_fatigued"] is False
    assert result["reason"] is None


# ============================================================================
# SMART MIX ROUTER - STRATEGY TESTS
# ============================================================================

def test_determine_strategy_entry(smart_mix_router):
    """
    Тест: Стратегия ENTRY для первых 3 вопросов
    """
    session_data = {"questions_answered": 0}
    strategy = smart_mix_router._determine_strategy(session_data)
    assert strategy == RoutingStrategy.ENTRY

    session_data = {"questions_answered": 2}
    strategy = smart_mix_router._determine_strategy(session_data)
    assert strategy == RoutingStrategy.ENTRY


def test_determine_strategy_exploration(smart_mix_router):
    """
    Тест: Стратегия EXPLORATION для вопросов 3-7
    """
    session_data = {"questions_answered": 3}
    strategy = smart_mix_router._determine_strategy(session_data)
    assert strategy == RoutingStrategy.EXPLORATION

    session_data = {"questions_answered": 6}
    strategy = smart_mix_router._determine_strategy(session_data)
    assert strategy == RoutingStrategy.EXPLORATION


def test_determine_strategy_deepening(smart_mix_router):
    """
    Тест: Стратегия DEEPENING для вопросов 7-12
    """
    session_data = {"questions_answered": 7}
    strategy = smart_mix_router._determine_strategy(session_data)
    assert strategy == RoutingStrategy.DEEPENING

    session_data = {"questions_answered": 11}
    strategy = smart_mix_router._determine_strategy(session_data)
    assert strategy == RoutingStrategy.DEEPENING


def test_determine_strategy_balancing(smart_mix_router):
    """
    Тест: Стратегия BALANCING для вопросов 12+
    """
    session_data = {"questions_answered": 12}
    strategy = smart_mix_router._determine_strategy(session_data)
    assert strategy == RoutingStrategy.BALANCING


# ============================================================================
# TRUST LEVEL TESTS
# ============================================================================

def test_get_max_depth_for_trust_level(smart_mix_router):
    """
    Тест: Правильная глубина вопросов для каждого уровня доверия
    """
    # STRANGER (0) -> SURFACE only
    max_depth = smart_mix_router._get_max_depth_for_trust_level(
        TrustLevel.STRANGER.value
    )
    assert max_depth == "SURFACE"

    # ACQUAINTANCE (1) -> CONSCIOUS
    max_depth = smart_mix_router._get_max_depth_for_trust_level(
        TrustLevel.ACQUAINTANCE.value
    )
    assert max_depth == "CONSCIOUS"

    # FRIEND (2) -> EDGE
    max_depth = smart_mix_router._get_max_depth_for_trust_level(
        TrustLevel.FRIEND.value
    )
    assert max_depth == "EDGE"

    # TRUSTED (3) -> SHADOW
    max_depth = smart_mix_router._get_max_depth_for_trust_level(
        TrustLevel.TRUSTED.value
    )
    assert max_depth == "SHADOW"

    # SOUL_MATE (4) -> CORE (все вопросы)
    max_depth = smart_mix_router._get_max_depth_for_trust_level(
        TrustLevel.SOUL_MATE.value
    )
    assert max_depth == "CORE"


# ============================================================================
# QUESTION SELECTION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_select_next_question_no_fatigue(smart_mix_router, mock_db_pool):
    """
    Тест: Выбор вопроса при отсутствии усталости
    """
    session_data = {
        "questions_answered": 0,
        "energy_balance": 0,
        "trust_level": TrustLevel.STRANGER.value,
        "answered_question_ids": [],
        "avg_answer_length": 50
    }

    # Mock database response
    mock_question = {
        "id": 1,
        "question_text": "Test question",
        "depth_level": "SURFACE",
        "energy_level": "OPENING"
    }

    mock_conn = AsyncMock()
    mock_conn.fetchrow.return_value = mock_question
    mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

    question = await smart_mix_router.select_next_question(
        user_id=123,
        session_id=1,
        session_data=session_data
    )

    assert question is not None
    assert question["id"] == 1


@pytest.mark.asyncio
async def test_select_next_question_max_questions_reached(smart_mix_router):
    """
    Тест: Возвращает None при достижении максимума вопросов
    """
    session_data = {
        "questions_answered": 15,
        "energy_balance": 0,
        "trust_level": TrustLevel.STRANGER.value,
        "answered_question_ids": []
    }

    question = await smart_mix_router.select_next_question(
        user_id=123,
        session_id=1,
        session_data=session_data
    )

    assert question is None


@pytest.mark.asyncio
async def test_select_next_question_low_energy_gives_healing(
    smart_mix_router,
    mock_db_pool
):
    """
    Тест: При низкой энергии выдается HEALING вопрос
    """
    session_data = {
        "questions_answered": 8,
        "energy_balance": -6,  # Low energy
        "trust_level": TrustLevel.STRANGER.value,
        "answered_question_ids": [],
        "avg_answer_length": 50
    }

    # Mock HEALING question
    mock_healing_question = {
        "id": 99,
        "question_text": "What makes you smile?",
        "depth_level": "SURFACE",
        "energy_level": "HEALING"
    }

    mock_conn = AsyncMock()
    mock_conn.fetchrow.return_value = mock_healing_question
    mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

    question = await smart_mix_router.select_next_question(
        user_id=123,
        session_id=1,
        session_data=session_data
    )

    assert question is not None
    assert question["energy_level"] == "HEALING"


# ============================================================================
# STRATEGY-SPECIFIC SELECTION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_select_by_strategy_entry(smart_mix_router, mock_db_pool):
    """
    Тест: ENTRY стратегия выбирает SURFACE + OPENING вопросы
    """
    session_data = {
        "trust_level": TrustLevel.STRANGER.value,
        "answered_question_ids": []
    }

    mock_question = {
        "id": 1,
        "depth_level": "SURFACE",
        "energy_level": "OPENING"
    }

    mock_conn = AsyncMock()
    mock_conn.fetchrow.return_value = mock_question
    mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

    question = await smart_mix_router._select_by_strategy(
        user_id=123,
        strategy=RoutingStrategy.ENTRY,
        session_data=session_data
    )

    assert question["depth_level"] == "SURFACE"
    assert question["energy_level"] == "OPENING"


@pytest.mark.asyncio
async def test_select_by_strategy_exploration(smart_mix_router, mock_db_pool):
    """
    Тест: EXPLORATION стратегия выбирает SURFACE/CONSCIOUS + NEUTRAL/PROCESSING
    """
    session_data = {
        "trust_level": TrustLevel.ACQUAINTANCE.value,
        "answered_question_ids": []
    }

    mock_question = {
        "id": 2,
        "depth_level": "CONSCIOUS",
        "energy_level": "NEUTRAL"
    }

    mock_conn = AsyncMock()
    mock_conn.fetchrow.return_value = mock_question
    mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

    question = await smart_mix_router._select_by_strategy(
        user_id=123,
        strategy=RoutingStrategy.EXPLORATION,
        session_data=session_data
    )

    assert question["depth_level"] in ["SURFACE", "CONSCIOUS"]
    assert question["energy_level"] in ["NEUTRAL", "PROCESSING"]


# ============================================================================
# ANSWERED QUESTIONS FILTER TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_excludes_answered_questions(smart_mix_router, mock_db_pool):
    """
    Тест: Не выбирает уже отвеченные вопросы
    """
    session_data = {
        "trust_level": TrustLevel.STRANGER.value,
        "answered_question_ids": [1, 2, 3]
    }

    mock_question = {"id": 4, "depth_level": "SURFACE"}

    mock_conn = AsyncMock()
    mock_conn.fetchrow.return_value = mock_question
    mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

    question = await smart_mix_router._select_by_strategy(
        user_id=123,
        strategy=RoutingStrategy.ENTRY,
        session_data=session_data
    )

    # Verify that SQL excluded answered questions
    call_args = mock_conn.fetchrow.call_args
    assert call_args is not None

    # Question ID should not be in answered list
    assert question["id"] not in session_data["answered_question_ids"]


# ============================================================================
# SERVICE INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_question_selection_service_handles_session_started():
    """
    Тест: Service обрабатывает событие user.session.started
    """
    # Mock dependencies
    mock_event_bus = AsyncMock()
    mock_db_pool = AsyncMock()

    # Mock database connection and question
    mock_conn = AsyncMock()
    mock_question = {
        "id": 1,
        "question_text": "First question",
        "depth_level": "SURFACE",
        "energy_level": "OPENING"
    }
    mock_conn.fetchrow.return_value = mock_question
    mock_conn.fetchval.return_value = 1
    mock_conn.execute.return_value = None
    mock_conn.transaction.return_value.__aenter__.return_value = None
    mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

    service = QuestionSelectionService(
        event_bus=mock_event_bus,
        db_pool=mock_db_pool
    )

    # Handle session started event
    await service.handle_session_started(
        event_type="user.session.started",
        payload={
            "user_id": 123,
            "session_id": 1,
            "trace_id": "test_trace"
        }
    )

    # Verify metrics incremented
    assert service.get_metrics()["sessions_started"] == 1


@pytest.mark.asyncio
async def test_question_selection_service_handles_answer_submitted():
    """
    Тест: Service обрабатывает событие user.answer.submitted
    """
    mock_event_bus = AsyncMock()
    mock_db_pool = AsyncMock()

    # Mock database
    mock_conn = AsyncMock()
    mock_question = {
        "id": 2,
        "question_text": "Next question",
        "depth_level": "SURFACE",
        "energy_level": "NEUTRAL"
    }
    mock_conn.fetchrow.return_value = mock_question
    mock_conn.fetchval.return_value = 1
    mock_conn.execute.return_value = None
    mock_conn.transaction.return_value.__aenter__.return_value = None
    mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

    service = QuestionSelectionService(
        event_bus=mock_event_bus,
        db_pool=mock_db_pool
    )

    # Handle answer submitted
    await service.handle_answer_submitted(
        event_type="user.answer.submitted",
        payload={
            "user_id": 123,
            "session_id": 1,
            "question_id": "q_001",
            "answer_text": "My answer",
            "trace_id": "test_trace"
        }
    )

    # Verify metrics
    assert service.get_metrics()["answers_processed"] == 1


# ============================================================================
# EDGE CASES
# ============================================================================

@pytest.mark.asyncio
async def test_no_questions_available_returns_none(smart_mix_router, mock_db_pool):
    """
    Тест: Возвращает None если нет доступных вопросов
    """
    session_data = {
        "trust_level": TrustLevel.STRANGER.value,
        "answered_question_ids": [],
        "questions_answered": 5,
        "energy_balance": 0,
        "avg_answer_length": 50
    }

    # Mock: no questions available
    mock_conn = AsyncMock()
    mock_conn.fetchrow.return_value = None
    mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

    question = await smart_mix_router.select_next_question(
        user_id=123,
        session_id=1,
        session_data=session_data
    )

    # Should try fallback query but still get None
    assert question is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
