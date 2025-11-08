"""
Unit Tests: AI Router

Тестирует все компоненты AI Router:
- Model selection logic
- Circuit breaker integration
- Fallback mechanisms
- Cost tracking
- Metrics collection
- Health status
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime

from systems.analysis.ai_router import (
    AIRouter,
    AIModel,
    TaskComplexity,
    MODEL_COSTS,
    FALLBACK_CHAINS
)
from core.circuit_breaker import CircuitBreakerRegistry, CircuitState


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI HTTP client"""
    client = AsyncMock()
    client.post = AsyncMock()
    client.aclose = AsyncMock()
    return client


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic HTTP client"""
    client = AsyncMock()
    client.post = AsyncMock()
    client.aclose = AsyncMock()
    return client


@pytest.fixture
def ai_router(mock_openai_client, mock_anthropic_client):
    """AIRouter instance with mocked HTTP clients"""
    router = AIRouter(
        openai_api_key="test_openai_key",
        anthropic_api_key="test_anthropic_key"
    )

    # Replace clients with mocks
    router.openai_client = mock_openai_client
    router.anthropic_client = mock_anthropic_client

    return router


# ============================================================================
# MODEL SELECTION TESTS
# ============================================================================

def test_select_model_by_complexity_simple(ai_router):
    """
    Тест: SIMPLE задачи маршрутизируются на GPT-4o-mini
    """
    model = ai_router.select_model_by_complexity(TaskComplexity.SIMPLE)
    assert model == AIModel.GPT4O_MINI


def test_select_model_by_complexity_medium(ai_router):
    """
    Тест: MEDIUM задачи маршрутизируются на GPT-4o
    """
    model = ai_router.select_model_by_complexity(TaskComplexity.MEDIUM)
    assert model == AIModel.GPT4O


def test_select_model_by_complexity_complex(ai_router):
    """
    Тест: COMPLEX задачи маршрутизируются на Claude Sonnet
    """
    model = ai_router.select_model_by_complexity(TaskComplexity.COMPLEX)
    assert model == AIModel.CLAUDE_SONNET


# ============================================================================
# API CALL TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_call_openai_success(ai_router, mock_openai_client):
    """
    Тест: Успешный вызов OpenAI API
    """
    # Mock successful response
    mock_response = AsyncMock()
    mock_response.json.return_value = {
        "choices": [{
            "message": {"content": "Test response"}
        }],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150
        }
    }
    mock_response.raise_for_status = Mock()
    mock_openai_client.post.return_value = mock_response

    result = await ai_router.call_ai(
        model=AIModel.GPT4O_MINI,
        messages=[{"role": "user", "content": "test"}],
        max_tokens=100,
        allow_fallback=False
    )

    assert result["content"] == "Test response"
    assert result["model"] == AIModel.GPT4O_MINI.value
    assert result["tokens_used"] == 150
    assert result["fallback_used"] is False
    assert "cost_usd" in result


@pytest.mark.asyncio
async def test_call_ai_with_fallback(ai_router, mock_openai_client):
    """
    Тест: Fallback на альтернативную модель при сбое primary
    """
    # First call fails
    mock_openai_client.post.side_effect = [
        Exception("Primary model failed"),
        # Second call (fallback) succeeds
        AsyncMock(
            json=lambda: {
                "choices": [{"message": {"content": "Fallback response"}}],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150
                }
            },
            raise_for_status=Mock()
        )
    ]

    result = await ai_router.call_ai(
        model=AIModel.GPT4O,
        messages=[{"role": "user", "content": "test"}],
        max_tokens=100,
        allow_fallback=True
    )

    assert result["content"] == "Fallback response"
    assert result["fallback_used"] is True
    assert result["original_model"] == AIModel.GPT4O.value
    assert result["model"] == AIModel.GPT4O_MINI.value  # Fallback to mini


@pytest.mark.asyncio
async def test_call_ai_all_models_fail(ai_router, mock_openai_client):
    """
    Тест: Exception если все модели недоступны
    """
    # All calls fail
    mock_openai_client.post.side_effect = Exception("All models failed")

    with pytest.raises(Exception, match="All AI models failed"):
        await ai_router.call_ai(
            model=AIModel.GPT4O,
            messages=[{"role": "user", "content": "test"}],
            max_tokens=100,
            allow_fallback=True
        )


# ============================================================================
# CIRCUIT BREAKER INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_circuit_breaker_protects_calls(ai_router):
    """
    Тест: Circuit breaker защищает от repeated failures
    """
    # Get circuit breaker for GPT-4o-mini
    breaker = ai_router.circuit_breaker_registry.get(f"ai_model_{AIModel.GPT4O_MINI.value}")

    # Manually open the circuit
    breaker.state = CircuitState.OPEN
    breaker.opened_at = datetime.now()

    # Mock client
    ai_router.openai_client.post = AsyncMock(
        return_value=AsyncMock(
            json=lambda: {
                "choices": [{"message": {"content": "Test"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}
            },
            raise_for_status=Mock()
        )
    )

    # Call should fail because circuit is open
    from core.circuit_breaker import CircuitBreakerOpenError
    with pytest.raises(CircuitBreakerOpenError):
        await ai_router.call_ai(
            model=AIModel.GPT4O_MINI,
            messages=[{"role": "user", "content": "test"}],
            allow_fallback=False
        )


# ============================================================================
# COST TRACKING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_cost_tracking(ai_router, mock_openai_client):
    """
    Тест: Правильный расчет стоимости запросов
    """
    # Mock response
    mock_response = AsyncMock()
    mock_response.json.return_value = {
        "choices": [{
            "message": {"content": "Test"}
        }],
        "usage": {
            "prompt_tokens": 1000,
            "completion_tokens": 500,
            "total_tokens": 1500
        }
    }
    mock_response.raise_for_status = Mock()
    mock_openai_client.post.return_value = mock_response

    result = await ai_router.call_ai(
        model=AIModel.GPT4O_MINI,
        messages=[{"role": "user", "content": "test"}],
        allow_fallback=False
    )

    # Calculate expected cost
    expected_cost = (
        (1000 / 1_000_000) * MODEL_COSTS[AIModel.GPT4O_MINI]["input"] +
        (500 / 1_000_000) * MODEL_COSTS[AIModel.GPT4O_MINI]["output"]
    )

    assert result["cost_usd"] == pytest.approx(expected_cost, rel=0.01)


# ============================================================================
# METRICS TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_metrics_tracking(ai_router, mock_openai_client):
    """
    Тест: Метрики правильно отслеживаются
    """
    # Mock successful response
    mock_response = AsyncMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Test"}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
    }
    mock_response.raise_for_status = Mock()
    mock_openai_client.post.return_value = mock_response

    # Make 3 successful calls
    for _ in range(3):
        await ai_router.call_ai(
            model=AIModel.GPT4O_MINI,
            messages=[{"role": "user", "content": "test"}],
            allow_fallback=False
        )

    metrics = ai_router.get_metrics()

    assert metrics["total_requests"] == 3
    assert metrics["successful_requests"] == 3
    assert metrics["failed_requests"] == 0
    assert metrics["requests_by_model"][AIModel.GPT4O_MINI.value] == 3
    assert metrics["success_rate"] == 1.0


@pytest.mark.asyncio
async def test_metrics_fallback_tracking(ai_router, mock_openai_client):
    """
    Тест: Fallback использование отслеживается в метриках
    """
    # First call fails, second succeeds
    mock_openai_client.post.side_effect = [
        Exception("Primary failed"),
        AsyncMock(
            json=lambda: {
                "choices": [{"message": {"content": "Fallback"}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
            },
            raise_for_status=Mock()
        )
    ]

    await ai_router.call_ai(
        model=AIModel.GPT4O,
        messages=[{"role": "user", "content": "test"}],
        allow_fallback=True
    )

    metrics = ai_router.get_metrics()

    assert metrics["fallback_used"] == 1
    assert metrics["requests_by_model"][AIModel.GPT4O_MINI.value] == 1  # Fallback model


# ============================================================================
# HEALTH STATUS TESTS
# ============================================================================

def test_health_status_healthy(ai_router):
    """
    Тест: Здоровый статус когда все circuit breakers закрыты
    """
    # All breakers should be CLOSED by default
    health = ai_router.get_health_status()
    assert health == "healthy"


def test_health_status_degraded(ai_router):
    """
    Тест: Degraded статус когда некоторые breakers открыты
    """
    # Open one circuit breaker
    breaker = ai_router.circuit_breaker_registry.get(f"ai_model_{AIModel.GPT4O_MINI.value}")
    breaker.state = CircuitState.OPEN

    health = ai_router.get_health_status()
    assert health == "degraded"


def test_health_status_unhealthy(ai_router):
    """
    Тест: Unhealthy статус когда все breakers открыты
    """
    # Open all circuit breakers
    for model in AIModel:
        breaker = ai_router.circuit_breaker_registry.get(f"ai_model_{model.value}")
        breaker.state = CircuitState.OPEN

    health = ai_router.get_health_status()
    assert health == "unhealthy"


# ============================================================================
# FALLBACK CHAIN TESTS
# ============================================================================

def test_fallback_chains_configured():
    """
    Тест: Fallback chains правильно настроены
    """
    assert AIModel.CLAUDE_SONNET in FALLBACK_CHAINS
    assert AIModel.GPT4O in FALLBACK_CHAINS[AIModel.CLAUDE_SONNET]
    assert AIModel.GPT4O_MINI in FALLBACK_CHAINS[AIModel.CLAUDE_SONNET]

    assert AIModel.GPT4O in FALLBACK_CHAINS
    assert AIModel.GPT4O_MINI in FALLBACK_CHAINS[AIModel.GPT4O]

    # GPT-4o-mini has no fallback (cheapest model)
    assert len(FALLBACK_CHAINS[AIModel.GPT4O_MINI]) == 0


# ============================================================================
# CLOSE/CLEANUP TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_close_clients(ai_router):
    """
    Тест: HTTP клиенты правильно закрываются
    """
    await ai_router.close()

    assert ai_router.openai_client.aclose.called
    assert ai_router.anthropic_client.aclose.called


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
