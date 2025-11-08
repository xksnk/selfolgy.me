"""
Analysis Worker Service - Microservice для психологического анализа ответов

Реализует двухфазный анализ ответов пользователей:
1. Instant Analysis (<500ms) - быстрый feedback для пользователя
2. Deep Analysis (2-10s) - глубокий психологический анализ в фоне

Features:
- Event-driven architecture через Redis Streams
- Двухфазный анализ (instant + deep)
- AI Router с Circuit Breaker и fallback
- Retry logic для временных ошибок
- Trait extraction и векторизация
- Публикация результатов через Outbox Pattern

Architecture:
    user.answer.submitted → AnalysisWorkerService
    ↓
    1. Instant Analysis (GPT-4o-mini, <500ms)
    ↓
    analysis.instant.completed (публикуется сразу)
    ↓
    2. Deep Analysis (Claude/GPT-4, background)
    ↓
    analysis.completed (финальные результаты)

Events Consumed:
    - user.answer.submitted

Events Published:
    - analysis.instant.completed
    - analysis.completed
    - trait.extracted

Database Schema: selfology.analysis_system
"""

import asyncio
import asyncpg
import logging
import httpx
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

from systems.base import BaseSystem, HealthStatus
from core.event_bus import EventBus
from core.outbox_pattern import OutboxPublisher
from core.circuit_breaker import CircuitBreaker
from core.retry import retry_with_backoff
from core.domain_events import (
    AnalysisCompletedEventV1,
    TraitExtractedEventV1,
    EventPriority
)

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================

class AnalysisType(str, Enum):
    """Типы анализа"""
    INSTANT = "instant"  # Быстрый анализ <500ms
    DEEP = "deep"        # Глубокий анализ 2-10s


class AIModel(str, Enum):
    """AI модели для анализа"""
    CLAUDE_SONNET = "claude-sonnet-4"
    GPT4 = "gpt-4"
    GPT4O_MINI = "gpt-4o-mini"


# ============================================================================
# ANALYSIS ENGINE
# ============================================================================

class AnalysisEngine:
    """
    Движок для психологического анализа

    Features:
    - Двухфазный анализ
    - Trait extraction
    - Sentiment analysis
    - Pattern recognition
    """

    def __init__(
        self,
        ai_router: 'AIRouter',
        db_pool: asyncpg.Pool
    ):
        self.ai_router = ai_router
        self.db_pool = db_pool

    async def analyze_instant(
        self,
        user_id: int,
        question_id: str,
        answer_text: str,
        question_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Instant анализ (<500ms)

        Быстрый feedback для пользователя:
        - Sentiment (positive/neutral/negative)
        - Answer quality score
        - Basic traits hints

        Args:
            user_id: ID пользователя
            question_id: ID вопроса
            answer_text: Текст ответа
            question_context: Контекст вопроса (depth, energy, domain)

        Returns:
            Instant analysis results
        """
        start_time = datetime.now()

        try:
            # Используем GPT-4o-mini для скорости
            prompt = self._build_instant_analysis_prompt(
                question_id,
                answer_text,
                question_context
            )

            result = await self.ai_router.call_ai(
                model=AIModel.GPT4O_MINI,
                messages=[
                    {"role": "system", "content": "You are a psychology expert. Provide instant feedback."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.5
            )

            # Parse результат
            analysis = self._parse_instant_result(result)

            # Добавляем metadata
            analysis["analysis_type"] = AnalysisType.INSTANT.value
            analysis["model_used"] = AIModel.GPT4O_MINI.value
            analysis["processing_time_ms"] = (datetime.now() - start_time).total_seconds() * 1000

            logger.info(
                f"Instant analysis completed for user {user_id} "
                f"in {analysis['processing_time_ms']:.0f}ms"
            )

            return analysis

        except Exception as e:
            logger.error(f"Instant analysis failed: {e}", exc_info=True)
            # Fallback: базовый анализ без AI
            return self._fallback_instant_analysis(answer_text)

    async def analyze_deep(
        self,
        user_id: int,
        question_id: str,
        answer_text: str,
        question_context: Optional[Dict[str, Any]] = None,
        user_history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Deep анализ (2-10s)

        Глубокий психологический анализ:
        - Trait extraction (Big Five + custom traits)
        - Psychological patterns
        - Growth insights
        - Recommendations

        Args:
            user_id: ID пользователя
            question_id: ID вопроса
            answer_text: Текст ответа
            question_context: Контекст вопроса
            user_history: История ответов пользователя

        Returns:
            Deep analysis results
        """
        start_time = datetime.now()

        try:
            # Используем Claude Sonnet или GPT-4 для глубины
            prompt = self._build_deep_analysis_prompt(
                question_id,
                answer_text,
                question_context,
                user_history
            )

            result = await self.ai_router.call_ai(
                model=AIModel.CLAUDE_SONNET,
                messages=[
                    {"role": "system", "content": "You are an expert psychologist analyzing personality traits."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )

            # Parse результат
            analysis = self._parse_deep_result(result)

            # Extract traits
            extracted_traits = self._extract_traits(analysis)

            analysis["extracted_traits"] = extracted_traits
            analysis["analysis_type"] = AnalysisType.DEEP.value
            analysis["model_used"] = result.get("model", AIModel.CLAUDE_SONNET.value)
            analysis["processing_time_ms"] = (datetime.now() - start_time).total_seconds() * 1000

            logger.info(
                f"Deep analysis completed for user {user_id} "
                f"in {analysis['processing_time_ms']:.0f}ms, "
                f"{len(extracted_traits)} traits extracted"
            )

            return analysis

        except Exception as e:
            logger.error(f"Deep analysis failed: {e}", exc_info=True)
            raise

    def _build_instant_analysis_prompt(
        self,
        question_id: str,
        answer_text: str,
        question_context: Optional[Dict[str, Any]]
    ) -> str:
        """Строит prompt для instant анализа"""
        return f"""
Analyze this answer quickly and provide instant feedback:

Question ID: {question_id}
Answer: "{answer_text}"

Provide JSON response:
{{
    "sentiment": "positive/neutral/negative",
    "quality_score": <0-10>,
    "brief_insight": "<1 sentence feedback>"
}}
"""

    def _build_deep_analysis_prompt(
        self,
        question_id: str,
        answer_text: str,
        question_context: Optional[Dict[str, Any]],
        user_history: Optional[List[Dict[str, Any]]]
    ) -> str:
        """Строит prompt для deep анализа"""
        history_text = ""
        if user_history:
            history_text = "\n\nUser's previous answers:\n" + "\n".join([
                f"- Q: {h.get('question_id')}: {h.get('answer_text', '')[:100]}"
                for h in user_history[-5:]  # Last 5 answers
            ])

        return f"""
Deep psychological analysis of this answer:

Question ID: {question_id}
Context: {json.dumps(question_context) if question_context else 'N/A'}
Answer: "{answer_text}"
{history_text}

Extract psychological traits (Big Five + custom):

JSON response:
{{
    "big_five": {{
        "openness": <0-1>,
        "conscientiousness": <0-1>,
        "extraversion": <0-1>,
        "agreeableness": <0-1>,
        "neuroticism": <0-1>
    }},
    "custom_traits": {{
        "emotional_depth": <0-1>,
        "self_awareness": <0-1>,
        "growth_mindset": <0-1>
    }},
    "patterns": ["pattern1", "pattern2"],
    "insights": ["insight1", "insight2"],
    "recommendations": ["rec1", "rec2"]
}}
"""

    def _parse_instant_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Парсит результат instant анализа"""
        content = result.get("content", "")

        # Extract JSON from content
        try:
            import re
            json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                return parsed
        except Exception as e:
            logger.warning(f"Failed to parse instant result: {e}")

        # Fallback
        return {
            "sentiment": "neutral",
            "quality_score": 5,
            "brief_insight": "Thank you for sharing!"
        }

    def _parse_deep_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Парсит результат deep анализа"""
        content = result.get("content", "")

        # Extract JSON from content
        try:
            import re
            json_match = re.search(r'\{[\s\S]*\}', content, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                return parsed
        except Exception as e:
            logger.warning(f"Failed to parse deep result: {e}")

        # Fallback
        return {
            "big_five": {
                "openness": 0.5,
                "conscientiousness": 0.5,
                "extraversion": 0.5,
                "agreeableness": 0.5,
                "neuroticism": 0.5
            },
            "custom_traits": {},
            "patterns": [],
            "insights": [],
            "recommendations": []
        }

    def _extract_traits(self, analysis: Dict[str, Any]) -> Dict[str, float]:
        """Извлекает traits из анализа"""
        traits = {}

        # Big Five
        big_five = analysis.get("big_five", {})
        for trait, value in big_five.items():
            traits[f"big_five_{trait}"] = float(value)

        # Custom traits
        custom = analysis.get("custom_traits", {})
        for trait, value in custom.items():
            traits[trait] = float(value)

        return traits

    def _fallback_instant_analysis(self, answer_text: str) -> Dict[str, Any]:
        """Fallback анализ без AI"""
        length = len(answer_text)

        return {
            "sentiment": "neutral",
            "quality_score": min(10, max(1, length / 20)),
            "brief_insight": "Thank you for your thoughtful answer!",
            "analysis_type": AnalysisType.INSTANT.value,
            "model_used": "fallback",
            "processing_time_ms": 0
        }


# ============================================================================
# ANALYSIS WORKER SERVICE
# ============================================================================

class AnalysisWorkerService(BaseSystem):
    """
    Analysis Worker Service

    Микросервис для психологического анализа ответов.
    """

    def __init__(
        self,
        event_bus: EventBus,
        db_pool: asyncpg.Pool,
        ai_router: 'AIRouter'
    ):
        super().__init__(name="analysis_worker_service", event_bus=event_bus)

        self.db_pool = db_pool
        self.ai_router = ai_router
        self.outbox_publisher = OutboxPublisher(schema="selfology")
        self.analysis_engine = AnalysisEngine(ai_router, db_pool)

    async def start(self):
        """Запускает Analysis Worker Service"""
        logger.info("Starting Analysis Worker Service...")

        # Event Consumer
        await self.add_event_consumer(
            event_types=["user.answer.submitted"],
            handler=self.handle_answer_submitted,
            consumer_name="analysis_worker"
        )

        self.state = self.state.RUNNING
        logger.info("✅ Analysis Worker Service started")

    async def stop(self):
        """Graceful shutdown"""
        logger.info("Stopping Analysis Worker Service...")
        await self.stop_all_consumers()
        logger.info("✅ Analysis Worker Service stopped")

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

        # AI Router
        checks["ai_router"] = self.ai_router.get_health_status()

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

    async def handle_answer_submitted(
        self,
        event_type: str,
        payload: Dict[str, Any]
    ):
        """
        Обрабатывает событие user.answer.submitted

        Запускает двухфазный анализ:
        1. Instant analysis → немедленный feedback
        2. Deep analysis → background processing
        """
        user_id = payload["user_id"]
        question_id = payload["question_id"]
        answer_text = payload["answer_text"]
        session_id = payload.get("session_id")
        trace_id = payload.get("trace_id")

        logger.info(
            f"Processing answer from user {user_id} for question {question_id}"
        )

        try:
            # Phase 1: Instant Analysis (<500ms)
            instant_result = await self.analysis_engine.analyze_instant(
                user_id=user_id,
                question_id=question_id,
                answer_text=answer_text
            )

            # Publish instant results
            await self._publish_instant_analysis(
                user_id=user_id,
                question_id=question_id,
                session_id=session_id,
                instant_result=instant_result,
                trace_id=trace_id
            )

            # Phase 2: Deep Analysis (background)
            asyncio.create_task(
                self._process_deep_analysis(
                    user_id=user_id,
                    question_id=question_id,
                    answer_text=answer_text,
                    session_id=session_id,
                    trace_id=trace_id
                )
            )

            self.increment_metric("answers_analyzed")
            self.increment_metric("instant_analyses")

        except Exception as e:
            logger.error(
                f"Failed to process answer: {e}",
                exc_info=True,
                extra={
                    "user_id": user_id,
                    "question_id": question_id
                }
            )
            self.increment_metric("analysis_errors")
            raise

    async def _process_deep_analysis(
        self,
        user_id: int,
        question_id: str,
        answer_text: str,
        session_id: Optional[int],
        trace_id: Optional[str]
    ):
        """Background task для deep analysis"""
        try:
            # Load user history
            user_history = await self._load_user_history(user_id)

            # Deep analysis
            deep_result = await self.analysis_engine.analyze_deep(
                user_id=user_id,
                question_id=question_id,
                answer_text=answer_text,
                user_history=user_history
            )

            # Save results
            await self._save_analysis_results(
                user_id=user_id,
                question_id=question_id,
                analysis_result=deep_result
            )

            # Publish deep analysis completed
            await self._publish_deep_analysis(
                user_id=user_id,
                question_id=question_id,
                session_id=session_id,
                deep_result=deep_result,
                trace_id=trace_id
            )

            # Publish extracted traits
            await self._publish_traits(
                user_id=user_id,
                question_id=question_id,
                traits=deep_result.get("extracted_traits", {}),
                trace_id=trace_id
            )

            self.increment_metric("deep_analyses")

        except Exception as e:
            logger.error(f"Deep analysis failed: {e}", exc_info=True)
            self.increment_metric("deep_analysis_errors")

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    async def _publish_instant_analysis(
        self,
        user_id: int,
        question_id: str,
        session_id: Optional[int],
        instant_result: Dict[str, Any],
        trace_id: Optional[str]
    ):
        """Публикует результат instant анализа"""
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                await self.outbox_publisher.publish(
                    conn,
                    "analysis.instant.completed",
                    {
                        "user_id": user_id,
                        "question_id": question_id,
                        "session_id": session_id,
                        "sentiment": instant_result.get("sentiment"),
                        "quality_score": instant_result.get("quality_score"),
                        "brief_insight": instant_result.get("brief_insight"),
                        "processing_time_ms": instant_result.get("processing_time_ms")
                    },
                    trace_id=trace_id
                )

    async def _publish_deep_analysis(
        self,
        user_id: int,
        question_id: str,
        session_id: Optional[int],
        deep_result: Dict[str, Any],
        trace_id: Optional[str]
    ):
        """Публикует результат deep анализа"""
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                await self.outbox_publisher.publish(
                    conn,
                    "analysis.completed",
                    {
                        "user_id": user_id,
                        "question_id": question_id,
                        "session_id": session_id,
                        "extracted_traits": deep_result.get("extracted_traits", {}),
                        "patterns": deep_result.get("patterns", []),
                        "insights": deep_result.get("insights", []),
                        "processing_time_ms": deep_result.get("processing_time_ms")
                    },
                    trace_id=trace_id
                )

    async def _publish_traits(
        self,
        user_id: int,
        question_id: str,
        traits: Dict[str, float],
        trace_id: Optional[str]
    ):
        """Публикует извлеченные traits"""
        if not traits:
            return

        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                await self.outbox_publisher.publish(
                    conn,
                    "trait.extracted",
                    {
                        "user_id": user_id,
                        "question_id": question_id,
                        "traits": traits,
                        "extracted_at": datetime.now().isoformat()
                    },
                    trace_id=trace_id
                )

    async def _save_analysis_results(
        self,
        user_id: int,
        question_id: str,
        analysis_result: Dict[str, Any]
    ):
        """Сохраняет результаты анализа в БД"""
        async with self.db_pool.acquire() as conn:
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
                "v2"  # Version 2 with deep analysis
            )

    async def _load_user_history(
        self,
        user_id: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Загружает историю ответов пользователя"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT question_id, answer_text, created_at
                FROM selfology.user_answers_new
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                user_id,
                limit
            )

            return [dict(row) for row in rows]
