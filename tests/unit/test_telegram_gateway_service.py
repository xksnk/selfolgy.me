"""
Unit Tests: Telegram Gateway Service

Тестирует компоненты Telegram Gateway:
- RateLimiter (sliding window algorithm)
- StateManager (Redis + fallback)
- Event handlers (command/message/callback → events)
- Message sending (event → Telegram API)
- Circuit Breaker integration
- Health checks
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from datetime import datetime

from systems.telegram.telegram_gateway_service import (
    TelegramGatewayService,
    RateLimiter,
    StateManager,
    UserStates
)
from core.event_bus import EventBus


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
async def redis_client():
    """Mock Redis client"""
    client = AsyncMock()
    client.zadd = AsyncMock()
    client.zremrangebyscore = AsyncMock()
    client.zcard = AsyncMock(return_value=1)
    client.expire = AsyncMock()
    client.get = AsyncMock()
    client.setex = AsyncMock()
    client.ping = AsyncMock()
    return client


@pytest.fixture
async def db_pool():
    """Mock PostgreSQL pool"""
    pool = AsyncMock()

    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=1)
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
def rate_limiter(redis_client):
    """RateLimiter instance"""
    return RateLimiter(
        redis_client=redis_client,
        max_requests=10,
        window_seconds=60
    )


@pytest.fixture
def state_manager(redis_client):
    """StateManager instance"""
    return StateManager(redis_client=redis_client)


# ============================================================================
# RATE LIMITER TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_rate_limiter_allows_within_limit(rate_limiter, redis_client):
    """
    Тест: Rate limiter разрешает запросы в пределах лимита
    """
    user_id = 12345

    # Simulate 5 requests (within limit of 10)
    redis_client.zcard.return_value = 5

    allowed = await rate_limiter.is_allowed(user_id)

    assert allowed is True


@pytest.mark.asyncio
async def test_rate_limiter_blocks_over_limit(rate_limiter, redis_client):
    """
    Тест: Rate limiter блокирует при превышении лимита
    """
    user_id = 12345

    # Simulate 11 requests (over limit of 10)
    redis_client.zcard.return_value = 11

    allowed = await rate_limiter.is_allowed(user_id)

    assert allowed is False


@pytest.mark.asyncio
async def test_rate_limiter_fails_open_on_error(rate_limiter, redis_client):
    """
    Тест: Rate limiter fail-open при ошибке Redis
    """
    user_id = 12345

    # Simulate Redis error
    redis_client.zadd.side_effect = Exception("Redis connection failed")

    # Should allow request on error (fail open)
    allowed = await rate_limiter.is_allowed(user_id)

    assert allowed is True


@pytest.mark.asyncio
async def test_rate_limiter_sets_expiration(rate_limiter, redis_client):
    """
    Тест: Rate limiter устанавливает TTL для ключа
    """
    user_id = 12345
    redis_client.zcard.return_value = 5

    await rate_limiter.is_allowed(user_id)

    # Verify expire was called
    assert redis_client.expire.called
    call_args = redis_client.expire.call_args[0]
    assert call_args[1] == 60  # window_seconds


# ============================================================================
# STATE MANAGER TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_state_manager_get_from_redis(state_manager, redis_client):
    """
    Тест: StateManager получает состояние из Redis
    """
    user_id = 12345

    # Mock Redis response
    redis_client.get.return_value = "onboarding_active"

    state = await state_manager.get_state(user_id)

    assert state == "onboarding_active"


@pytest.mark.asyncio
async def test_state_manager_fallback_on_redis_error(state_manager, redis_client):
    """
    Тест: StateManager использует fallback при ошибке Redis
    """
    user_id = 12345

    # Simulate Redis error
    redis_client.get.side_effect = Exception("Redis connection failed")

    # Set fallback value
    state_manager.fallback_storage[user_id] = "chat_active"

    state = await state_manager.get_state(user_id)

    assert state == "chat_active"


@pytest.mark.asyncio
async def test_state_manager_set_state_redis(state_manager, redis_client):
    """
    Тест: StateManager сохраняет состояние в Redis
    """
    user_id = 12345
    new_state = "waiting_for_answer"

    await state_manager.set_state(user_id, new_state, ttl=3600)

    # Verify setex was called with correct params
    assert redis_client.setex.called
    call_args = redis_client.setex.call_args[0]
    assert call_args[1] == 3600  # TTL
    assert call_args[2] == new_state


@pytest.mark.asyncio
async def test_state_manager_set_state_updates_fallback(state_manager, redis_client):
    """
    Тест: StateManager всегда обновляет fallback storage
    """
    user_id = 12345
    new_state = "onboarding_complete"

    # Simulate Redis error
    redis_client.setex.side_effect = Exception("Redis error")

    await state_manager.set_state(user_id, new_state)

    # Fallback should be updated even if Redis fails
    assert state_manager.fallback_storage[user_id] == new_state


@pytest.mark.asyncio
async def test_state_manager_get_data(state_manager, redis_client):
    """
    Тест: StateManager получает FSM данные
    """
    user_id = 12345

    # Mock Redis response with JSON data
    import json
    data = {"question_id": 123, "session_id": 456}
    redis_client.get.return_value = json.dumps(data)

    result = await state_manager.get_data(user_id)

    assert result == data


@pytest.mark.asyncio
async def test_state_manager_set_data(state_manager, redis_client):
    """
    Тест: StateManager сохраняет FSM данные
    """
    user_id = 12345
    data = {"answer": "test answer", "question_id": 123}

    await state_manager.set_data(user_id, data, ttl=7200)

    assert redis_client.setex.called


# ============================================================================
# GATEWAY SERVICE EVENT HANDLER TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_handle_send_message_request(event_bus, db_pool, redis_client):
    """
    Тест: message.send.requested отправляет сообщение через Telegram API
    """
    # Create service with mocked bot
    with patch('systems.telegram.telegram_gateway_service.Bot') as MockBot:
        mock_bot_instance = AsyncMock()
        MockBot.return_value = mock_bot_instance

        service = TelegramGatewayService(
            event_bus=event_bus,
            db_pool=db_pool,
            redis_client=redis_client,
            bot_token="test_token"
        )

        # Mock event
        event = {
            "payload": {
                "user_id": 12345,
                "text": "Test message",
                "parse_mode": "HTML"
            }
        }

        await service._handle_send_message_request(event)

        # Verify bot.send_message was called
        assert mock_bot_instance.send_message.called
        call_args = mock_bot_instance.send_message.call_args
        assert call_args.kwargs["chat_id"] == 12345
        assert call_args.kwargs["text"] == "Test message"


@pytest.mark.asyncio
async def test_handle_send_message_with_keyboard(event_bus, db_pool, redis_client):
    """
    Тест: Отправка сообщения с клавиатурой
    """
    with patch('systems.telegram.telegram_gateway_service.Bot') as MockBot:
        mock_bot_instance = AsyncMock()
        MockBot.return_value = mock_bot_instance

        service = TelegramGatewayService(
            event_bus=event_bus,
            db_pool=db_pool,
            redis_client=redis_client,
            bot_token="test_token"
        )

        # Mock keyboard
        keyboard = {"inline_keyboard": [[{"text": "Button"}]]}

        event = {
            "payload": {
                "user_id": 12345,
                "text": "Choose option:",
                "keyboard": keyboard
            }
        }

        await service._handle_send_message_request(event)

        # Verify keyboard was passed
        call_args = mock_bot_instance.send_message.call_args
        assert call_args.kwargs["reply_markup"] == keyboard


@pytest.mark.asyncio
async def test_handle_state_change_request(event_bus, db_pool, redis_client):
    """
    Тест: state.change.requested изменяет состояние пользователя
    """
    with patch('systems.telegram.telegram_gateway_service.Bot'):
        service = TelegramGatewayService(
            event_bus=event_bus,
            db_pool=db_pool,
            redis_client=redis_client,
            bot_token="test_token"
        )

        event = {
            "payload": {
                "user_id": 12345,
                "new_state": "chat_active"
            }
        }

        await service._handle_state_change_request(event)

        # Verify state was set
        assert redis_client.setex.called


# ============================================================================
# CIRCUIT BREAKER TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_send_message_respects_circuit_breaker(event_bus, db_pool, redis_client):
    """
    Тест: Circuit Breaker защищает Telegram API вызовы
    """
    with patch('systems.telegram.telegram_gateway_service.Bot') as MockBot:
        mock_bot_instance = AsyncMock()
        MockBot.return_value = mock_bot_instance

        service = TelegramGatewayService(
            event_bus=event_bus,
            db_pool=db_pool,
            redis_client=redis_client,
            bot_token="test_token"
        )

        # Simulate Telegram API failure
        mock_bot_instance.send_message.side_effect = Exception("Telegram API error")

        event = {
            "payload": {
                "user_id": 12345,
                "text": "Test"
            }
        }

        # Should raise exception
        with pytest.raises(Exception):
            await service._handle_send_message_request(event)

        # Error metric should increase
        assert service.metrics["errors"] > 0


# ============================================================================
# HEALTH CHECK TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_health_check_healthy(event_bus, db_pool, redis_client):
    """
    Тест: Health check возвращает healthy когда все работает
    """
    with patch('systems.telegram.telegram_gateway_service.Bot'):
        service = TelegramGatewayService(
            event_bus=event_bus,
            db_pool=db_pool,
            redis_client=redis_client,
            bot_token="test_token"
        )

        # Mock successful ping/queries
        conn = await db_pool.acquire().__aenter__()
        conn.fetchval.return_value = 1
        redis_client.ping.return_value = True

        health = await service.health_check()

        assert health["redis"] == "healthy"
        assert health["database"] == "healthy"


@pytest.mark.asyncio
async def test_health_check_degraded_redis(event_bus, db_pool, redis_client):
    """
    Тест: Health check degraded при сбое Redis
    """
    with patch('systems.telegram.telegram_gateway_service.Bot'):
        service = TelegramGatewayService(
            event_bus=event_bus,
            db_pool=db_pool,
            redis_client=redis_client,
            bot_token="test_token"
        )

        # Mock Redis failure
        redis_client.ping.side_effect = Exception("Redis connection failed")

        # DB is healthy
        conn = await db_pool.acquire().__aenter__()
        conn.fetchval.return_value = 1

        health = await service.health_check()

        assert health["status"] == "degraded"
        assert health["redis"] == "degraded"


# ============================================================================
# METRICS TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_metrics_tracking(event_bus, db_pool, redis_client):
    """
    Тест: Метрики правильно отслеживаются
    """
    with patch('systems.telegram.telegram_gateway_service.Bot') as MockBot:
        mock_bot_instance = AsyncMock()
        MockBot.return_value = mock_bot_instance

        service = TelegramGatewayService(
            event_bus=event_bus,
            db_pool=db_pool,
            redis_client=redis_client,
            bot_token="test_token"
        )

        # Send 3 messages
        for i in range(3):
            event = {
                "payload": {
                    "user_id": 12345 + i,
                    "text": f"Message {i}"
                }
            }
            await service._handle_send_message_request(event)

        metrics = service.get_metrics()

        assert metrics["messages_sent"] == 3


# ============================================================================
# FSM STATES TESTS
# ============================================================================

def test_user_states_defined():
    """
    Тест: UserStates содержит все необходимые состояния
    """
    # Verify all required states exist
    assert hasattr(UserStates, 'new_user')
    assert hasattr(UserStates, 'gdpr_pending')
    assert hasattr(UserStates, 'onboarding_active')
    assert hasattr(UserStates, 'waiting_for_answer')
    assert hasattr(UserStates, 'processing_answer')
    assert hasattr(UserStates, 'onboarding_paused')
    assert hasattr(UserStates, 'onboarding_complete')
    assert hasattr(UserStates, 'chat_active')
    assert hasattr(UserStates, 'chat_paused')


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
