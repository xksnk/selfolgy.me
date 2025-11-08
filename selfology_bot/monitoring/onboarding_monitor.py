"""
Comprehensive Onboarding Pipeline Monitoring System

Отслеживает весь путь пользователя от Telegram до обновления Digital Personality:
1. Telegram ответ → SQL
2. SQL → AI анализ (deep_analysis_pipeline)
3. AI анализ → Векторизация (Qdrant)
4. Векторизация → Обновление DP (PostgreSQL)

Интегрируется с существующей системой мониторинга без изменения основного кода.
"""

import asyncio
import asyncpg
import httpx
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import json
import os

logger = logging.getLogger(__name__)


class OnboardingStage(Enum):
    """Этапы обработки ответа пользователя"""
    TELEGRAM_RECEIVED = "telegram_received"
    SQL_SAVED = "sql_saved"
    AI_ANALYZING = "ai_analyzing"
    AI_COMPLETED = "ai_completed"
    VECTORIZATION_PENDING = "vectorization_pending"
    VECTORIZATION_COMPLETED = "vectorization_completed"
    DP_UPDATE_PENDING = "dp_update_pending"
    DP_UPDATE_COMPLETED = "dp_update_completed"
    FULLY_PROCESSED = "fully_processed"


class ProcessingStatus(Enum):
    """Статусы обработки"""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    STUCK = "stuck"
    TIMEOUT = "timeout"


@dataclass
class OnboardingMetrics:
    """Метрики производительности онбординга"""
    # Timing metrics (milliseconds)
    sql_save_time: float = 0.0
    ai_analysis_time: float = 0.0
    vectorization_time: float = 0.0
    dp_update_time: float = 0.0
    total_pipeline_time: float = 0.0

    # Success rates
    ai_success_rate: float = 100.0
    vectorization_success_rate: float = 100.0
    dp_update_success_rate: float = 100.0

    # Queue depths
    pending_analyses: int = 0
    pending_vectorizations: int = 0
    pending_dp_updates: int = 0

    # Error counts
    ai_errors: int = 0
    vectorization_errors: int = 0
    dp_update_errors: int = 0

    # Retry stats
    total_retries: int = 0
    retry_success_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'timing': {
                'sql_save_ms': self.sql_save_time,
                'ai_analysis_ms': self.ai_analysis_time,
                'vectorization_ms': self.vectorization_time,
                'dp_update_ms': self.dp_update_time,
                'total_pipeline_ms': self.total_pipeline_time
            },
            'success_rates': {
                'ai_analysis': f"{self.ai_success_rate:.1f}%",
                'vectorization': f"{self.vectorization_success_rate:.1f}%",
                'dp_update': f"{self.dp_update_success_rate:.1f}%"
            },
            'queue_depth': {
                'pending_analyses': self.pending_analyses,
                'pending_vectorizations': self.pending_vectorizations,
                'pending_dp_updates': self.pending_dp_updates
            },
            'errors': {
                'ai_errors': self.ai_errors,
                'vectorization_errors': self.vectorization_errors,
                'dp_update_errors': self.dp_update_errors
            },
            'retries': {
                'total': self.total_retries,
                'success_rate': f"{self.retry_success_rate:.1f}%"
            }
        }


@dataclass
class PipelineAlert:
    """Алерт о проблеме в pipeline"""
    alert_type: str  # "error", "slow_processing", "stuck_task", "high_failure_rate"
    severity: str    # "warning", "error", "critical"
    message: str
    details: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: Optional[int] = None
    answer_id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'alert_type': self.alert_type,
            'severity': self.severity,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp.isoformat(),
            'user_id': self.user_id,
            'answer_id': self.answer_id
        }


class OnboardingPipelineMonitor:
    """
    Comprehensive monitoring для всего онбординг pipeline

    Отслеживает:
    - Время обработки на каждом этапе
    - Success/failure rates
    - Зависшие background tasks
    - Очереди обработки
    - Ошибки и их причины
    """

    def __init__(self, db_config: Dict[str, Any]):
        self.db_config = db_config
        self.db_pool: Optional[asyncpg.Pool] = None
        self.http_client = httpx.AsyncClient(timeout=10.0)

        # Metrics storage
        self.metrics_history = deque(maxlen=1000)
        self.current_metrics = OnboardingMetrics()

        # Alert storage
        self.alerts = deque(maxlen=500)
        self.alert_callbacks: List[Callable] = []

        # Monitoring state
        self.monitoring_active = False
        self.monitoring_tasks: List[asyncio.Task] = []

        # Configuration
        self.slow_processing_threshold = int(os.getenv('ONBOARDING_SLOW_THRESHOLD_MS', 15000))  # 15 sec
        self.stuck_task_threshold = int(os.getenv('ONBOARDING_STUCK_THRESHOLD_SEC', 300))  # 5 min
        self.high_failure_rate_threshold = float(os.getenv('ONBOARDING_FAILURE_THRESHOLD', 0.2))  # 20%

        # Health check URLs
        self.qdrant_url = os.getenv('QDRANT_URL', 'http://localhost:6333')
        self.openai_api_key = os.getenv('OPENAI_API_KEY', '')

        logger.info("Onboarding Pipeline Monitor initialized")

    async def initialize(self):
        """Инициализация мониторинга"""
        try:
            # Setup database pool
            self.db_pool = await asyncpg.create_pool(
                **self.db_config,
                min_size=2,
                max_size=10,
                command_timeout=30
            )
            logger.info("Database pool for monitoring initialized")

        except Exception as e:
            logger.error(f"Failed to initialize monitoring: {e}")
            raise

    async def start_monitoring(self):
        """Запустить мониторинг"""
        if self.monitoring_active:
            logger.warning("Monitoring already active")
            return

        self.monitoring_active = True
        logger.info("Starting onboarding pipeline monitoring")

        # Запускаем мониторинг задачи
        self.monitoring_tasks = [
            asyncio.create_task(self._monitor_pipeline_loop()),
            asyncio.create_task(self._collect_metrics_loop()),
            asyncio.create_task(self._detect_stuck_tasks_loop()),
            asyncio.create_task(self._health_check_loop())
        ]

        await asyncio.gather(*self.monitoring_tasks, return_exceptions=True)

    async def stop_monitoring(self):
        """Остановить мониторинг"""
        self.monitoring_active = False

        for task in self.monitoring_tasks:
            task.cancel()

        if self.monitoring_tasks:
            await asyncio.gather(*self.monitoring_tasks, return_exceptions=True)

        if self.db_pool:
            await self.db_pool.close()

        await self.http_client.aclose()

        logger.info("Monitoring stopped")

    async def _monitor_pipeline_loop(self):
        """Основной цикл мониторинга pipeline"""
        while self.monitoring_active:
            try:
                # Проверяем статусы обработки
                await self._check_processing_statuses()

                # Проверяем медленную обработку
                await self._check_slow_processing()

                # Проверяем failure rates
                await self._check_failure_rates()

                await asyncio.sleep(10)  # Проверка каждые 10 секунд

            except Exception as e:
                logger.error(f"Error in pipeline monitoring loop: {e}")
                await asyncio.sleep(30)

    async def _collect_metrics_loop(self):
        """Цикл сбора метрик"""
        while self.monitoring_active:
            try:
                metrics = await self.collect_current_metrics()
                self.current_metrics = metrics
                self.metrics_history.append({
                    'timestamp': datetime.now(timezone.utc),
                    'metrics': metrics
                })

                await asyncio.sleep(30)  # Сбор каждые 30 секунд

            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
                await asyncio.sleep(60)

    async def _detect_stuck_tasks_loop(self):
        """Цикл детектирования зависших задач"""
        while self.monitoring_active:
            try:
                stuck_tasks = await self.detect_stuck_background_tasks()

                for task_info in stuck_tasks:
                    alert = PipelineAlert(
                        alert_type="stuck_task",
                        severity="critical",
                        message=f"Background task stuck for {task_info['stuck_minutes']:.1f} minutes",
                        details=task_info,
                        user_id=task_info.get('user_id'),
                        answer_id=task_info.get('answer_id')
                    )
                    await self._trigger_alert(alert)

                await asyncio.sleep(60)  # Проверка каждую минуту

            except Exception as e:
                logger.error(f"Error detecting stuck tasks: {e}")
                await asyncio.sleep(120)

    async def _health_check_loop(self):
        """Цикл проверки здоровья сервисов"""
        while self.monitoring_active:
            try:
                health_status = await self.check_services_health()

                # Алерты при проблемах с сервисами
                for service, status in health_status.items():
                    if status['status'] != 'healthy':
                        alert = PipelineAlert(
                            alert_type="service_unhealthy",
                            severity="critical",
                            message=f"Service {service} is {status['status']}",
                            details=status
                        )
                        await self._trigger_alert(alert)

                await asyncio.sleep(60)  # Проверка каждую минуту

            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(120)

    async def _check_processing_statuses(self):
        """Проверка статусов обработки"""
        try:
            async with self.db_pool.acquire() as conn:
                # Проверяем pending статусы которые долго висят
                query = """
                    SELECT
                        aa.id,
                        aa.user_answer_id,
                        ua.session_id,
                        os.user_id,
                        aa.vectorization_status,
                        aa.dp_update_status,
                        aa.processed_at,
                        EXTRACT(EPOCH FROM (NOW() - aa.processed_at)) as seconds_since_analysis
                    FROM selfology.answer_analysis aa
                    JOIN selfology.user_answers_new ua ON ua.id = aa.user_answer_id
                    JOIN selfology.onboarding_sessions os ON os.id = ua.session_id
                    WHERE
                        (aa.vectorization_status = 'pending' OR aa.dp_update_status = 'pending')
                        AND aa.processed_at < NOW() - INTERVAL '5 minutes'
                    ORDER BY aa.processed_at ASC
                    LIMIT 20
                """

                rows = await conn.fetch(query)

                for row in rows:
                    alert = PipelineAlert(
                        alert_type="stuck_processing",
                        severity="warning",
                        message=f"Processing stuck for {row['seconds_since_analysis']/60:.1f} minutes",
                        details={
                            'analysis_id': row['id'],
                            'answer_id': row['user_answer_id'],
                            'vectorization_status': row['vectorization_status'],
                            'dp_update_status': row['dp_update_status'],
                            'minutes_stuck': row['seconds_since_analysis'] / 60
                        },
                        user_id=row['user_id'],
                        answer_id=row['user_answer_id']
                    )
                    await self._trigger_alert(alert)

        except Exception as e:
            logger.error(f"Error checking processing statuses: {e}")

    async def _check_slow_processing(self):
        """Проверка медленной обработки"""
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT
                        aa.id,
                        aa.user_answer_id,
                        os.user_id,
                        aa.processing_time_ms,
                        aa.background_task_duration_ms
                    FROM selfology.answer_analysis aa
                    JOIN selfology.user_answers_new ua ON ua.id = aa.user_answer_id
                    JOIN selfology.onboarding_sessions os ON os.id = ua.session_id
                    WHERE
                        aa.processed_at > NOW() - INTERVAL '1 hour'
                        AND aa.background_task_duration_ms > $1
                    ORDER BY aa.background_task_duration_ms DESC
                    LIMIT 10
                """

                rows = await conn.fetch(query, self.slow_processing_threshold)

                for row in rows:
                    alert = PipelineAlert(
                        alert_type="slow_processing",
                        severity="warning",
                        message=f"Slow background processing: {row['background_task_duration_ms']}ms",
                        details={
                            'analysis_id': row['id'],
                            'answer_id': row['user_answer_id'],
                            'ai_time_ms': row['processing_time_ms'],
                            'background_time_ms': row['background_task_duration_ms']
                        },
                        user_id=row['user_id'],
                        answer_id=row['user_answer_id']
                    )
                    await self._trigger_alert(alert)

        except Exception as e:
            logger.error(f"Error checking slow processing: {e}")

    async def _check_failure_rates(self):
        """Проверка процента ошибок"""
        try:
            metrics = await self.collect_current_metrics()

            # Проверяем каждый этап
            if metrics.ai_success_rate < (1 - self.high_failure_rate_threshold) * 100:
                alert = PipelineAlert(
                    alert_type="high_failure_rate",
                    severity="critical",
                    message=f"High AI analysis failure rate: {100-metrics.ai_success_rate:.1f}%",
                    details={'stage': 'ai_analysis', 'success_rate': metrics.ai_success_rate}
                )
                await self._trigger_alert(alert)

            if metrics.vectorization_success_rate < (1 - self.high_failure_rate_threshold) * 100:
                alert = PipelineAlert(
                    alert_type="high_failure_rate",
                    severity="critical",
                    message=f"High vectorization failure rate: {100-metrics.vectorization_success_rate:.1f}%",
                    details={'stage': 'vectorization', 'success_rate': metrics.vectorization_success_rate}
                )
                await self._trigger_alert(alert)

            if metrics.dp_update_success_rate < (1 - self.high_failure_rate_threshold) * 100:
                alert = PipelineAlert(
                    alert_type="high_failure_rate",
                    severity="critical",
                    message=f"High DP update failure rate: {100-metrics.dp_update_success_rate:.1f}%",
                    details={'stage': 'dp_update', 'success_rate': metrics.dp_update_success_rate}
                )
                await self._trigger_alert(alert)

        except Exception as e:
            logger.error(f"Error checking failure rates: {e}")

    async def collect_current_metrics(self) -> OnboardingMetrics:
        """Собрать текущие метрики"""
        try:
            async with self.db_pool.acquire() as conn:
                # Метрики за последний час
                query = """
                    WITH recent_analyses AS (
                        SELECT
                            aa.*,
                            ua.answered_at,
                            EXTRACT(EPOCH FROM (aa.processed_at - ua.answered_at)) * 1000 as sql_to_ai_ms
                        FROM selfology.answer_analysis aa
                        JOIN selfology.user_answers_new ua ON ua.id = aa.user_answer_id
                        WHERE aa.processed_at > NOW() - INTERVAL '1 hour'
                    )
                    SELECT
                        -- Timing averages
                        AVG(processing_time_ms) as avg_ai_time,
                        AVG(background_task_duration_ms) as avg_background_time,

                        -- Success rates
                        COUNT(*) FILTER (WHERE vectorization_status = 'success')::float / NULLIF(COUNT(*), 0) * 100 as vec_success_rate,
                        COUNT(*) FILTER (WHERE dp_update_status = 'success')::float / NULLIF(COUNT(*), 0) * 100 as dp_success_rate,

                        -- Pending counts
                        COUNT(*) FILTER (WHERE vectorization_status = 'pending') as pending_vec,
                        COUNT(*) FILTER (WHERE dp_update_status = 'pending') as pending_dp,

                        -- Error counts
                        COUNT(*) FILTER (WHERE vectorization_status = 'failed') as vec_errors,
                        COUNT(*) FILTER (WHERE dp_update_status = 'failed') as dp_errors,

                        -- Retry stats
                        SUM(retry_count) as total_retries,
                        COUNT(*) FILTER (WHERE retry_count > 0 AND vectorization_status = 'success')::float /
                            NULLIF(COUNT(*) FILTER (WHERE retry_count > 0), 0) * 100 as retry_success_rate

                    FROM recent_analyses
                """

                row = await conn.fetchrow(query)

                metrics = OnboardingMetrics(
                    ai_analysis_time=float(row['avg_ai_time'] or 0),
                    total_pipeline_time=float(row['avg_background_time'] or 0),

                    vectorization_success_rate=float(row['vec_success_rate'] or 100),
                    dp_update_success_rate=float(row['dp_success_rate'] or 100),
                    ai_success_rate=100.0,  # AI success определяем наличием analysis_id

                    pending_vectorizations=int(row['pending_vec'] or 0),
                    pending_dp_updates=int(row['pending_dp'] or 0),

                    vectorization_errors=int(row['vec_errors'] or 0),
                    dp_update_errors=int(row['dp_errors'] or 0),

                    total_retries=int(row['total_retries'] or 0),
                    retry_success_rate=float(row['retry_success_rate'] or 0)
                )

                return metrics

        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            return OnboardingMetrics()

    async def detect_stuck_background_tasks(self) -> List[Dict[str, Any]]:
        """Детектирование зависших background tasks"""
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT
                        aa.id as analysis_id,
                        aa.user_answer_id as answer_id,
                        os.user_id,
                        ua.question_json_id,
                        aa.processed_at,
                        aa.vectorization_status,
                        aa.dp_update_status,
                        aa.background_task_completed,
                        EXTRACT(EPOCH FROM (NOW() - aa.processed_at)) / 60 as stuck_minutes
                    FROM selfology.answer_analysis aa
                    JOIN selfology.user_answers_new ua ON ua.id = aa.user_answer_id
                    JOIN selfology.onboarding_sessions os ON os.id = ua.session_id
                    WHERE
                        aa.background_task_completed = FALSE
                        AND aa.processed_at < NOW() - INTERVAL '$1 seconds'
                    ORDER BY aa.processed_at ASC
                    LIMIT 20
                """

                rows = await conn.fetch(query.replace('$1', str(self.stuck_task_threshold)))

                stuck_tasks = []
                for row in rows:
                    stuck_tasks.append({
                        'analysis_id': row['analysis_id'],
                        'answer_id': row['answer_id'],
                        'user_id': row['user_id'],
                        'question_id': row['question_json_id'],
                        'stuck_minutes': float(row['stuck_minutes']),
                        'vectorization_status': row['vectorization_status'],
                        'dp_update_status': row['dp_update_status']
                    })

                return stuck_tasks

        except Exception as e:
            logger.error(f"Error detecting stuck tasks: {e}")
            return []

    async def check_services_health(self) -> Dict[str, Dict[str, Any]]:
        """Проверка здоровья всех сервисов"""
        health_status = {}

        # PostgreSQL health
        try:
            async with self.db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
                health_status['postgresql'] = {
                    'status': 'healthy',
                    'response_time_ms': 0
                }
        except Exception as e:
            health_status['postgresql'] = {
                'status': 'unhealthy',
                'error': str(e)
            }

        # Qdrant health
        try:
            start = time.time()
            response = await self.http_client.get(f"{self.qdrant_url}/collections")
            response_time = (time.time() - start) * 1000

            if response.status_code == 200:
                health_status['qdrant'] = {
                    'status': 'healthy',
                    'response_time_ms': response_time
                }
            else:
                health_status['qdrant'] = {
                    'status': 'degraded',
                    'response_time_ms': response_time,
                    'status_code': response.status_code
                }
        except Exception as e:
            health_status['qdrant'] = {
                'status': 'unhealthy',
                'error': str(e)
            }

        # OpenAI API health (minimal test)
        try:
            start = time.time()
            response = await self.http_client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {self.openai_api_key}"}
            )
            response_time = (time.time() - start) * 1000

            if response.status_code == 200:
                health_status['openai'] = {
                    'status': 'healthy',
                    'response_time_ms': response_time
                }
            else:
                health_status['openai'] = {
                    'status': 'degraded',
                    'response_time_ms': response_time,
                    'status_code': response.status_code
                }
        except Exception as e:
            health_status['openai'] = {
                'status': 'unhealthy',
                'error': str(e)
            }

        return health_status

    async def _trigger_alert(self, alert: PipelineAlert):
        """Триггерить алерт"""
        # Добавляем в историю
        self.alerts.append(alert)

        # Логируем
        log_level = {
            'warning': logger.warning,
            'error': logger.error,
            'critical': logger.critical
        }.get(alert.severity, logger.info)

        log_level(f"[{alert.alert_type.upper()}] {alert.message}: {alert.details}")

        # Вызываем callbacks
        for callback in self.alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")

    def register_alert_callback(self, callback: Callable):
        """Регистрация callback для алертов"""
        self.alert_callbacks.append(callback)

    async def get_pipeline_status(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Получить статус pipeline"""
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT
                        os.user_id,
                        COUNT(ua.id) as total_answers,
                        COUNT(aa.id) as analyzed_answers,
                        COUNT(*) FILTER (WHERE aa.vectorization_status = 'success') as vectorized,
                        COUNT(*) FILTER (WHERE aa.dp_update_status = 'success') as dp_updated,
                        COUNT(*) FILTER (WHERE aa.background_task_completed) as completed_tasks,
                        AVG(aa.background_task_duration_ms) as avg_processing_time
                    FROM selfology.onboarding_sessions os
                    JOIN selfology.user_answers_new ua ON ua.session_id = os.id
                    LEFT JOIN selfology.answer_analysis aa ON aa.user_answer_id = ua.id
                    WHERE os.status = 'active'
                """

                if user_id:
                    query += f" AND os.user_id = {user_id}"

                query += " GROUP BY os.user_id"

                rows = await conn.fetch(query)

                pipeline_status = []
                for row in rows:
                    pipeline_status.append({
                        'user_id': row['user_id'],
                        'total_answers': row['total_answers'],
                        'analyzed': row['analyzed_answers'],
                        'vectorized': row['vectorized'],
                        'dp_updated': row['dp_updated'],
                        'completed_tasks': row['completed_tasks'],
                        'avg_processing_time_ms': float(row['avg_processing_time'] or 0)
                    })

                return {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'users': pipeline_status,
                    'current_metrics': self.current_metrics.to_dict()
                }

        except Exception as e:
            logger.error(f"Error getting pipeline status: {e}")
            return {}

    async def get_recent_errors(self, hours: int = 1, limit: int = 50) -> List[Dict[str, Any]]:
        """Получить недавние ошибки"""
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT
                        aa.id as analysis_id,
                        aa.user_answer_id as answer_id,
                        os.user_id,
                        ua.question_json_id,
                        aa.processed_at,
                        aa.vectorization_status,
                        aa.vectorization_error,
                        aa.dp_update_status,
                        aa.dp_update_error,
                        aa.retry_count
                    FROM selfology.answer_analysis aa
                    JOIN selfology.user_answers_new ua ON ua.id = aa.user_answer_id
                    JOIN selfology.onboarding_sessions os ON os.id = ua.session_id
                    WHERE
                        aa.processed_at > NOW() - INTERVAL '$1 hours'
                        AND (aa.vectorization_status = 'failed' OR aa.dp_update_status = 'failed')
                    ORDER BY aa.processed_at DESC
                    LIMIT $2
                """

                rows = await conn.fetch(query.replace('$1', str(hours)).replace('$2', str(limit)))

                errors = []
                for row in rows:
                    error_info = {
                        'analysis_id': row['analysis_id'],
                        'answer_id': row['answer_id'],
                        'user_id': row['user_id'],
                        'question_id': row['question_json_id'],
                        'timestamp': row['processed_at'].isoformat(),
                        'retry_count': row['retry_count']
                    }

                    if row['vectorization_status'] == 'failed':
                        error_info['vectorization_error'] = row['vectorization_error']

                    if row['dp_update_status'] == 'failed':
                        error_info['dp_update_error'] = row['dp_update_error']

                    errors.append(error_info)

                return errors

        except Exception as e:
            logger.error(f"Error getting recent errors: {e}")
            return []

    async def get_metrics_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Получить сводку метрик за период"""
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

            recent_metrics = [
                m for m in self.metrics_history
                if m['timestamp'] > cutoff
            ]

            if not recent_metrics:
                return {'message': 'No metrics available for this period'}

            # Агрегируем метрики
            summary = {
                'period_hours': hours,
                'data_points': len(recent_metrics),
                'timing': {
                    'avg_ai_analysis_ms': 0,
                    'avg_total_pipeline_ms': 0,
                    'max_pipeline_ms': 0
                },
                'success_rates': {
                    'ai_analysis': 0,
                    'vectorization': 0,
                    'dp_update': 0
                },
                'totals': {
                    'retries': 0,
                    'errors': 0
                }
            }

            for metric_data in recent_metrics:
                m = metric_data['metrics']
                summary['timing']['avg_ai_analysis_ms'] += m.ai_analysis_time
                summary['timing']['avg_total_pipeline_ms'] += m.total_pipeline_time
                summary['timing']['max_pipeline_ms'] = max(
                    summary['timing']['max_pipeline_ms'],
                    m.total_pipeline_time
                )

                summary['success_rates']['ai_analysis'] += m.ai_success_rate
                summary['success_rates']['vectorization'] += m.vectorization_success_rate
                summary['success_rates']['dp_update'] += m.dp_update_success_rate

                summary['totals']['retries'] += m.total_retries
                summary['totals']['errors'] += (m.ai_errors + m.vectorization_errors + m.dp_update_errors)

            # Усредняем
            count = len(recent_metrics)
            summary['timing']['avg_ai_analysis_ms'] /= count
            summary['timing']['avg_total_pipeline_ms'] /= count
            summary['success_rates']['ai_analysis'] /= count
            summary['success_rates']['vectorization'] /= count
            summary['success_rates']['dp_update'] /= count

            return summary

        except Exception as e:
            logger.error(f"Error getting metrics summary: {e}")
            return {}


# Global monitor instance
_pipeline_monitor: Optional[OnboardingPipelineMonitor] = None


def initialize_onboarding_monitor(db_config: Dict[str, Any]) -> OnboardingPipelineMonitor:
    """Инициализация глобального монитора"""
    global _pipeline_monitor
    _pipeline_monitor = OnboardingPipelineMonitor(db_config)
    return _pipeline_monitor


def get_onboarding_monitor() -> Optional[OnboardingPipelineMonitor]:
    """Получить глобальный экземпляр монитора"""
    return _pipeline_monitor
