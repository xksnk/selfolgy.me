"""
AI Router with Circuit Breaker and Fallback Logic

Интеллектуальная маршрутизация AI запросов между моделями:
- Claude Sonnet 4 (10%) - премиум анализ
- GPT-4o (75%) - основной рабочий конь
- GPT-4o-mini (15%) - быстрые простые задачи

Features:
- Circuit Breaker для каждой модели
- Automatic fallback при сбоях
- Cost optimization (smart routing)
- Retry logic с exponential backoff
- Request/response logging
- Performance metrics

Architecture:
    Request → AI Router
    ↓
    1. Select model based on task complexity
    2. Check circuit breaker status
    3. Call AI API with retry
    4. Fallback to alternative model if needed
    5. Return result + metrics
"""

import asyncio
import httpx
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
import json

from core.circuit_breaker import CircuitBreaker, CircuitBreakerRegistry
from core.retry import retry_with_backoff

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================

class AIModel(str, Enum):
    """Поддерживаемые AI модели"""
    CLAUDE_SONNET = "claude-sonnet-4"
    GPT4O = "gpt-4o"
    GPT4O_MINI = "gpt-4o-mini"


class TaskComplexity(str, Enum):
    """Сложность задачи для выбора модели"""
    SIMPLE = "simple"      # GPT-4o-mini
    MEDIUM = "medium"      # GPT-4o
    COMPLEX = "complex"    # Claude Sonnet или GPT-4


# Model costs (per 1M tokens)
MODEL_COSTS = {
    AIModel.CLAUDE_SONNET: {"input": 3.0, "output": 15.0},
    AIModel.GPT4O: {"input": 2.5, "output": 10.0},
    AIModel.GPT4O_MINI: {"input": 0.15, "output": 0.6}
}

# Fallback chains
FALLBACK_CHAINS = {
    AIModel.CLAUDE_SONNET: [AIModel.GPT4O, AIModel.GPT4O_MINI],
    AIModel.GPT4O: [AIModel.GPT4O_MINI],
    AIModel.GPT4O_MINI: []  # No fallback for cheapest model
}


# ============================================================================
# AI ROUTER
# ============================================================================

class AIRouter:
    """
    AI Router с Circuit Breaker и intelligent fallback

    Features:
    - Smart model selection
    - Circuit breaker per model
    - Automatic fallback
    - Cost tracking
    - Performance metrics
    """

    def __init__(
        self,
        openai_api_key: str,
        anthropic_api_key: Optional[str] = None,
        circuit_breaker_registry: Optional[CircuitBreakerRegistry] = None
    ):
        """
        Args:
            openai_api_key: OpenAI API key
            anthropic_api_key: Anthropic API key (optional)
            circuit_breaker_registry: Registry for circuit breakers
        """
        self.openai_api_key = openai_api_key
        self.anthropic_api_key = anthropic_api_key

        # HTTP clients
        self.openai_client = httpx.AsyncClient(
            base_url="https://api.openai.com/v1",
            headers={
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        )

        self.anthropic_client = None
        if anthropic_api_key:
            self.anthropic_client = httpx.AsyncClient(
                base_url="https://api.anthropic.com/v1",
                headers={
                    "x-api-key": anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                },
                timeout=30.0
            )

        # Circuit Breakers
        self.circuit_breaker_registry = circuit_breaker_registry or CircuitBreakerRegistry()
        self._setup_circuit_breakers()

        # Metrics
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "fallback_used": 0,
            "total_cost_usd": 0.0,
            "requests_by_model": {model.value: 0 for model in AIModel},
            "avg_latency_ms": {}
        }

    def _setup_circuit_breakers(self):
        """Настраивает circuit breakers для каждой модели"""
        for model in AIModel:
            breaker = CircuitBreaker(
                name=f"ai_model_{model.value}",
                failure_threshold=5,
                timeout=60.0,
                exponential_backoff_multiplier=2.0
            )
            self.circuit_breaker_registry.register(breaker)

    async def call_ai(
        self,
        model: AIModel,
        messages: List[Dict[str, str]],
        max_tokens: int = 500,
        temperature: float = 0.7,
        allow_fallback: bool = True
    ) -> Dict[str, Any]:
        """
        Вызывает AI модель с fallback logic

        Args:
            model: Модель для использования
            messages: Сообщения для AI
            max_tokens: Максимум токенов в ответе
            temperature: Температура (0-1)
            allow_fallback: Разрешить fallback на другие модели

        Returns:
            {
                "content": str,
                "model": str,
                "tokens_used": int,
                "cost_usd": float,
                "latency_ms": float,
                "fallback_used": bool
            }
        """
        start_time = datetime.now()
        self.metrics["total_requests"] += 1
        fallback_used = False

        try:
            # Try primary model
            result = await self._call_model(model, messages, max_tokens, temperature)

            self.metrics["successful_requests"] += 1
            self.metrics["requests_by_model"][model.value] += 1

            result["fallback_used"] = False
            result["latency_ms"] = (datetime.now() - start_time).total_seconds() * 1000

            # Update cost
            self.metrics["total_cost_usd"] += result.get("cost_usd", 0.0)

            return result

        except Exception as e:
            logger.warning(f"Model {model.value} failed: {e}")

            # Try fallback if allowed
            if allow_fallback and model in FALLBACK_CHAINS:
                for fallback_model in FALLBACK_CHAINS[model]:
                    try:
                        logger.info(f"Trying fallback model: {fallback_model.value}")

                        result = await self._call_model(
                            fallback_model,
                            messages,
                            max_tokens,
                            temperature
                        )

                        self.metrics["successful_requests"] += 1
                        self.metrics["fallback_used"] += 1
                        self.metrics["requests_by_model"][fallback_model.value] += 1

                        result["fallback_used"] = True
                        result["original_model"] = model.value
                        result["latency_ms"] = (datetime.now() - start_time).total_seconds() * 1000

                        self.metrics["total_cost_usd"] += result.get("cost_usd", 0.0)

                        return result

                    except Exception as fallback_error:
                        logger.warning(
                            f"Fallback model {fallback_model.value} also failed: {fallback_error}"
                        )
                        continue

            # All attempts failed
            self.metrics["failed_requests"] += 1
            raise Exception(f"All AI models failed for request. Last error: {e}")

    @retry_with_backoff(max_attempts=3, base_delay=1.0)
    async def _call_model(
        self,
        model: AIModel,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float
    ) -> Dict[str, Any]:
        """
        Вызывает конкретную модель с Circuit Breaker защитой

        Args:
            model: Модель
            messages: Сообщения
            max_tokens: Макс токены
            temperature: Температура

        Returns:
            Response from AI
        """
        # Get circuit breaker for this model
        breaker = self.circuit_breaker_registry.get(f"ai_model_{model.value}")

        # Call with circuit breaker protection
        async with breaker:
            if model == AIModel.CLAUDE_SONNET:
                return await self._call_claude(messages, max_tokens, temperature)
            else:
                return await self._call_openai(model, messages, max_tokens, temperature)

    async def _call_openai(
        self,
        model: AIModel,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float
    ) -> Dict[str, Any]:
        """Вызывает OpenAI API"""
        request_data = {
            "model": model.value,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        response = await self.openai_client.post(
            "/chat/completions",
            json=request_data
        )

        response.raise_for_status()
        data = response.json()

        # Extract result
        content = data["choices"][0]["message"]["content"]
        tokens_used = data["usage"]["total_tokens"]

        # Calculate cost
        input_tokens = data["usage"]["prompt_tokens"]
        output_tokens = data["usage"]["completion_tokens"]
        cost_usd = (
            (input_tokens / 1_000_000) * MODEL_COSTS[model]["input"] +
            (output_tokens / 1_000_000) * MODEL_COSTS[model]["output"]
        )

        return {
            "content": content,
            "model": model.value,
            "tokens_used": tokens_used,
            "cost_usd": cost_usd
        }

    async def _call_claude(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float
    ) -> Dict[str, Any]:
        """Вызывает Anthropic Claude API"""
        if not self.anthropic_client:
            raise Exception("Anthropic API key not configured")

        # Convert messages format
        system_message = None
        conversation = []

        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                conversation.append(msg)

        request_data = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": conversation
        }

        if system_message:
            request_data["system"] = system_message

        response = await self.anthropic_client.post(
            "/messages",
            json=request_data
        )

        response.raise_for_status()
        data = response.json()

        # Extract result
        content = data["content"][0]["text"]
        tokens_used = data["usage"]["input_tokens"] + data["usage"]["output_tokens"]

        # Calculate cost
        input_tokens = data["usage"]["input_tokens"]
        output_tokens = data["usage"]["output_tokens"]
        cost_usd = (
            (input_tokens / 1_000_000) * MODEL_COSTS[AIModel.CLAUDE_SONNET]["input"] +
            (output_tokens / 1_000_000) * MODEL_COSTS[AIModel.CLAUDE_SONNET]["output"]
        )

        return {
            "content": content,
            "model": AIModel.CLAUDE_SONNET.value,
            "tokens_used": tokens_used,
            "cost_usd": cost_usd
        }

    def select_model_by_complexity(self, complexity: TaskComplexity) -> AIModel:
        """
        Выбирает модель на основе сложности задачи

        Args:
            complexity: Сложность задачи

        Returns:
            Рекомендуемая модель
        """
        if complexity == TaskComplexity.SIMPLE:
            return AIModel.GPT4O_MINI
        elif complexity == TaskComplexity.MEDIUM:
            return AIModel.GPT4O
        else:  # COMPLEX
            return AIModel.CLAUDE_SONNET

    def get_metrics(self) -> Dict[str, Any]:
        """Возвращает метрики AI Router"""
        success_rate = 0.0
        if self.metrics["total_requests"] > 0:
            success_rate = self.metrics["successful_requests"] / self.metrics["total_requests"]

        return {
            **self.metrics,
            "success_rate": round(success_rate, 3),
            "avg_cost_per_request": (
                self.metrics["total_cost_usd"] / max(self.metrics["total_requests"], 1)
            )
        }

    def get_health_status(self) -> str:
        """Возвращает статус здоровья AI Router"""
        # Check circuit breakers
        all_breakers = self.circuit_breaker_registry.get_all()

        open_breakers = [
            b for b in all_breakers
            if b.state.value == "open"
        ]

        if len(open_breakers) == len(all_breakers):
            return "unhealthy"  # All models down
        elif len(open_breakers) > 0:
            return "degraded"  # Some models down
        else:
            return "healthy"  # All models up

    async def close(self):
        """Закрывает HTTP клиенты"""
        await self.openai_client.aclose()
        if self.anthropic_client:
            await self.anthropic_client.aclose()


# ============================================================================
# FACTORY
# ============================================================================

def create_ai_router(
    openai_api_key: str,
    anthropic_api_key: Optional[str] = None
) -> AIRouter:
    """
    Factory для создания AI Router

    Args:
        openai_api_key: OpenAI API key
        anthropic_api_key: Anthropic API key (optional)

    Returns:
        Configured AIRouter instance
    """
    return AIRouter(
        openai_api_key=openai_api_key,
        anthropic_api_key=anthropic_api_key
    )
