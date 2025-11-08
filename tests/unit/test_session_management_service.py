"""
Unit Tests: Session Management Service

Тестирует все компоненты Session Management Service:
- SessionManager CRUD operations
- Redis caching
- Timeout detection
- Session analytics
- Event handling
- Background tasks
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timedelta

from systems.onboarding.session_management_service import (
    SessionManagementService,
    SessionManager,
    SessionStatus
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_db_pool():
    """Mock database pool"""
    return AsyncMock()


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    redis_mock = AsyncMock()
    redis_mock.setex = AsyncMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.delete = AsyncMock()
    redis_mock.ping = AsyncMock()
    return redis_mock


@pytest.fixture
def session_manager(mock_db_pool, mock_redis):
    """SessionManager instance with mocked dependencies"""
    return SessionManager(mock_db_pool, mock_redis)


# ============================================================================
# SESSION CRUD TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_create_session(session_manager, mock_db_pool, mock_redis):
    """
    Тест: Создание новой сессии
    """
    # Mock database response
    mock_conn = AsyncMock()
    mock_conn.fetchval.return_value = 1  # session_id
    mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

    session_id = await session_manager.create_session(
        user_id=123,
        session_type="onboarding"
    )

    assert session_id == 1

    # Verify database insert called
    assert mock_conn.fetchval.called

    # Verify Redis cache called
    assert mock_redis.setex.called


@pytest.mark.asyncio
async def test_get_session_from_cache(session_manager, mock_redis):
    """
    Тест: Получение сессии из cache (без обращения к БД)
    """
    # Mock cached session
    cached_data = {
        "id": 1,
        "user_id": 123,
        "status": SessionStatus.ACTIVE.value
    }
    mock_redis.get.return_value = json.dumps(cached_data)

    session = await session_manager.get_session(session_id=1)

    assert session is not None
    assert session["id"] == 1
    assert session["user_id"] == 123

    # Verify cache was checked
    assert mock_redis.get.called


@pytest.mark.asyncio
async def test_get_session_from_database_on_cache_miss(
    session_manager,
    mock_db_pool,
    mock_redis
):
    """
    Тест: Получение сессии из БД при отсутствии в cache
    """
    # Cache miss
    mock_redis.get.return_value = None

    # Mock database response
    mock_conn = AsyncMock()
    mock_conn.fetchrow.return_value = {
        "id": 1,
        "user_id": 123,
        "session_type": "onboarding",
        "status": SessionStatus.ACTIVE.value,
        "started_at": datetime.now(),
        "completed_at": None,
        "last_activity_at": datetime.now()
    }
    mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

    session = await session_manager.get_session(session_id=1)

    assert session is not None
    assert session["id"] == 1

    # Verify database was queried
    assert mock_conn.fetchrow.called

    # Verify result was cached
    assert mock_redis.setex.called


@pytest.mark.asyncio
async def test_get_session_returns_none_when_not_found(
    session_manager,
    mock_db_pool,
    mock_redis
):
    """
    Тест: Возвращает None если сессия не найдена
    """
    # Cache miss
    mock_redis.get.return_value = None

    # Database miss
    mock_conn = AsyncMock()
    mock_conn.fetchrow.return_value = None
    mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

    session = await session_manager.get_session(session_id=999)

    assert session is None


# ============================================================================
# SESSION UPDATE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_update_session_activity(session_manager, mock_db_pool, mock_redis):
    """
    Тест: Обновление last_activity_at сессии
    """
    # Mock existing session in cache
    cached_data = {
        "id": 1,
        "user_id": 123,
        "status": SessionStatus.ACTIVE.value,
        "last_activity_at": datetime.now().isoformat()
    }
    mock_redis.get.return_value = json.dumps(cached_data)

    # Mock database
    mock_conn = AsyncMock()
    mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

    await session_manager.update_session_activity(
        session_id=1,
        activity_data={"question_id": "q_001"}
    )

    # Verify database update
    assert mock_conn.execute.called

    # Verify cache updated
    assert mock_redis.setex.called


@pytest.mark.asyncio
async def test_complete_session(session_manager, mock_db_pool, mock_redis):
    """
    Тест: Завершение сессии
    """
    # Mock existing session
    cached_data = {
        "id": 1,
        "user_id": 123,
        "status": SessionStatus.ACTIVE.value
    }
    mock_redis.get.return_value = json.dumps(cached_data)

    # Mock database
    mock_conn = AsyncMock()
    mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

    await session_manager.complete_session(session_id=1)

    # Verify status updated to COMPLETED
    assert mock_conn.execute.called

    # Verify cache updated with completed status
    assert mock_redis.setex.called


# ============================================================================
# TIMEOUT DETECTION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_check_timeouts_detects_inactive_sessions(
    session_manager,
    mock_db_pool
):
    """
    Тест: Обнаружение inactive сессий по timeout
    """
    # Mock database with timed out sessions
    mock_conn = AsyncMock()

    # Timed out sessions
    mock_conn.fetch.return_value = [
        {"id": 1},
        {"id": 2}
    ]

    mock_conn.execute.return_value = None
    mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

    timed_out_ids = await session_manager.check_timeouts()

    assert len(timed_out_ids) == 2
    assert 1 in timed_out_ids
    assert 2 in timed_out_ids

    # Verify status updated to TIMED_OUT
    assert mock_conn.execute.call_count >= 2


@pytest.mark.asyncio
async def test_check_timeouts_clears_cache(session_manager, mock_db_pool, mock_redis):
    """
    Тест: Cache очищается для timed out сессий
    """
    # Mock timed out session
    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = [{"id": 1}]
    mock_conn.execute.return_value = None
    mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

    await session_manager.check_timeouts()

    # Verify cache cleared
    assert mock_redis.delete.called


# ============================================================================
# SESSION ANALYTICS TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_get_session_analytics(session_manager, mock_db_pool):
    """
    Тест: Получение аналитики сессии
    """
    # Mock session data
    now = datetime.now()
    started_at = now - timedelta(minutes=10)

    mock_conn = AsyncMock()
    mock_conn.fetchrow.return_value = {
        "id": 1,
        "user_id": 123,
        "status": SessionStatus.COMPLETED.value,
        "started_at": started_at,
        "completed_at": now,
        "last_activity_at": now
    }

    # Mock answers count
    mock_conn.fetchval.return_value = 10  # 10 questions answered

    mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

    analytics = await session_manager.get_session_analytics(session_id=1)

    assert analytics["total_questions"] == 10
    assert analytics["duration_seconds"] == pytest.approx(600, rel=5)  # ~10 minutes
    assert analytics["completion_rate"] == pytest.approx(10/15, rel=0.01)  # 10/15 = 0.67
    assert analytics["status"] == SessionStatus.COMPLETED.value


@pytest.mark.asyncio
async def test_get_session_analytics_completion_rate_capped_at_100_percent(
    session_manager,
    mock_db_pool
):
    """
    Тест: Completion rate не превышает 100%
    """
    mock_conn = AsyncMock()
    mock_conn.fetchrow.return_value = {
        "id": 1,
        "status": SessionStatus.COMPLETED.value,
        "started_at": datetime.now(),
        "completed_at": datetime.now(),
        "last_activity_at": datetime.now()
    }

    # More than 15 questions (over 100%)
    mock_conn.fetchval.return_value = 20

    mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

    analytics = await session_manager.get_session_analytics(session_id=1)

    # Should be capped at 1.0 (100%)
    assert analytics["completion_rate"] == 1.0


# ============================================================================
# REDIS CACHE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_cache_session(session_manager, mock_redis):
    """
    Тест: Кэширование сессии в Redis
    """
    session_data = {
        "id": 1,
        "user_id": 123,
        "status": SessionStatus.ACTIVE.value
    }

    await session_manager._cache_session(1, session_data)

    # Verify setex called with correct TTL (1800 seconds = 30 minutes)
    assert mock_redis.setex.called
    call_args = mock_redis.setex.call_args
    assert call_args[0][0] == "session:1"  # key
    assert call_args[0][1] == 1800  # TTL


@pytest.mark.asyncio
async def test_get_cached_session(session_manager, mock_redis):
    """
    Тест: Получение сессии из cache
    """
    cached_data = {"id": 1, "user_id": 123}
    mock_redis.get.return_value = json.dumps(cached_data)

    session = await session_manager._get_cached_session(session_id=1)

    assert session is not None
    assert session["id"] == 1


@pytest.mark.asyncio
async def test_clear_cache(session_manager, mock_redis):
    """
    Тест: Очистка cache сессии
    """
    await session_manager._clear_cache(session_id=1)

    # Verify delete called
    assert mock_redis.delete.called
    assert mock_redis.delete.call_args[0][0] == "session:1"


# ============================================================================
# SERVICE INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_service_handles_onboarding_initiated():
    """
    Тест: Service обрабатывает user.onboarding.initiated
    """
    mock_event_bus = AsyncMock()
    mock_db_pool = AsyncMock()
    mock_redis = AsyncMock()

    # Mock database
    mock_conn = AsyncMock()
    mock_conn.fetchval.return_value = 1  # session_id
    mock_conn.execute.return_value = None
    mock_conn.transaction.return_value.__aenter__.return_value = None
    mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

    service = SessionManagementService(
        event_bus=mock_event_bus,
        db_pool=mock_db_pool,
        redis_client=mock_redis
    )

    await service.handle_onboarding_initiated(
        event_type="user.onboarding.initiated",
        payload={
            "user_id": 123,
            "trace_id": "test_trace"
        }
    )

    # Verify metrics
    assert service.get_metrics()["sessions_created"] == 1


@pytest.mark.asyncio
async def test_service_handles_answer_submitted():
    """
    Тест: Service обрабатывает user.answer.submitted
    """
    mock_event_bus = AsyncMock()
    mock_db_pool = AsyncMock()
    mock_redis = AsyncMock()

    # Mock database
    mock_conn = AsyncMock()
    mock_conn.execute.return_value = None
    mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

    # Mock cached session
    mock_redis.get.return_value = json.dumps({
        "id": 1,
        "user_id": 123,
        "status": SessionStatus.ACTIVE.value
    })

    service = SessionManagementService(
        event_bus=mock_event_bus,
        db_pool=mock_db_pool,
        redis_client=mock_redis
    )

    await service.handle_answer_submitted(
        event_type="user.answer.submitted",
        payload={
            "user_id": 123,
            "session_id": 1,
            "question_id": "q_001",
            "answer_text": "My answer"
        }
    )

    # Verify metrics
    assert service.get_metrics()["session_activities"] == 1


@pytest.mark.asyncio
async def test_service_handles_session_completed():
    """
    Тест: Service обрабатывает session.completed
    """
    mock_event_bus = AsyncMock()
    mock_db_pool = AsyncMock()
    mock_redis = AsyncMock()

    # Mock database
    mock_conn = AsyncMock()
    mock_conn.execute.return_value = None
    mock_conn.fetchrow.return_value = {
        "id": 1,
        "status": SessionStatus.COMPLETED.value,
        "started_at": datetime.now(),
        "completed_at": datetime.now(),
        "last_activity_at": datetime.now()
    }
    mock_conn.fetchval.return_value = 10
    mock_conn.transaction.return_value.__aenter__.return_value = None
    mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

    # Mock cached session
    mock_redis.get.return_value = json.dumps({
        "id": 1,
        "user_id": 123,
        "status": SessionStatus.ACTIVE.value
    })

    service = SessionManagementService(
        event_bus=mock_event_bus,
        db_pool=mock_db_pool,
        redis_client=mock_redis
    )

    await service.handle_session_completed(
        event_type="session.completed",
        payload={
            "session_id": 1,
            "user_id": 123
        }
    )

    # Verify metrics
    assert service.get_metrics()["sessions_completed"] == 1


# ============================================================================
# HEALTH CHECK TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_health_check_all_healthy():
    """
    Тест: Health check возвращает healthy когда все компоненты работают
    """
    mock_event_bus = AsyncMock()
    mock_event_bus.redis.ping = AsyncMock()

    mock_db_pool = AsyncMock()
    mock_conn = AsyncMock()
    mock_conn.fetchval.return_value = 1
    mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock()

    service = SessionManagementService(
        event_bus=mock_event_bus,
        db_pool=mock_db_pool,
        redis_client=mock_redis
    )

    health = await service.health_check()

    assert health["status"] == "healthy"
    assert health["checks"]["database"] == "healthy"
    assert health["checks"]["redis"] == "healthy"
    assert health["checks"]["event_bus"] == "healthy"


@pytest.mark.asyncio
async def test_health_check_unhealthy_when_component_fails():
    """
    Тест: Health check возвращает unhealthy когда компонент падает
    """
    mock_event_bus = AsyncMock()
    mock_event_bus.redis.ping = AsyncMock()

    mock_db_pool = AsyncMock()
    mock_conn = AsyncMock()
    mock_conn.fetchval.side_effect = Exception("Database error")
    mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock()

    service = SessionManagementService(
        event_bus=mock_event_bus,
        db_pool=mock_db_pool,
        redis_client=mock_redis
    )

    health = await service.health_check()

    assert health["status"] == "unhealthy"
    assert health["checks"]["database"] == "unhealthy"


# ============================================================================
# SESSION STATUS TESTS
# ============================================================================

def test_session_status_enum():
    """
    Тест: SessionStatus enum имеет все необходимые статусы
    """
    assert SessionStatus.ACTIVE.value == "active"
    assert SessionStatus.PAUSED.value == "paused"
    assert SessionStatus.COMPLETED.value == "completed"
    assert SessionStatus.TIMED_OUT.value == "timed_out"
    assert SessionStatus.ABANDONED.value == "abandoned"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
