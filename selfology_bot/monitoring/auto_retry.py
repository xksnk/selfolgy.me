"""
Automatic Retry System for Failed Onboarding Operations

Автоматически перезапускает failed операции:
- Векторизация (vectorization_status = 'failed')
- Обновление DP (dp_update_status = 'failed')
- Зависшие pending статусы

Использует exponential backoff и ограничение на количество попыток.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
import asyncpg

logger = logging.getLogger(__name__)


class AutoRetryManager:
    """
    Менеджер автоматических повторных попыток

    Features:
    - Exponential backoff (1min → 5min → 15min → 30min)
    - Max retry limit (configurable, default 3)
    - Smart retry logic (только для исправимых ошибок)
    - Метрики успешности ретраев
    """

    def __init__(self, db_config: Dict[str, Any]):
        self.db_config = db_config
        self.db_pool: Optional[asyncpg.Pool] = None

        # Configuration
        self.max_retries = 3
        self.retry_delays = [60, 300, 900, 1800]  # 1min, 5min, 15min, 30min (seconds)

        # Statistics
        self.retry_stats = {
            'total_retries': 0,
            'successful_retries': 0,
            'failed_retries': 0
        }

        # Running state
        self.running = False
        self.retry_task: Optional[asyncio.Task] = None

    async def initialize(self):
        """Инициализация"""
        try:
            self.db_pool = await asyncpg.create_pool(
                **self.db_config,
                min_size=2,
                max_size=5,
                command_timeout=60
            )
            logger.info("AutoRetryManager initialized")
        except Exception as e:
            logger.error(f"Failed to initialize AutoRetryManager: {e}")
            raise

    async def start(self):
        """Запустить автоматические ретраи"""
        if self.running:
            logger.warning("AutoRetryManager already running")
            return

        self.running = True
        logger.info("Starting automatic retry system")

        self.retry_task = asyncio.create_task(self._retry_loop())

    async def stop(self):
        """Остановить ретраи"""
        self.running = False

        if self.retry_task:
            self.retry_task.cancel()
            try:
                await self.retry_task
            except asyncio.CancelledError:
                pass

        if self.db_pool:
            await self.db_pool.close()

        logger.info("AutoRetryManager stopped")

    async def _retry_loop(self):
        """Основной цикл ретраев"""
        while self.running:
            try:
                # Ретраим failed векторизации
                vec_retried = await self._retry_failed_vectorizations()

                # Ретраим failed DP updates
                dp_retried = await self._retry_failed_dp_updates()

                # Ретраим зависшие pending статусы
                stuck_retried = await self._retry_stuck_pending()

                if vec_retried > 0 or dp_retried > 0 or stuck_retried > 0:
                    logger.info(
                        f"Retry cycle completed: "
                        f"vectorization={vec_retried}, dp={dp_retried}, stuck={stuck_retried}"
                    )

                # Спим между циклами
                await asyncio.sleep(60)  # Проверяем каждую минуту

            except Exception as e:
                logger.error(f"Error in retry loop: {e}")
                await asyncio.sleep(120)

    async def _retry_failed_vectorizations(self) -> int:
        """
        Повторить failed векторизации

        Использует существующие колонки:
        - vectorization_status: 'failed'
        - last_retry_at: время последней попытки (если NULL - первая ошибка)
        - retry_count: количество попыток
        """
        try:
            # Находим failed векторизации которые можно ретраить
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT
                        aa.id as analysis_id,
                        aa.user_answer_id,
                        os.user_id,
                        aa.retry_count,
                        aa.vectorization_error,
                        aa.processed_at,
                        aa.last_retry_at,
                        EXTRACT(EPOCH FROM (
                            NOW() - COALESCE(aa.last_retry_at, aa.processed_at)
                        )) / 60 as minutes_since_failure
                    FROM selfology.answer_analysis aa
                    JOIN selfology.user_answers_new ua ON ua.id = aa.user_answer_id
                    JOIN selfology.onboarding_sessions os ON os.id = ua.session_id
                    WHERE
                        aa.vectorization_status = 'failed'
                        AND aa.retry_count < $1
                        AND (
                            aa.last_retry_at IS NULL
                            OR aa.last_retry_at < NOW() - INTERVAL '1 minute'
                        )
                    ORDER BY aa.processed_at ASC
                    LIMIT 10
                """

                rows = await conn.fetch(query, self.max_retries)

                retried_count = 0

                for row in rows:
                    retry_count = row['retry_count']

                    # Проверяем нужно ли ждать (exponential backoff)
                    if row['minutes_since_failure']:
                        required_delay = self.retry_delays[min(retry_count, len(self.retry_delays) - 1)] / 60
                        if row['minutes_since_failure'] < required_delay:
                            logger.debug(
                                f"Skipping analysis {row['analysis_id']}: "
                                f"need to wait {required_delay - row['minutes_since_failure']:.1f} more minutes"
                            )
                            continue

                    # Проверяем является ли ошибка recoverable
                    if not self._is_recoverable_error(row['vectorization_error']):
                        logger.info(f"Skipping non-recoverable vectorization error for analysis {row['analysis_id']}")
                        continue

                    # Пытаемся ретраить
                    success = await self._retry_vectorization(
                        row['analysis_id'],
                        row['user_id'],
                        row['user_answer_id']
                    )

                    if success:
                        retried_count += 1
                        self.retry_stats['successful_retries'] += 1
                    else:
                        self.retry_stats['failed_retries'] += 1

                    self.retry_stats['total_retries'] += 1

                return retried_count

        except Exception as e:
            logger.error(f"Error retrying vectorizations: {e}")
            return 0

    async def _retry_failed_dp_updates(self) -> int:
        """
        Повторить failed DP updates

        Использует существующие колонки:
        - dp_update_status: 'failed'
        - last_retry_at: время последней попытки (если NULL - первая ошибка)
        - retry_count: количество попыток
        """
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT
                        aa.id as analysis_id,
                        aa.user_answer_id,
                        os.user_id,
                        aa.retry_count,
                        aa.dp_update_error,
                        aa.processed_at,
                        aa.last_retry_at,
                        EXTRACT(EPOCH FROM (
                            NOW() - COALESCE(aa.last_retry_at, aa.processed_at)
                        )) / 60 as minutes_since_failure
                    FROM selfology.answer_analysis aa
                    JOIN selfology.user_answers_new ua ON ua.id = aa.user_answer_id
                    JOIN selfology.onboarding_sessions os ON os.id = ua.session_id
                    WHERE
                        aa.dp_update_status = 'failed'
                        AND aa.retry_count < $1
                        AND (
                            aa.last_retry_at IS NULL
                            OR aa.last_retry_at < NOW() - INTERVAL '1 minute'
                        )
                    ORDER BY aa.processed_at ASC
                    LIMIT 10
                """

                rows = await conn.fetch(query, self.max_retries)

                retried_count = 0

                for row in rows:
                    retry_count = row['retry_count']

                    # Exponential backoff
                    if row['minutes_since_failure']:
                        required_delay = self.retry_delays[min(retry_count, len(self.retry_delays) - 1)] / 60
                        if row['minutes_since_failure'] < required_delay:
                            logger.debug(
                                f"Skipping analysis {row['analysis_id']}: "
                                f"need to wait {required_delay - row['minutes_since_failure']:.1f} more minutes"
                            )
                            continue

                    # Проверяем recoverable
                    if not self._is_recoverable_error(row['dp_update_error']):
                        logger.info(f"Skipping non-recoverable DP error for analysis {row['analysis_id']}")
                        continue

                    # Ретраим
                    success = await self._retry_dp_update(
                        row['analysis_id'],
                        row['user_id'],
                        row['user_answer_id']
                    )

                    if success:
                        retried_count += 1
                        self.retry_stats['successful_retries'] += 1
                    else:
                        self.retry_stats['failed_retries'] += 1

                    self.retry_stats['total_retries'] += 1

                return retried_count

        except Exception as e:
            logger.error(f"Error retrying DP updates: {e}")
            return 0

    async def _retry_stuck_pending(self) -> int:
        """Повторить зависшие pending статусы"""
        try:
            async with self.db_pool.acquire() as conn:
                # Находим pending которые висят больше 10 минут
                query = """
                    SELECT
                        aa.id as analysis_id,
                        aa.user_answer_id,
                        os.user_id,
                        aa.retry_count,
                        aa.vectorization_status,
                        aa.dp_update_status,
                        EXTRACT(EPOCH FROM (NOW() - aa.processed_at)) / 60 as minutes_pending
                    FROM selfology.answer_analysis aa
                    JOIN selfology.user_answers_new ua ON ua.id = aa.user_answer_id
                    JOIN selfology.onboarding_sessions os ON os.id = ua.session_id
                    WHERE
                        (aa.vectorization_status = 'pending' OR aa.dp_update_status = 'pending')
                        AND aa.retry_count < $1
                        AND aa.processed_at < NOW() - INTERVAL '10 minutes'
                    ORDER BY aa.processed_at ASC
                    LIMIT 10
                """

                rows = await conn.fetch(query, self.max_retries)

                retried_count = 0

                for row in rows:
                    # Ретраим векторизацию если pending
                    if row['vectorization_status'] == 'pending':
                        success = await self._retry_vectorization(
                            row['analysis_id'],
                            row['user_id'],
                            row['user_answer_id']
                        )
                        if success:
                            retried_count += 1

                    # Ретраим DP если pending
                    if row['dp_update_status'] == 'pending':
                        success = await self._retry_dp_update(
                            row['analysis_id'],
                            row['user_id'],
                            row['user_answer_id']
                        )
                        if success:
                            retried_count += 1

                return retried_count

        except Exception as e:
            logger.error(f"Error retrying stuck pending: {e}")
            return 0

    async def _retry_vectorization(self, analysis_id: int, user_id: int, answer_id: int) -> bool:
        """
        Повторить векторизацию для конкретного анализа

        Returns:
            True если успешно, False если ошибка
        """
        try:
            logger.info(f"Retrying vectorization for analysis {analysis_id}")

            # Получаем данные анализа
            async with self.db_pool.acquire() as conn:
                analysis_data = await conn.fetchrow("""
                    SELECT raw_ai_response
                    FROM selfology.answer_analysis
                    WHERE id = $1
                """, analysis_id)

                if not analysis_data:
                    logger.error(f"Analysis {analysis_id} not found")
                    return False

                # Инкрементируем retry_count и обновляем last_retry_at
                await conn.execute("""
                    UPDATE selfology.answer_analysis
                    SET
                        retry_count = retry_count + 1,
                        last_retry_at = NOW(),
                        vectorization_status = 'pending'
                    WHERE id = $1
                """, analysis_id)

            # Импортируем EmbeddingCreator (избегаем circular import)
            import sys
            from pathlib import Path
            sys.path.append(str(Path(__file__).parent.parent))

            from analysis import EmbeddingCreator

            # Создаем embeddings
            embedding_creator = EmbeddingCreator()

            # Преобразуем данные анализа в нужный формат
            import json
            raw_response = analysis_data['raw_ai_response']
            if isinstance(raw_response, str):
                raw_response = json.loads(raw_response)

            analysis_result = {
                'raw_ai_response': raw_response,
                'user_id': user_id
            }

            # Создаем векторы
            success = await embedding_creator.create_personality_vector(
                user_id=user_id,
                analysis_result=analysis_result,
                is_update=True
            )

            # Обновляем статус
            async with self.db_pool.acquire() as conn:
                if success:
                    await conn.execute("""
                        UPDATE selfology.answer_analysis
                        SET
                            vectorization_status = 'success',
                            vectorization_completed_at = NOW(),
                            vectorization_error = NULL
                        WHERE id = $1
                    """, analysis_id)
                    logger.info(f"Successfully retried vectorization for analysis {analysis_id}")
                else:
                    await conn.execute("""
                        UPDATE selfology.answer_analysis
                        SET
                            vectorization_status = 'failed',
                            vectorization_error = 'Retry failed'
                        WHERE id = $1
                    """, analysis_id)

            return success

        except Exception as e:
            logger.error(f"Error retrying vectorization for analysis {analysis_id}: {e}")

            # Отмечаем как failed
            try:
                async with self.db_pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE selfology.answer_analysis
                        SET
                            vectorization_status = 'failed',
                            vectorization_error = $2
                        WHERE id = $1
                    """, analysis_id, str(e)[:500])
            except:
                pass

            return False

    async def _retry_dp_update(self, analysis_id: int, user_id: int, answer_id: int) -> bool:
        """
        Повторить обновление DP для конкретного анализа

        Returns:
            True если успешно, False если ошибка
        """
        try:
            logger.info(f"Retrying DP update for analysis {analysis_id}")

            # Получаем данные анализа и вопроса
            async with self.db_pool.acquire() as conn:
                data = await conn.fetchrow("""
                    SELECT
                        aa.raw_ai_response,
                        ua.raw_answer,
                        ua.question_json_id
                    FROM selfology.answer_analysis aa
                    JOIN selfology.user_answers_new ua ON ua.id = aa.user_answer_id
                    WHERE aa.id = $1
                """, analysis_id)

                if not data:
                    logger.error(f"Analysis {analysis_id} not found")
                    return False

                # Инкрементируем retry_count и обновляем last_retry_at
                await conn.execute("""
                    UPDATE selfology.answer_analysis
                    SET
                        retry_count = retry_count + 1,
                        last_retry_at = NOW(),
                        dp_update_status = 'pending'
                    WHERE id = $1
                """, analysis_id)

            # Импортируем PersonalityExtractor
            import sys
            from pathlib import Path
            sys.path.append(str(Path(__file__).parent.parent))

            from analysis import PersonalityExtractor
            from database import DigitalPersonalityDAO, DatabaseService
            import os

            # Инициализируем сервисы
            db_service = DatabaseService(
                host=os.getenv("DB_HOST", "localhost"),
                port=int(os.getenv("DB_PORT", 5432)),
                user=os.getenv("DB_USER", "n8n"),
                password=os.getenv("DB_PASSWORD"),
                database=os.getenv("DB_NAME", "n8n")
            )
            await db_service.initialize()

            personality_dao = DigitalPersonalityDAO(db_service)
            personality_extractor = PersonalityExtractor()

            # Загружаем метаданные вопроса
            sys.path.append(str(Path(__file__).parent.parent.parent / "intelligent_question_core"))
            from intelligent_question_core.api.core_api import SelfologyQuestionCore

            core_file = str(Path(__file__).parent.parent.parent / "intelligent_question_core" / "data" / "selfology_intelligent_core.json")
            question_core = SelfologyQuestionCore(core_file)
            question_data = question_core.get_question(data['question_json_id'])

            # Извлекаем личность
            existing_personality = await personality_dao.get_personality(user_id)

            extracted = await personality_extractor.extract_from_answer(
                question_text=question_data.get('text', ''),
                user_answer=data['raw_answer'],
                question_metadata=question_data.get('classification', {}),
                existing_personality=existing_personality
            )

            # Обновляем
            if existing_personality:
                merged = personality_extractor.merge_extractions(existing_personality, extracted)
                await personality_dao.update_personality(user_id, merged, merge=True)
            else:
                await personality_dao.create_personality(user_id, extracted)

            # Отмечаем успех
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    UPDATE selfology.answer_analysis
                    SET
                        dp_update_status = 'success',
                        dp_update_completed_at = NOW(),
                        dp_update_error = NULL
                    WHERE id = $1
                """, analysis_id)

            logger.info(f"Successfully retried DP update for analysis {analysis_id}")
            return True

        except Exception as e:
            logger.error(f"Error retrying DP update for analysis {analysis_id}: {e}")

            # Отмечаем как failed
            try:
                async with self.db_pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE selfology.answer_analysis
                        SET
                            dp_update_status = 'failed',
                            dp_update_error = $2
                        WHERE id = $1
                    """, analysis_id, str(e)[:500])
            except:
                pass

            return False

    def _is_recoverable_error(self, error_message: Optional[str]) -> bool:
        """
        Определить является ли ошибка recoverable

        Non-recoverable ошибки:
        - Invalid data format
        - Missing required fields
        - Authorization errors

        Recoverable ошибки:
        - Network timeouts
        - Service unavailable
        - Rate limiting
        """
        if not error_message:
            return True

        error_lower = error_message.lower()

        # Non-recoverable patterns
        non_recoverable = [
            'invalid json',
            'missing required field',
            'unauthorized',
            'invalid api key',
            'malformed',
            'invalid format'
        ]

        for pattern in non_recoverable:
            if pattern in error_lower:
                return False

        # Recoverable patterns
        recoverable = [
            'timeout',
            'connection',
            'unavailable',
            'rate limit',
            'too many requests',
            'service temporarily',
            'network error'
        ]

        for pattern in recoverable:
            if pattern in error_lower:
                return True

        # По умолчанию считаем recoverable
        return True

    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику ретраев"""
        total = self.retry_stats['total_retries']
        successful = self.retry_stats['successful_retries']

        return {
            'total_retries': total,
            'successful_retries': successful,
            'failed_retries': self.retry_stats['failed_retries'],
            'success_rate': (successful / total * 100) if total > 0 else 0.0
        }


# Global instance
_auto_retry_manager: Optional[AutoRetryManager] = None


def initialize_auto_retry(db_config: Dict[str, Any]) -> AutoRetryManager:
    """Инициализация глобального retry manager"""
    global _auto_retry_manager
    _auto_retry_manager = AutoRetryManager(db_config)
    return _auto_retry_manager


def get_auto_retry_manager() -> Optional[AutoRetryManager]:
    """Получить глобальный экземпляр retry manager"""
    return _auto_retry_manager
