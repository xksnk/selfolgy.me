"""
Analysis System - Example Microservice Implementation

Пример микросервиса на базе BaseSystem для демонстрации event-driven архитектуры.

Функциональность:
- Прослушивает событие user.answer.submitted
- Анализирует ответы пользователя через AI API (GPT-4o)
- Извлекает психологические черты
- Публикует событие analysis.completed
- Использует Circuit Breaker для защиты от сбоев AI API
- Использует Retry Pattern для fault tolerance
- Сохраняет результаты в БД через Outbox Pattern

Architecture:
    user.answer.submitted → AnalysisSystem → AI Analysis → analysis.completed

Integration Points:
- Event Bus: Consumer для user.answer.submitted
- Database: Сохранение результатов анализа
- AI API: GPT-4o для психологического анализа
- Outbox Pattern: Гарантированная публикация событий
- Circuit Breaker: Защита от сбоев AI API
- Retry Pattern: Автоматические retry при временных ошибках
"""

import asyncio
import asyncpg
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import httpx

from systems.base import BaseSystem, HealthStatus
from core.event_bus import EventBus
from core.outbox_pattern import OutboxPublisher
from core.circuit_breaker import CircuitBreaker
from core.retry import retry_with_backoff, RetryConfig
from core.domain_events import (
    UserAnswerSubmittedEventV1,
    AnalysisCompletedEventV1,
    EventPriority
)

logger = logging.getLogger(__name__)


# ============================================================================
# ANALYSIS SYSTEM
# ============================================================================

class AnalysisSystem(BaseSystem):
    """
    Analysis System - Микросервис для психологического анализа ответов

    Демонстрирует:
    - Event-driven architecture
    - Circuit Breaker для AI API
    - Retry Pattern для fault tolerance
    - Outbox Pattern для guaranteed delivery
    - Health checks и metrics
    - Graceful shutdown
    """

    def __init__(
        self,
        event_bus: EventBus,
        db_pool: asyncpg.Pool,
        openai_api_key: str,
        openai_base_url: str = "https://api.openai.com/v1"
    ):
        """
        Args:
            event_bus: Event Bus instance
            db_pool: PostgreSQL connection pool
            openai_api_key: OpenAI API key
            openai_base_url: OpenAI API base URL
        """
        super().__init__(name="analysis_system", event_bus=event_bus)

        self.db_pool = db_pool
        self.openai_api_key = openai_api_key
        self.openai_base_url = openai_base_url

        # Outbox Publisher
        self.outbox_publisher = OutboxPublisher(schema="selfology")

        # HTTP client для AI API
        self.http_client: Optional[httpx.AsyncClient] = None

        # Circuit Breaker для AI API
        self.ai_circuit_breaker: Optional[CircuitBreaker] = None

    # ========================================================================
    # LIFECYCLE METHODS
    # ========================================================================

    async def start(self):
        """
        Запускает Analysis System

        Setup:
        1. HTTP client для AI API
        2. Circuit Breaker для AI API
        3. Event Consumer для user.answer.submitted
        4. Background tasks
        """
        logger.info("Starting Analysis System...")

        # 1. HTTP client
        self.http_client = httpx.AsyncClient(
            base_url=self.openai_base_url,
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
        )

        # 2. Circuit Breaker для AI API
        self.ai_circuit_breaker = self.register_circuit_breaker(
            name="openai_api",
            failure_threshold=5,
            timeout=60.0,
            exponential_backoff_multiplier=2.0
        )

        # 3. Event Consumer для user.answer.submitted
        await self.add_event_consumer(
            event_types=["user.answer.submitted"],
            handler=self.handle_user_answer,
            consumer_name="analysis_worker"
        )

        # Mark as running
        self.state = self.state.RUNNING

        logger.info("✅ Analysis System started successfully")

    async def stop(self):
        """
        Graceful shutdown Analysis System

        Cleanup:
        1. Stop event consumers
        2. Close HTTP client
        3. Wait for pending tasks
        """
        logger.info("Stopping Analysis System...")

        # Stop consumers
        await self.stop_all_consumers()

        # Close HTTP client
        if self.http_client:
            await self.http_client.aclose()

        logger.info("✅ Analysis System stopped successfully")

    async def health_check(self) -> Dict[str, Any]:
        """
        Health check Analysis System

        Проверяет:
        - Database connection
        - AI API availability (через Circuit Breaker)
        - Event Bus connection
        """
        checks = {}

        # Check database
        try:
            async with self.db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            checks["database"] = "healthy"
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            checks["database"] = "unhealthy"

        # Check AI API (через Circuit Breaker state)
        if self.ai_circuit_breaker:
            breaker_state = self.ai_circuit_breaker.state.value
            if breaker_state == "closed":
                checks["ai_api"] = "healthy"
            elif breaker_state == "half_open":
                checks["ai_api"] = "degraded"
            else:
                checks["ai_api"] = "unhealthy"
        else:
            checks["ai_api"] = "unknown"

        # Check Event Bus
        try:
            await self.event_bus.redis.ping()
            checks["event_bus"] = "healthy"
        except Exception as e:
            logger.error(f"Event Bus health check failed: {e}")
            checks["event_bus"] = "unhealthy"

        # Overall status
        if all(v == "healthy" for v in checks.values()):
            status = HealthStatus.HEALTHY
        elif any(v == "unhealthy" for v in checks.values()):
            status = HealthStatus.UNHEALTHY
        else:
            status = HealthStatus.DEGRADED

        return {
            "status": status.value,
            "checks": checks,
            "metrics": self.get_metrics()
        }

    # ========================================================================
    # EVENT HANDLERS
    # ========================================================================

    async def handle_user_answer(self, event_type: str, payload: Dict[str, Any]):
        """
        Обрабатывает событие user.answer.submitted

        Flow:
        1. Валидация события
        2. AI анализ ответа (с Circuit Breaker + Retry)
        3. Сохранение результатов в БД
        4. Публикация события analysis.completed (через Outbox)

        Args:
            event_type: Тип события
            payload: Данные события
        """
        try:
            # Валидация события
            event = UserAnswerSubmittedEventV1(**payload)

            logger.info(
                f"Processing answer from user {event.user_id} "
                f"for question {event.question_id}"
            )

            # AI анализ
            analysis_result = await self._analyze_answer(
                user_id=event.user_id,
                question_id=event.question_id,
                answer_text=event.answer_text
            )

            # Сохранение в БД + публикация события (атомарно через Outbox)
            await self._save_and_publish_analysis(
                user_id=event.user_id,
                question_id=event.question_id,
                analysis_result=analysis_result,
                trace_id=event.trace_id
            )

            # Metrics
            self.increment_metric("events_processed")
            self.increment_metric("successful_analyses")

            logger.info(
                f"✅ Analysis completed for user {event.user_id}, "
                f"question {event.question_id}"
            )

        except Exception as e:
            logger.error(
                f"Failed to process answer event: {e}",
                exc_info=True,
                extra={
                    "event_type": event_type,
                    "user_id": payload.get("user_id"),
                    "question_id": payload.get("question_id")
                }
            )

            self.increment_metric("events_failed")
            raise

    # ========================================================================
    # AI ANALYSIS
    # ========================================================================

    @retry_with_backoff(
        max_attempts=3,
        base_delay=1.0,
        exponential_base=2.0
    )
    async def _analyze_answer(
        self,
        user_id: int,
        question_id: str,
        answer_text: str
    ) -> Dict[str, Any]:
        """
        Анализирует ответ пользователя через AI API

        Использует:
        - Circuit Breaker для защиты от сбоев
        - Retry Pattern для fault tolerance

        Args:
            user_id: ID пользователя
            question_id: ID вопроса
            answer_text: Текст ответа

        Returns:
            Результат анализа с извлеченными чертами
        """
        # Circuit Breaker защита
        async with self.ai_circuit_breaker:
            # Call AI API
            response = await self._call_openai_api(
                question_id=question_id,
                answer_text=answer_text
            )

            # Parse результат
            analysis = self._parse_ai_response(response)

            logger.debug(
                f"AI analysis completed for user {user_id}: "
                f"{len(analysis.get('extracted_traits', {}))} traits extracted"
            )

            return analysis

    async def _call_openai_api(
        self,
        question_id: str,
        answer_text: str
    ) -> Dict[str, Any]:
        """
        Вызов OpenAI API для психологического анализа

        Args:
            question_id: ID вопроса
            answer_text: Текст ответа

        Returns:
            AI response
        """
        prompt = self._build_analysis_prompt(question_id, answer_text)

        request_data = {
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a professional psychologist analyzing user responses. "
                        "Extract psychological traits and provide structured insights."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }

        # HTTP request с timeout
        response = await self.http_client.post(
            "/chat/completions",
            json=request_data
        )

        response.raise_for_status()

        return response.json()

    def _build_analysis_prompt(
        self,
        question_id: str,
        answer_text: str
    ) -> str:
        """
        Строит prompt для AI анализа

        Args:
            question_id: ID вопроса
            answer_text: Текст ответа

        Returns:
            Prompt для AI
        """
        return f"""
Analyze this psychological response:

Question ID: {question_id}
User Answer: "{answer_text}"

Extract psychological traits in JSON format:
{{
    "openness": <float 0-1>,
    "conscientiousness": <float 0-1>,
    "extraversion": <float 0-1>,
    "agreeableness": <float 0-1>,
    "neuroticism": <float 0-1>,
    "emotional_depth": <float 0-1>,
    "self_awareness": <float 0-1>
}}

Provide brief insights (2-3 sentences).
"""

    def _parse_ai_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Парсит ответ от AI API

        Args:
            response: Raw AI response

        Returns:
            Parsed analysis result
        """
        # Extract content from OpenAI response
        content = response["choices"][0]["message"]["content"]

        # Simplified parsing (в продакшене нужен robust JSON parser)
        # Здесь демонстрационный вариант
        import json
        import re

        # Извлекаем JSON из response
        json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
        if json_match:
            traits = json.loads(json_match.group())
        else:
            traits = {}

        return {
            "extracted_traits": traits,
            "raw_response": content,
            "model": response.get("model"),
            "analyzed_at": datetime.now().isoformat()
        }

    # ========================================================================
    # DATABASE & OUTBOX
    # ========================================================================

    async def _save_and_publish_analysis(
        self,
        user_id: int,
        question_id: str,
        analysis_result: Dict[str, Any],
        trace_id: Optional[str] = None
    ):
        """
        Сохраняет результат анализа в БД и публикует событие (атомарно через Outbox)

        Args:
            user_id: ID пользователя
            question_id: ID вопроса
            analysis_result: Результат AI анализа
            trace_id: Trace ID для distributed tracing
        """
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                # 1. Сохранение результата анализа
                await conn.execute(
                    """
                    INSERT INTO selfology.answer_analysis
                    (user_id, question_id, extracted_traits, analysis_version, analyzed_at)
                    VALUES ($1, $2, $3, $4, NOW())
                    ON CONFLICT (user_id, question_id, analysis_version)
                    DO UPDATE SET
                        extracted_traits = EXCLUDED.extracted_traits,
                        analyzed_at = NOW()
                    """,
                    user_id,
                    question_id,
                    analysis_result.get("extracted_traits", {}),
                    "v1"
                )

                # 2. Публикация события через Outbox (в той же транзакции!)
                event_payload = {
                    "user_id": user_id,
                    "question_id": question_id,
                    "extracted_traits": analysis_result.get("extracted_traits", {}),
                    "analysis_version": "v1",
                    "analyzed_at": analysis_result.get("analyzed_at")
                }

                await self.outbox_publisher.publish(
                    conn,
                    "analysis.completed",
                    event_payload,
                    trace_id=trace_id
                )

        logger.debug(
            f"Analysis saved and event published for user {user_id}, "
            f"question {question_id}"
        )


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

async def create_analysis_system(
    event_bus: EventBus,
    db_config: Dict[str, Any],
    openai_api_key: str
) -> AnalysisSystem:
    """
    Factory для создания Analysis System

    Args:
        event_bus: Event Bus instance
        db_config: Database configuration
        openai_api_key: OpenAI API key

    Returns:
        Configured AnalysisSystem instance
    """
    # Create database pool
    db_pool = await asyncpg.create_pool(
        host=db_config.get("host", "n8n-postgres"),
        port=db_config.get("port", 5432),
        user=db_config.get("user", "postgres"),
        password=db_config["password"],
        database=db_config.get("database", "n8n"),
        min_size=2,
        max_size=10
    )

    # Create system
    system = AnalysisSystem(
        event_bus=event_bus,
        db_pool=db_pool,
        openai_api_key=openai_api_key
    )

    return system


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    """
    Пример запуска Analysis System
    """
    import os
    from core.event_bus import get_event_bus

    async def main():
        # Configuration
        db_config = {
            "host": "n8n-postgres",
            "port": 5432,
            "user": "postgres",
            "password": os.getenv("POSTGRES_PASSWORD"),
            "database": "n8n"
        }

        openai_api_key = os.getenv("OPENAI_API_KEY")

        # Create Event Bus
        event_bus = await get_event_bus()

        # Create Analysis System
        system = await create_analysis_system(
            event_bus=event_bus,
            db_config=db_config,
            openai_api_key=openai_api_key
        )

        # Start system (context manager для graceful shutdown)
        async with system:
            logger.info("Analysis System running... Press Ctrl+C to stop")

            # Health check
            health = await system.health_check()
            logger.info(f"Health status: {health}")

            # Run until interrupted
            try:
                await asyncio.Event().wait()
            except KeyboardInterrupt:
                logger.info("Shutting down...")

    # Run
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
