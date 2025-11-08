"""
Unit Tests: Trait Evolution Service

Тестирует компоненты Trait Evolution Service:
- TraitHistoryManager (запись и получение истории)
- EvolutionAnalyzer (обнаружение паттернов)
- Pattern detection (increasing/decreasing/stable/oscillating)
- Significant change detection
- Event handlers (trait.extracted → record history)
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock
from datetime import datetime, timedelta

from systems.profile.trait_evolution_service import (
    TraitEvolutionService,
    TraitHistoryManager,
    EvolutionAnalyzer,
    TraitChange,
    EvolutionPattern
)
from core.event_bus import EventBus


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
async def db_pool():
    """Mock PostgreSQL connection pool"""
    pool = AsyncMock()

    conn = AsyncMock()
    conn.fetchval = AsyncMock()
    conn.fetchrow = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.execute = AsyncMock()
    conn.transaction = AsyncMock()

    pool.acquire = AsyncMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.acquire.return_value.__aexit__ = AsyncMock()

    return pool


@pytest.fixture
def event_bus():
    """Mock Event Bus"""
    bus = AsyncMock(spec=EventBus)
    bus.subscribe = AsyncMock()
    bus.publish = AsyncMock()
    return bus


@pytest.fixture
def history_manager(db_pool):
    """TraitHistoryManager instance"""
    return TraitHistoryManager(db_pool=db_pool)


@pytest.fixture
def evolution_analyzer(history_manager):
    """EvolutionAnalyzer instance"""
    return EvolutionAnalyzer(history_manager=history_manager)


@pytest.fixture
async def evolution_service(event_bus, db_pool):
    """TraitEvolutionService instance"""
    service = TraitEvolutionService(
        event_bus=event_bus,
        db_pool=db_pool
    )
    return service


# ============================================================================
# TRAIT HISTORY MANAGER TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_record_change_success(history_manager, db_pool):
    """
    Тест: Успешная запись изменения черты
    """
    user_id = 12345

    conn = await db_pool.acquire().__aenter__()
    conn.fetchval.return_value = 1

    history_id = await history_manager.record_change(
        user_id=user_id,
        trait_category="big_five",
        trait_name="openness",
        old_value=0.5,
        new_value=0.7,
        confidence=0.8,
        trigger="analysis"
    )

    assert history_id == 1
    assert conn.fetchval.called


@pytest.mark.asyncio
async def test_record_change_first_time(history_manager, db_pool):
    """
    Тест: Запись первого значения черты (old_value=None)
    """
    user_id = 12345

    conn = await db_pool.acquire().__aenter__()
    conn.fetchval.return_value = 1

    history_id = await history_manager.record_change(
        user_id=user_id,
        trait_category="big_five",
        trait_name="openness",
        old_value=None,  # First time
        new_value=0.7,
        confidence=0.8
    )

    assert history_id == 1

    # Verify old_value was passed as None
    call_args = conn.fetchval.call_args[0]
    assert call_args[4] is None  # old_value parameter


@pytest.mark.asyncio
async def test_get_trait_history_all(history_manager, db_pool):
    """
    Тест: Получение всей истории пользователя
    """
    user_id = 12345

    # Mock history rows
    conn = await db_pool.acquire().__aenter__()
    conn.fetch.return_value = [
        {
            "trait_category": "big_five",
            "trait_name": "openness",
            "old_value": 0.5,
            "new_value": 0.7,
            "confidence": 0.8,
            "trigger": "analysis",
            "timestamp": datetime.now()
        },
        {
            "trait_category": "big_five",
            "trait_name": "conscientiousness",
            "old_value": 0.6,
            "new_value": 0.65,
            "confidence": 0.75,
            "trigger": "analysis",
            "timestamp": datetime.now()
        }
    ]

    history = await history_manager.get_trait_history(
        user_id=user_id,
        limit=100
    )

    assert len(history) == 2
    assert isinstance(history[0], TraitChange)
    assert history[0].trait_name == "openness"
    assert history[0].new_value == 0.7


@pytest.mark.asyncio
async def test_get_trait_history_filtered(history_manager, db_pool):
    """
    Тест: Получение истории с фильтром по категории и имени
    """
    user_id = 12345

    conn = await db_pool.acquire().__aenter__()
    conn.fetch.return_value = [
        {
            "trait_category": "big_five",
            "trait_name": "openness",
            "old_value": 0.5,
            "new_value": 0.7,
            "confidence": 0.8,
            "trigger": "analysis",
            "timestamp": datetime.now()
        }
    ]

    history = await history_manager.get_trait_history(
        user_id=user_id,
        trait_category="big_five",
        trait_name="openness",
        limit=10
    )

    assert len(history) == 1
    assert history[0].trait_category == "big_five"
    assert history[0].trait_name == "openness"


@pytest.mark.asyncio
async def test_get_latest_values(history_manager, db_pool):
    """
    Тест: Получение последних значений всех черт в категории
    """
    user_id = 12345

    conn = await db_pool.acquire().__aenter__()
    conn.fetch.return_value = [
        {"trait_name": "openness", "new_value": 0.7},
        {"trait_name": "conscientiousness", "new_value": 0.65},
        {"trait_name": "extraversion", "new_value": 0.55}
    ]

    latest = await history_manager.get_latest_values(
        user_id=user_id,
        trait_category="big_five"
    )

    assert len(latest) == 3
    assert latest["openness"] == 0.7
    assert latest["conscientiousness"] == 0.65
    assert latest["extraversion"] == 0.55


# ============================================================================
# EVOLUTION ANALYZER TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_analyze_evolution_increasing_pattern(evolution_analyzer, db_pool):
    """
    Тест: Обнаружение increasing паттерна
    """
    user_id = 12345

    # Create history showing increasing trend
    now = datetime.now()
    history = [
        TraitChange("big_five", "openness", 0.4, 0.5, 0.8, "analysis", now - timedelta(days=20)),
        TraitChange("big_five", "openness", 0.5, 0.6, 0.8, "analysis", now - timedelta(days=15)),
        TraitChange("big_five", "openness", 0.6, 0.7, 0.8, "analysis", now - timedelta(days=10)),
        TraitChange("big_five", "openness", 0.7, 0.8, 0.8, "analysis", now - timedelta(days=5))
    ]

    # Mock get_trait_history
    evolution_analyzer.history_manager.get_trait_history = AsyncMock(return_value=history)

    pattern = await evolution_analyzer.analyze_evolution(
        user_id=user_id,
        trait_category="big_five",
        trait_name="openness",
        lookback_days=30
    )

    assert pattern is not None
    assert pattern.pattern_type == "increasing"
    assert pattern.strength > 0
    assert pattern.trait_name == "openness"


@pytest.mark.asyncio
async def test_analyze_evolution_decreasing_pattern(evolution_analyzer, db_pool):
    """
    Тест: Обнаружение decreasing паттерна
    """
    user_id = 12345

    now = datetime.now()
    history = [
        TraitChange("big_five", "neuroticism", 0.8, 0.7, 0.8, "analysis", now - timedelta(days=20)),
        TraitChange("big_five", "neuroticism", 0.7, 0.6, 0.8, "analysis", now - timedelta(days=15)),
        TraitChange("big_five", "neuroticism", 0.6, 0.5, 0.8, "analysis", now - timedelta(days=10)),
        TraitChange("big_five", "neuroticism", 0.5, 0.4, 0.8, "analysis", now - timedelta(days=5))
    ]

    evolution_analyzer.history_manager.get_trait_history = AsyncMock(return_value=history)

    pattern = await evolution_analyzer.analyze_evolution(
        user_id=user_id,
        trait_category="big_five",
        trait_name="neuroticism",
        lookback_days=30
    )

    assert pattern is not None
    assert pattern.pattern_type == "decreasing"
    assert pattern.strength > 0


@pytest.mark.asyncio
async def test_analyze_evolution_stable_pattern(evolution_analyzer, db_pool):
    """
    Тест: Обнаружение stable паттерна
    """
    user_id = 12345

    now = datetime.now()
    history = [
        TraitChange("big_five", "conscientiousness", 0.6, 0.61, 0.8, "analysis", now - timedelta(days=20)),
        TraitChange("big_five", "conscientiousness", 0.61, 0.60, 0.8, "analysis", now - timedelta(days=15)),
        TraitChange("big_five", "conscientiousness", 0.60, 0.62, 0.8, "analysis", now - timedelta(days=10)),
        TraitChange("big_five", "conscientiousness", 0.62, 0.61, 0.8, "analysis", now - timedelta(days=5))
    ]

    evolution_analyzer.history_manager.get_trait_history = AsyncMock(return_value=history)

    pattern = await evolution_analyzer.analyze_evolution(
        user_id=user_id,
        trait_category="big_five",
        trait_name="conscientiousness",
        lookback_days=30
    )

    assert pattern is not None
    assert pattern.pattern_type == "stable"


@pytest.mark.asyncio
async def test_analyze_evolution_insufficient_data(evolution_analyzer):
    """
    Тест: Возвращает None при недостаточных данных
    """
    user_id = 12345

    # Only 1 change - insufficient
    evolution_analyzer.history_manager.get_trait_history = AsyncMock(return_value=[
        TraitChange("big_five", "openness", None, 0.7, 0.8, "analysis", datetime.now())
    ])

    pattern = await evolution_analyzer.analyze_evolution(
        user_id=user_id,
        trait_category="big_five",
        trait_name="openness",
        lookback_days=30
    )

    assert pattern is None


@pytest.mark.asyncio
async def test_detect_significant_changes(evolution_analyzer, db_pool):
    """
    Тест: Обнаружение значительных изменений
    """
    user_id = 12345

    # Mock recent changes
    conn = await evolution_analyzer.history_manager.db_pool.acquire().__aenter__()
    conn.fetch.return_value = [
        {
            "trait_category": "big_five",
            "trait_name": "openness",
            "old_value": 0.5,
            "new_value": 0.8,  # +0.3 - significant!
            "confidence": 0.9,
            "timestamp": datetime.now()
        },
        {
            "trait_category": "big_five",
            "trait_name": "conscientiousness",
            "old_value": 0.6,
            "new_value": 0.62,  # +0.02 - not significant
            "confidence": 0.7,
            "timestamp": datetime.now()
        }
    ]

    significant = await evolution_analyzer.detect_significant_changes(
        user_id=user_id,
        threshold=0.2
    )

    # Only openness should be significant
    assert len(significant) == 1
    assert significant[0]["trait_name"] == "openness"
    assert significant[0]["change"] >= 0.2


# ============================================================================
# PATTERN DETECTION TESTS
# ============================================================================

def test_detect_pattern_increasing(evolution_analyzer):
    """
    Тест: _detect_pattern правильно определяет increasing
    """
    history = [
        TraitChange("big_five", "openness", i * 0.1, (i + 1) * 0.1, 0.8, "analysis", datetime.now())
        for i in range(5)
    ]

    pattern_type, strength = evolution_analyzer._detect_pattern(history)

    assert pattern_type == "increasing"
    assert strength > 0


def test_detect_pattern_decreasing(evolution_analyzer):
    """
    Тест: _detect_pattern правильно определяет decreasing
    """
    history = [
        TraitChange("big_five", "neuroticism", 0.9 - i * 0.1, 0.8 - i * 0.1, 0.8, "analysis", datetime.now())
        for i in range(5)
    ]

    pattern_type, strength = evolution_analyzer._detect_pattern(history)

    assert pattern_type == "decreasing"
    assert strength > 0


def test_detect_pattern_stable(evolution_analyzer):
    """
    Тест: _detect_pattern правильно определяет stable
    """
    history = [
        TraitChange("big_five", "agreeableness", 0.6, 0.6 + i * 0.01, 0.8, "analysis", datetime.now())
        for i in range(5)
    ]

    pattern_type, strength = evolution_analyzer._detect_pattern(history)

    assert pattern_type == "stable"


# ============================================================================
# SERVICE EVENT HANDLER TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_handle_trait_extracted_records_changes(evolution_service, db_pool):
    """
    Тест: trait.extracted записывает изменения в историю
    """
    event = {
        "event_type": "trait.extracted",
        "payload": {
            "user_id": 12345,
            "traits": {
                "big_five": {
                    "openness": 0.8,
                    "conscientiousness": 0.7
                }
            },
            "confidence": 0.85
        },
        "trace_id": "test_trace_123"
    }

    # Mock get_latest_values (no previous values)
    conn = await db_pool.acquire().__aenter__()
    conn.fetch.return_value = []  # No previous values

    # Mock record_change
    conn.fetchval.return_value = 1

    # Mock transaction for outbox
    mock_transaction = AsyncMock()
    mock_transaction.__aenter__ = AsyncMock()
    mock_transaction.__aexit__ = AsyncMock()
    conn.transaction.return_value = mock_transaction

    await evolution_service._handle_trait_extracted(event)

    # Should record 2 changes (openness + conscientiousness)
    assert evolution_service.metrics["changes_recorded"] == 2


@pytest.mark.asyncio
async def test_handle_trait_extracted_detects_significant_changes(evolution_service, db_pool):
    """
    Тест: Обнаружение значительных изменений публикует событие
    """
    event = {
        "payload": {
            "user_id": 12345,
            "traits": {
                "big_five": {
                    "openness": 0.9  # Big jump from 0.5
                }
            },
            "confidence": 0.9
        },
        "trace_id": "test_trace_123"
    }

    # Mock previous value
    conn = await db_pool.acquire().__aenter__()
    conn.fetch.return_value = [
        {"trait_name": "openness", "new_value": 0.5}
    ]

    conn.fetchval.return_value = 1

    # Mock transaction
    mock_transaction = AsyncMock()
    mock_transaction.__aenter__ = AsyncMock()
    mock_transaction.__aexit__ = AsyncMock()
    conn.transaction.return_value = mock_transaction

    await evolution_service._handle_trait_extracted(event)

    # Should detect significant change (0.5 → 0.9 = +0.4)
    assert evolution_service.metrics["significant_changes"] >= 1


@pytest.mark.asyncio
async def test_handle_trait_extracted_skips_small_changes(evolution_service, db_pool):
    """
    Тест: Маленькие изменения не записываются
    """
    event = {
        "payload": {
            "user_id": 12345,
            "traits": {
                "big_five": {
                    "openness": 0.501  # Tiny change from 0.5
                }
            },
            "confidence": 0.8
        }
    }

    # Mock previous value very close
    conn = await db_pool.acquire().__aenter__()
    conn.fetch.return_value = [
        {"trait_name": "openness", "new_value": 0.5}
    ]

    await evolution_service._handle_trait_extracted(event)

    # Should not record (change < 0.01)
    assert evolution_service.metrics["changes_recorded"] == 0


# ============================================================================
# HEALTH CHECK TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_health_check_healthy(evolution_service, db_pool):
    """
    Тест: Health check возвращает healthy
    """
    conn = await db_pool.acquire().__aenter__()
    conn.fetchval.return_value = 1

    health = await evolution_service.health_check()

    assert health["status"] == "healthy"
    assert health["database"] == "healthy"


@pytest.mark.asyncio
async def test_health_check_unhealthy(evolution_service, db_pool):
    """
    Тест: Health check возвращает unhealthy при сбое DB
    """
    conn = await db_pool.acquire().__aenter__()
    conn.fetchval.side_effect = Exception("DB connection failed")

    health = await evolution_service.health_check()

    assert health["status"] == "unhealthy"
    assert health["database"] == "unhealthy"


# ============================================================================
# METRICS TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_metrics_tracking(evolution_service, db_pool):
    """
    Тест: Метрики правильно отслеживаются
    """
    # Simulate multiple events
    for i in range(3):
        event = {
            "payload": {
                "user_id": 12345 + i,
                "traits": {
                    "big_five": {
                        "openness": 0.7
                    }
                },
                "confidence": 0.8
            }
        }

        # Mock no previous values
        conn = await db_pool.acquire().__aenter__()
        conn.fetch.return_value = []
        conn.fetchval.return_value = i + 1

        # Mock transaction
        mock_transaction = AsyncMock()
        mock_transaction.__aenter__ = AsyncMock()
        mock_transaction.__aexit__ = AsyncMock()
        conn.transaction.return_value = mock_transaction

        await evolution_service._handle_trait_extracted(event)

    metrics = evolution_service.get_metrics()

    assert metrics["changes_recorded"] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
