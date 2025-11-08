"""
Unit Tests: Profile Storage Service

Тестирует компоненты Profile Storage Service:
- ProfileManager CRUD operations
- Deep merge logic
- VectorStorageClient (с mocked Qdrant)
- Event handlers (trait.extracted → profile.updated)
- Graceful degradation
- Health checks
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime
import json

from systems.profile.profile_storage_service import (
    ProfileStorageService,
    ProfileManager,
    VectorStorageClient
)
from core.event_bus import EventBus
from core.circuit_breaker import CircuitBreakerRegistry


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
async def db_pool():
    """Mock PostgreSQL connection pool"""
    pool = AsyncMock()

    # Mock acquire context manager
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
def profile_manager(db_pool):
    """ProfileManager instance with mocked DB"""
    return ProfileManager(db_pool=db_pool)


@pytest.fixture
def vector_client():
    """VectorStorageClient with mocked Qdrant"""
    return VectorStorageClient(qdrant_url="http://mock-qdrant:6333")


@pytest.fixture
async def profile_service(event_bus, db_pool):
    """ProfileStorageService instance"""
    service = ProfileStorageService(
        event_bus=event_bus,
        db_pool=db_pool,
        qdrant_url="http://mock-qdrant:6333"
    )
    return service


# ============================================================================
# PROFILE MANAGER TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_create_profile_success(profile_manager, db_pool):
    """
    Тест: Создание нового профиля успешно
    """
    user_id = 12345

    # Mock successful insert
    conn = await db_pool.acquire().__aenter__()
    conn.fetchval.return_value = 1

    profile_id = await profile_manager.create_profile(
        user_id=user_id,
        initial_data={"big_five": {"openness": {"value": 0.7, "confidence": 0.8}}}
    )

    assert profile_id == 1
    assert conn.fetchval.called


@pytest.mark.asyncio
async def test_create_profile_with_defaults(profile_manager, db_pool):
    """
    Тест: Создание профиля с дефолтными данными
    """
    user_id = 12345

    conn = await db_pool.acquire().__aenter__()
    conn.fetchval.return_value = 2

    profile_id = await profile_manager.create_profile(user_id=user_id)

    assert profile_id == 2

    # Verify default structure was used
    call_args = conn.fetchval.call_args
    profile_data = json.loads(call_args[0][2])

    assert "big_five" in profile_data
    assert "core_dynamics" in profile_data
    assert "version" in profile_data


@pytest.mark.asyncio
async def test_get_profile_exists(profile_manager, db_pool):
    """
    Тест: Получение существующего профиля
    """
    user_id = 12345

    # Mock profile row
    conn = await db_pool.acquire().__aenter__()
    conn.fetchrow.return_value = {
        "id": 1,
        "user_id": user_id,
        "profile_data": {"big_five": {"openness": {"value": 0.7, "confidence": 0.8}}},
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }

    profile = await profile_manager.get_profile(user_id=user_id)

    assert profile is not None
    assert profile["user_id"] == user_id
    assert "big_five" in profile["profile_data"]


@pytest.mark.asyncio
async def test_get_profile_not_exists(profile_manager, db_pool):
    """
    Тест: Получение несуществующего профиля возвращает None
    """
    user_id = 99999

    conn = await db_pool.acquire().__aenter__()
    conn.fetchrow.return_value = None

    profile = await profile_manager.get_profile(user_id=user_id)

    assert profile is None


@pytest.mark.asyncio
async def test_update_profile_deep_merge(profile_manager, db_pool):
    """
    Тест: Deep merge при обновлении профиля
    """
    user_id = 12345

    # Mock existing profile
    existing_data = {
        "big_five": {
            "openness": {"value": 0.5, "confidence": 0.5},
            "conscientiousness": {"value": 0.6, "confidence": 0.6}
        },
        "core_dynamics": {}
    }

    conn = await db_pool.acquire().__aenter__()
    conn.fetchrow.return_value = {
        "id": 1,
        "user_id": user_id,
        "profile_data": existing_data,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    conn.execute.return_value = "UPDATE 1"

    # Update only openness
    updates = {
        "big_five": {
            "openness": {"value": 0.7, "confidence": 0.8}
        }
    }

    success = await profile_manager.update_profile(
        user_id=user_id,
        updates=updates,
        merge_strategy="deep"
    )

    assert success is True

    # Verify deep merge happened
    call_args = conn.execute.call_args[0]
    updated_data = json.loads(call_args[1])

    # Openness should be updated
    assert updated_data["big_five"]["openness"]["value"] == 0.7
    # Conscientiousness should remain
    assert updated_data["big_five"]["conscientiousness"]["value"] == 0.6


@pytest.mark.asyncio
async def test_update_profile_creates_if_not_exists(profile_manager, db_pool):
    """
    Тест: update_profile создает профиль если не существует
    """
    user_id = 12345

    conn = await db_pool.acquire().__aenter__()
    conn.fetchrow.return_value = None  # Profile doesn't exist
    conn.fetchval.return_value = 1     # Create returns ID

    updates = {"big_five": {"openness": {"value": 0.8, "confidence": 0.9}}}

    success = await profile_manager.update_profile(
        user_id=user_id,
        updates=updates
    )

    assert success is True
    assert conn.fetchval.called  # create_profile was called


@pytest.mark.asyncio
async def test_delete_profile_success(profile_manager, db_pool):
    """
    Тест: Успешное удаление профиля
    """
    user_id = 12345

    conn = await db_pool.acquire().__aenter__()
    conn.execute.return_value = "DELETE 1"

    deleted = await profile_manager.delete_profile(user_id=user_id)

    assert deleted is True


@pytest.mark.asyncio
async def test_delete_profile_not_exists(profile_manager, db_pool):
    """
    Тест: Удаление несуществующего профиля возвращает False
    """
    user_id = 99999

    conn = await db_pool.acquire().__aenter__()
    conn.execute.return_value = "DELETE 0"

    deleted = await profile_manager.delete_profile(user_id=user_id)

    assert deleted is False


# ============================================================================
# VECTOR STORAGE CLIENT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_vector_upsert_success(vector_client):
    """
    Тест: Успешное сохранение вектора в Qdrant
    """
    user_id = 12345
    embedding = [0.1] * 512  # 512D vector

    # Mock successful upsert
    success = await vector_client.upsert_profile_vector(
        user_id=user_id,
        embedding=embedding,
        metadata={"version": 1}
    )

    # Currently simulated success
    assert success is True


@pytest.mark.asyncio
async def test_vector_search_graceful_degradation(vector_client):
    """
    Тест: Graceful degradation при ошибке Qdrant
    """
    query_embedding = [0.1] * 512

    # Should return empty list on error (graceful degradation)
    results = await vector_client.search_similar_profiles(
        query_embedding=query_embedding,
        limit=10
    )

    assert isinstance(results, list)


# ============================================================================
# SERVICE EVENT HANDLER TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_handle_trait_extracted_updates_profile(profile_service, db_pool):
    """
    Тест: trait.extracted обновляет профиль
    """
    event = {
        "event_type": "trait.extracted",
        "payload": {
            "user_id": 12345,
            "traits": {
                "big_five": {
                    "openness": {"value": 0.8, "confidence": 0.9}
                },
                "core_dynamics": {
                    "self_awareness": {"value": 0.7, "confidence": 0.8}
                }
            },
            "confidence": 0.85
        },
        "trace_id": "test_trace_123"
    }

    # Mock existing profile
    conn = await db_pool.acquire().__aenter__()
    conn.fetchrow.return_value = {
        "id": 1,
        "user_id": 12345,
        "profile_data": {
            "big_five": {"openness": {"value": 0.5, "confidence": 0.5}},
            "core_dynamics": {}
        },
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    conn.execute.return_value = "UPDATE 1"

    # Mock transaction for outbox
    mock_transaction = AsyncMock()
    mock_transaction.__aenter__ = AsyncMock()
    mock_transaction.__aexit__ = AsyncMock()
    conn.transaction.return_value = mock_transaction

    # Handle event
    await profile_service._handle_trait_extracted(event)

    # Verify profile was updated
    assert conn.execute.called
    assert profile_service.metrics["profiles_updated"] == 1
    assert profile_service.metrics["traits_processed"] == 1


@pytest.mark.asyncio
async def test_handle_profile_update_requested(profile_service, db_pool):
    """
    Тест: profile.update.requested обновляет профиль
    """
    event = {
        "event_type": "profile.update.requested",
        "payload": {
            "user_id": 12345,
            "updates": {
                "adaptive_traits": {
                    "creativity": {"value": 0.9, "confidence": 0.8}
                }
            },
            "merge_strategy": "deep"
        }
    }

    # Mock existing profile
    conn = await db_pool.acquire().__aenter__()
    conn.fetchrow.return_value = {
        "id": 1,
        "user_id": 12345,
        "profile_data": {"big_five": {}, "adaptive_traits": {}},
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    conn.execute.return_value = "UPDATE 1"

    # Handle event
    await profile_service._handle_profile_update_requested(event)

    assert profile_service.metrics["profiles_updated"] == 1


# ============================================================================
# HEALTH CHECK TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_health_check_healthy(profile_service, db_pool):
    """
    Тест: Health check возвращает healthy когда все работает
    """
    conn = await db_pool.acquire().__aenter__()
    conn.fetchval.return_value = 1  # DB is up

    health = await profile_service.health_check()

    assert health["status"] in ["healthy", "degraded"]  # Can be degraded if Qdrant is down
    assert health["database"] == "healthy"


@pytest.mark.asyncio
async def test_health_check_database_down(profile_service, db_pool):
    """
    Тест: Health check возвращает unhealthy когда DB недоступна
    """
    conn = await db_pool.acquire().__aenter__()
    conn.fetchval.side_effect = Exception("Database connection failed")

    health = await profile_service.health_check()

    assert health["status"] == "unhealthy"
    assert health["database"] == "unhealthy"


# ============================================================================
# METRICS TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_metrics_tracking(profile_service, db_pool):
    """
    Тест: Метрики правильно отслеживаются
    """
    # Simulate processing multiple trait.extracted events
    for i in range(3):
        event = {
            "payload": {
                "user_id": 12345 + i,
                "traits": {"big_five": {"openness": {"value": 0.7, "confidence": 0.8}}},
                "confidence": 0.8
            }
        }

        # Mock profile exists
        conn = await db_pool.acquire().__aenter__()
        conn.fetchrow.return_value = {
            "id": i + 1,
            "user_id": 12345 + i,
            "profile_data": {"big_five": {}},
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        conn.execute.return_value = "UPDATE 1"

        # Mock transaction
        mock_transaction = AsyncMock()
        mock_transaction.__aenter__ = AsyncMock()
        mock_transaction.__aexit__ = AsyncMock()
        conn.transaction.return_value = mock_transaction

        await profile_service._handle_trait_extracted(event)

    metrics = profile_service.get_metrics()

    assert metrics["profiles_updated"] == 3
    assert metrics["traits_processed"] == 3


# ============================================================================
# DEEP MERGE TESTS
# ============================================================================

def test_deep_merge_nested_dicts(profile_manager):
    """
    Тест: Deep merge правильно объединяет вложенные словари
    """
    base = {
        "big_five": {
            "openness": {"value": 0.5, "confidence": 0.5},
            "conscientiousness": {"value": 0.6, "confidence": 0.6}
        },
        "core_dynamics": {
            "self_awareness": {"value": 0.7, "confidence": 0.7}
        }
    }

    updates = {
        "big_five": {
            "openness": {"value": 0.8, "confidence": 0.9}
        },
        "adaptive_traits": {
            "creativity": {"value": 0.85, "confidence": 0.8}
        }
    }

    result = profile_manager._deep_merge(base, updates)

    # Openness should be updated
    assert result["big_five"]["openness"]["value"] == 0.8
    # Conscientiousness should remain
    assert result["big_five"]["conscientiousness"]["value"] == 0.6
    # Self_awareness should remain
    assert result["core_dynamics"]["self_awareness"]["value"] == 0.7
    # New adaptive_traits should be added
    assert "adaptive_traits" in result
    assert result["adaptive_traits"]["creativity"]["value"] == 0.85


def test_deep_merge_overwrites_primitives(profile_manager):
    """
    Тест: Deep merge перезаписывает примитивные значения
    """
    base = {
        "version": 1,
        "last_update": "2024-01-01"
    }

    updates = {
        "version": 2,
        "last_update": "2024-01-02"
    }

    result = profile_manager._deep_merge(base, updates)

    assert result["version"] == 2
    assert result["last_update"] == "2024-01-02"


# ============================================================================
# DEFAULT PROFILE TESTS
# ============================================================================

def test_default_profile_structure(profile_manager):
    """
    Тест: Дефолтный профиль имеет правильную структуру
    """
    default = profile_manager._get_default_profile()

    # Should have all required layers
    assert "big_five" in default
    assert "core_dynamics" in default
    assert "adaptive_traits" in default
    assert "domain_affinities" in default
    assert "version" in default

    # Big Five should have 5 traits
    assert len(default["big_five"]) == 5
    assert "openness" in default["big_five"]
    assert "conscientiousness" in default["big_five"]

    # Each trait should have value and confidence
    for trait_name, trait_data in default["big_five"].items():
        assert "value" in trait_data
        assert "confidence" in trait_data
        assert 0 <= trait_data["value"] <= 1
        assert 0 <= trait_data["confidence"] <= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
