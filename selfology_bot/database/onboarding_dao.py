"""
New OnboardingDAO - Чистая гибридная архитектура

Принципы:
- Минимум в БД + полные данные в JSON
- Одна активная сессия на пользователя
- questions_metadata заполняется автоматически при ответах
- НЕТ лишних таблиц и сложной логики
"""

import logging
import json
import asyncpg
from datetime import datetime
from typing import Dict, List, Optional, Any

from .service import DatabaseService

logger = logging.getLogger(__name__)

class OnboardingDAO:
    """DAO для новой системы онбординга"""

    def __init__(self, db_service: DatabaseService):
        self.db = db_service

    async def create_onboarding_tables(self):
        """Создать чистые таблицы онбординга"""

        # 1. questions_metadata - минимальные метаданные из JSON
        questions_metadata_sql = """
        CREATE TABLE IF NOT EXISTS questions_metadata (
            id SERIAL PRIMARY KEY,
            json_id VARCHAR(50) UNIQUE NOT NULL,
            domain VARCHAR(20) NOT NULL,
            depth_level VARCHAR(15) NOT NULL,
            energy VARCHAR(15) NOT NULL,

            -- Флаги "на доработку" (только для админа)
            is_flagged BOOLEAN DEFAULT false,
            flagged_by_admin VARCHAR(20),
            flag_reason TEXT,
            flagged_at TIMESTAMP,

            created_at TIMESTAMP DEFAULT NOW()
        )
        """

        # 2. onboarding_sessions - простые сессии
        sessions_sql = """
        CREATE TABLE IF NOT EXISTS onboarding_sessions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,

            started_at TIMESTAMP DEFAULT NOW(),
            completed_at TIMESTAMP,
            status VARCHAR(20) DEFAULT 'active',

            questions_asked INTEGER DEFAULT 0,
            questions_answered INTEGER DEFAULT 0,
            current_question_json_id VARCHAR(10),

            -- Smart Mix состояние
            last_strategy VARCHAR(20),
            domains_covered TEXT[],
            heavy_count INTEGER DEFAULT 0,

            session_data JSONB DEFAULT '{}'
        )
        """

        # 3. Адаптируем существующую user_answers для новой архитектуры
        user_answers_sql = """
        CREATE TABLE IF NOT EXISTS user_answers_new (
            id SERIAL PRIMARY KEY,
            session_id INTEGER REFERENCES onboarding_sessions(id) ON DELETE CASCADE,
            question_json_id VARCHAR(10) NOT NULL,

            raw_answer TEXT NOT NULL,
            answer_length INTEGER,
            answered_at TIMESTAMP DEFAULT NOW(),

            -- Для Phase 2 (анализ)
            analysis_status VARCHAR(20) DEFAULT 'pending'
        )
        """

        # 4. Таблица анализа ответов (Phase 2)
        answer_analysis_sql = """
        CREATE TABLE IF NOT EXISTS answer_analysis (
            id SERIAL PRIMARY KEY,
            user_answer_id INTEGER REFERENCES user_answers_new(id) ON DELETE CASCADE,

            -- Версионирование анализа
            analysis_version VARCHAR(10) NOT NULL DEFAULT '2.0',

            -- Результаты анализа
            psychological_insights TEXT,
            trait_scores JSONB NOT NULL DEFAULT '{}'
                CONSTRAINT valid_trait_structure CHECK (
                    trait_scores ? 'version' AND
                    trait_scores ? 'big_five' AND
                    trait_scores ? 'timestamp'
                ),
            emotional_state VARCHAR(30),
            fatigue_level FLOAT,

            -- Рекомендации для роутера
            next_question_hints JSONB DEFAULT '{}',

            -- Метаданные обработки
            ai_model_used VARCHAR(30),
            processing_time_ms INTEGER,
            processed_at TIMESTAMP DEFAULT NOW(),

            -- Для отладки и улучшения (сжатое хранение)
            raw_ai_response JSONB,
            debug_priority SMALLINT DEFAULT 0,
            can_be_compressed BOOLEAN DEFAULT TRUE,

            -- Качество анализа
            quality_score FLOAT DEFAULT 0.0,
            confidence_score FLOAT DEFAULT 0.0,

            -- Специальные ситуации
            special_situation VARCHAR(20),  -- crisis, breakthrough, resistance
            is_milestone BOOLEAN DEFAULT false
        )
        """

        # Создаем индексы для всех таблиц
        indexes_sql = [
            # questions_metadata индексы
            "CREATE INDEX IF NOT EXISTS idx_qmeta_domain ON questions_metadata(domain)",
            "CREATE INDEX IF NOT EXISTS idx_qmeta_flagged ON questions_metadata(is_flagged) WHERE is_flagged = false",

            # onboarding_sessions индексы
            "CREATE INDEX IF NOT EXISTS idx_sessions_user ON onboarding_sessions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_sessions_active ON onboarding_sessions(user_id, status) WHERE status = 'active'",

            # user_answers_new индексы
            "CREATE INDEX IF NOT EXISTS idx_answers_session ON user_answers_new(session_id)",
            "CREATE INDEX IF NOT EXISTS idx_answers_question ON user_answers_new(question_json_id)",
            "CREATE INDEX IF NOT EXISTS idx_answers_status ON user_answers_new(analysis_status)",

            # answer_analysis индексы (Phase 2)
            "CREATE INDEX IF NOT EXISTS idx_analysis_answer ON answer_analysis(user_answer_id)",
            "CREATE INDEX IF NOT EXISTS idx_analysis_version ON answer_analysis(analysis_version)",
            "CREATE INDEX IF NOT EXISTS idx_analysis_model ON answer_analysis(ai_model_used)",
            "CREATE INDEX IF NOT EXISTS idx_analysis_quality ON answer_analysis(quality_score)",
            "CREATE INDEX IF NOT EXISTS idx_analysis_milestone ON answer_analysis(is_milestone) WHERE is_milestone = true",
            "CREATE INDEX IF NOT EXISTS idx_analysis_situation ON answer_analysis(special_situation)"
        ]

        try:
            async with self.db.get_connection() as conn:
                # Создаем таблицы
                await conn.execute(questions_metadata_sql)
                await conn.execute(sessions_sql)
                await conn.execute(user_answers_sql)
                await conn.execute(answer_analysis_sql)  # 🆕 Phase 2 table

                # Создаем индексы
                for index_sql in indexes_sql:
                    await conn.execute(index_sql)

                logger.info("✅ New onboarding tables created")

        except Exception as e:
            logger.error(f"❌ Error creating onboarding tables: {e}")
            raise

    async def get_active_session(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получить активную сессию пользователя с глобальной статистикой

        Returns:
            Session data + total_answers_lifetime из user_stats
        """

        try:
            async with self.db.get_connection() as conn:
                row = await conn.fetchrow("""
                    SELECT
                        os.id, os.user_id, os.started_at, os.status,
                        os.questions_asked, os.questions_answered,
                        os.current_question_json_id,
                        os.last_strategy, os.domains_covered,
                        os.heavy_count, os.session_data,
                        COALESCE(us.total_answers_lifetime, 0) as total_answers_lifetime
                    FROM onboarding_sessions os
                    LEFT JOIN user_stats us ON us.user_id = os.user_id
                    WHERE os.user_id = $1 AND os.status = 'active'
                    ORDER BY os.started_at DESC
                    LIMIT 1
                """, user_id)

                if row:
                    return dict(row)
                return None

        except Exception as e:
            logger.error(f"❌ Error getting active session for user {user_id}: {e}")
            return None

    async def get_session_by_id(self, session_id: int) -> Optional[Dict[str, Any]]:
        """
        Получить сессию по ID

        Returns:
            Session data
        """

        try:
            async with self.db.get_connection() as conn:
                row = await conn.fetchrow("""
                    SELECT
                        id, user_id, started_at, status,
                        questions_asked, questions_answered,
                        current_question_json_id,
                        last_strategy, domains_covered,
                        heavy_count, session_data
                    FROM onboarding_sessions
                    WHERE id = $1
                """, session_id)

                if row:
                    return dict(row)
                return None

        except Exception as e:
            logger.error(f"❌ Error getting session {session_id}: {e}")
            return None

    async def start_session(self, user_id: int) -> int:
        """Начать новую сессию (закрывает предыдущие активные)"""

        try:
            async with self.db.get_connection() as conn:
                # Закрываем любые активные сессии пользователя
                await conn.execute("""
                    UPDATE onboarding_sessions
                    SET status = 'abandoned', completed_at = NOW()
                    WHERE user_id = $1 AND status = 'active'
                """, user_id)

                # Создаем новую сессию
                session_id = await conn.fetchval("""
                    INSERT INTO onboarding_sessions (user_id, status)
                    VALUES ($1, 'active')
                    RETURNING id
                """, user_id)

                logger.info(f"🚀 Started new session {session_id} for user {user_id}")
                return session_id

        except Exception as e:
            logger.error(f"❌ Error starting session for user {user_id}: {e}")
            raise

    async def save_user_answer(self, session_id: int, question_json_id: str, answer: str) -> int:
        """
        Сохранить ответ пользователя

        NOTE: total_answers_lifetime обновляется автоматически через триггер update_lifetime_answers_trigger
        """

        try:
            async with self.db.get_connection() as conn:
                answer_id = await conn.fetchval("""
                    INSERT INTO user_answers_new (session_id, question_json_id, raw_answer, answer_length)
                    VALUES ($1, $2, $3, $4)
                    RETURNING id
                """, session_id, question_json_id, answer, len(answer))

                # Обновляем счетчик ответов ТОЛЬКО для текущей сессии
                # Глобальный счетчик total_answers_lifetime обновляется триггером автоматически
                await conn.execute("""
                    UPDATE onboarding_sessions
                    SET questions_answered = questions_answered + 1
                    WHERE id = $1
                """, session_id)

                logger.info(f"💬 Saved answer {answer_id} for session {session_id}")
                return answer_id

        except Exception as e:
            logger.error(f"❌ Error saving answer for session {session_id}: {e}")
            raise

    async def increment_questions_asked(self, session_id: int):
        """Инкремент счетчика заданных вопросов после отправки вопроса пользователю"""

        try:
            async with self.db.get_connection() as conn:
                await conn.execute("""
                    UPDATE onboarding_sessions
                    SET questions_asked = questions_asked + 1
                    WHERE id = $1
                """, session_id)

                logger.debug(f"✅ Incremented questions_asked for session {session_id}")

        except Exception as e:
            logger.error(f"❌ Error incrementing questions_asked for session {session_id}: {e}")
            raise

    async def update_current_question(self, session_id: int, question_json_id: str):
        """Обновить текущий вопрос в сессии"""

        try:
            async with self.db.get_connection() as conn:
                await conn.execute("""
                    UPDATE onboarding_sessions
                    SET current_question_json_id = $2
                    WHERE id = $1
                """, session_id, question_json_id)

                logger.debug(f"✅ Updated current question to {question_json_id} for session {session_id}")

        except Exception as e:
            logger.error(f"❌ Error updating current question for session {session_id}: {e}")
            raise

    async def complete_session(self, session_id: int):
        """
        Завершить сессию онбординга

        Args:
            session_id: ID сессии для завершения
        """
        try:
            async with self.db.get_connection() as conn:
                await conn.execute("""
                    UPDATE onboarding_sessions
                    SET status = 'completed', completed_at = NOW()
                    WHERE id = $1
                """, session_id)

                logger.info(f"✅ Session {session_id} completed")

        except Exception as e:
            logger.error(f"❌ Error completing session {session_id}: {e}")
            raise

    async def auto_approve_question(self, json_id: str, domain: str, depth: str, energy: str):
        """Автоматически одобрить вопрос при ответе пользователя"""

        try:
            async with self.db.get_connection() as conn:
                await conn.execute("""
                    INSERT INTO questions_metadata (json_id, domain, depth_level, energy, is_flagged)
                    VALUES ($1, $2, $3, $4, false)
                    ON CONFLICT (json_id) DO NOTHING
                """, json_id, domain, depth, energy)

                logger.info(f"✅ Question {json_id} auto-approved")

        except Exception as e:
            logger.error(f"❌ Error auto-approving question {json_id}: {e}")

    async def flag_question_for_admin(self, json_id: str, admin_id: str, reason: str):
        """Пометить вопрос на доработку (только админ)"""

        try:
            async with self.db.get_connection() as conn:
                await conn.execute("""
                    INSERT INTO questions_metadata (json_id, domain, depth_level, energy, is_flagged, flagged_by_admin, flag_reason, flagged_at)
                    SELECT $1, 'UNKNOWN', 'UNKNOWN', 'UNKNOWN', true, $2, $3, NOW()
                    WHERE NOT EXISTS (SELECT 1 FROM questions_metadata WHERE json_id = $1)

                    UNION ALL

                    UPDATE questions_metadata
                    SET is_flagged = true, flagged_by_admin = $2, flag_reason = $3, flagged_at = NOW()
                    WHERE json_id = $1
                """, json_id, admin_id, reason)

                logger.info(f"🚧 Question {json_id} flagged by admin {admin_id}")

        except Exception as e:
            logger.error(f"❌ Error flagging question {json_id}: {e}")
            raise

    async def get_unflagged_questions(self, domain: str = None) -> List[str]:
        """Получить одобренные json_id для роутера"""

        try:
            async with self.db.get_connection() as conn:
                if domain:
                    json_ids = await conn.fetch("""
                        SELECT json_id FROM questions_metadata
                        WHERE is_flagged = false AND domain = $1
                    """, domain)
                else:
                    json_ids = await conn.fetch("""
                        SELECT json_id FROM questions_metadata
                        WHERE is_flagged = false
                    """)

                return [row['json_id'] for row in json_ids]

        except Exception as e:
            logger.error(f"❌ Error getting unflagged questions: {e}")
            return []  # Fallback - пустой список

    async def get_flagged_question_ids(self) -> set:
        """
        Получить set ID вопросов, помеченных флагом (для фильтрации)

        Returns:
            Set JSON IDs помеченных вопросов
        """
        try:
            async with self.db.get_connection() as conn:
                rows = await conn.fetch("""
                    SELECT json_id FROM questions_metadata
                    WHERE is_flagged = true
                """)

                flagged_ids = {row['json_id'] for row in rows}
                logger.debug(f"🚩 Found {len(flagged_ids)} flagged questions")
                return flagged_ids

        except Exception as e:
            logger.error(f"❌ Error getting flagged questions: {e}")
            return set()  # Fallback - пустой set

    async def flag_question(self, question_id: str, reason: str, admin_id: int) -> bool:
        """
        Пометить вопрос на доработку (сохранить в БД)

        Args:
            question_id: JSON ID вопроса (например, q_172)
            reason: Причина пометки
            admin_id: Telegram ID администратора

        Returns:
            True если успешно, False при ошибке
        """
        try:
            async with self.db.get_connection() as conn:
                await conn.execute("""
                    INSERT INTO questions_metadata
                        (json_id, is_flagged, flag_reason, flagged_at, flagged_by_admin)
                    VALUES ($1, true, $2, NOW(), $3)
                    ON CONFLICT (json_id)
                    DO UPDATE SET
                        is_flagged = true,
                        flag_reason = $2,
                        flagged_at = NOW(),
                        flagged_by_admin = $3
                """, question_id, reason, str(admin_id))

                logger.info(f"✅ Flagged question {question_id} in database")
                return True

        except Exception as e:
            logger.error(f"❌ Error flagging question {question_id}: {e}")
            return False

    async def unflag_question(self, question_id: str) -> bool:
        """
        Снять флаг с вопроса

        Args:
            question_id: JSON ID вопроса

        Returns:
            True если успешно
        """
        try:
            async with self.db.get_connection() as conn:
                await conn.execute("""
                    UPDATE questions_metadata
                    SET is_flagged = false,
                        flag_reason = NULL,
                        flagged_at = NULL,
                        flagged_by_admin = NULL
                    WHERE json_id = $1
                """, question_id)

                logger.info(f"✅ Unflagged question {question_id}")
                return True

        except Exception as e:
            logger.error(f"❌ Error unflagging question {question_id}: {e}")
            return False

    async def get_session_analysis_insights(self, session_id: int) -> List[Dict[str, Any]]:
        """
        Получить AI анализ всех ответов в сессии для умного роутинга

        Args:
            session_id: ID сессии

        Returns:
            Список с insights из анализа
        """
        try:
            async with self.db.get_connection() as conn:
                rows = await conn.fetch("""
                    SELECT
                        ua.question_json_id,
                        ua.raw_answer,
                        aa.emotional_state,
                        aa.quality_score,
                        aa.confidence_score,
                        aa.special_situation,
                        aa.next_question_hints,
                        qm.domain
                    FROM user_answers_new ua
                    LEFT JOIN answer_analysis aa ON aa.user_answer_id = ua.id
                    LEFT JOIN questions_metadata qm ON qm.json_id = ua.question_json_id
                    WHERE ua.session_id = $1
                    ORDER BY ua.answered_at ASC
                """, session_id)

                insights = []
                for row in rows:
                    insights.append({
                        'question_id': row['question_json_id'],
                        'answer': row['raw_answer'],
                        'emotional_state': row['emotional_state'],
                        'quality_score': row['quality_score'] or 0.0,
                        'confidence_score': row['confidence_score'] or 0.0,
                        'special_situation': row['special_situation'],
                        'next_question_hints': row['next_question_hints'] or {},
                        'domain': row['domain']
                    })

                logger.debug(f"📊 Retrieved {len(insights)} analysis insights for session {session_id}")
                return insights

        except Exception as e:
            logger.error(f"❌ Error getting session analysis insights for session {session_id}: {e}")
            return []

    async def save_analysis_result(
        self,
        user_answer_id: int,
        analysis_result: Dict[str, Any]
    ) -> int:
        """
        Сохранить результат анализа ответа в БД

        Args:
            user_answer_id: ID ответа пользователя
            analysis_result: Полный результат анализа из AnswerAnalyzer

        Returns:
            ID созданной записи анализа
        """

        try:
            # Извлекаем данные из результата анализа
            processing_meta = analysis_result.get("processing_metadata", {})
            quality_meta = analysis_result.get("quality_metadata", {})
            psychological = analysis_result.get("psychological_analysis", {})
            traits = analysis_result.get("personality_traits", {})
            router_rec = analysis_result.get("router_recommendations", {})

            async with self.db.get_connection() as conn:
                analysis_id = await conn.fetchval("""
                    INSERT INTO answer_analysis (
                        user_answer_id, analysis_version, psychological_insights,
                        trait_scores, emotional_state, fatigue_level,
                        next_question_hints, ai_model_used, processing_time_ms,
                        raw_ai_response, debug_priority, quality_score,
                        confidence_score, special_situation, is_milestone
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                    RETURNING id
                """,
                    user_answer_id,
                    analysis_result.get("analysis_version", "2.0"),
                    json.dumps(psychological.get("insights", {}), ensure_ascii=False),
                    json.dumps(traits, ensure_ascii=False),
                    psychological.get("emotional_assessment", {}).get("primary", "neutral"),
                    quality_meta.get("fatigue_indicators", 0.0),
                    json.dumps(router_rec, ensure_ascii=False),
                    processing_meta.get("model_used", "unknown"),
                    processing_meta.get("processing_time_ms", 0),
                    json.dumps(analysis_result, ensure_ascii=False),  # 🔥 FIX: Сохраняем ВЕСЬ результат, не только debug_info!
                    1 if processing_meta.get("special_situation") else 0,
                    quality_meta.get("overall_reliability", 0.0),
                    quality_meta.get("data_completeness", 0.0),
                    processing_meta.get("special_situation"),
                    processing_meta.get("special_situation") == "breakthrough"
                )

                # Обновляем статус ответа
                await conn.execute("""
                    UPDATE user_answers_new
                    SET analysis_status = 'analyzed'
                    WHERE id = $1
                """, user_answer_id)

                logger.info(f"💾 Analysis saved with ID {analysis_id} for answer {user_answer_id}")
                return analysis_id

        except Exception as e:
            logger.error(f"❌ Error saving analysis for answer {user_answer_id}: {e}")
            raise

    async def get_user_total_answers(self, user_id: int) -> int:
        """
        Получить общее количество ответов пользователя за всё время

        Returns:
            Общее количество ответов (из таблицы user_stats)
        """

        try:
            async with self.db.get_connection() as conn:
                total = await conn.fetchval("""
                    SELECT COALESCE(total_answers_lifetime, 0)
                    FROM user_stats
                    WHERE user_id = $1
                """, user_id)

                return total if total is not None else 0

        except Exception as e:
            logger.error(f"❌ Error getting total answers for user {user_id}: {e}")
            return 0

    async def get_user_answered_questions(self, user_id: int) -> List[str]:
        """
        Получить список всех вопросов на которые пользователь уже ответил (из всех сессий)

        ВКЛЮЧАЕТ:
        - Обычные вопросы из user_answers_new
        - Системный вопрос system_context_story из context_stories

        Returns:
            Список question_json_id
        """
        try:
            async with self.db.get_connection() as conn:
                rows = await conn.fetch("""
                    SELECT DISTINCT ua.question_json_id
                    FROM selfology.user_answers_new ua
                    JOIN selfology.onboarding_sessions s ON ua.session_id = s.id
                    WHERE s.user_id = $1

                    UNION

                    SELECT 'system_context_story' as question_json_id
                    FROM selfology.user_context_stories cs
                    WHERE cs.user_id = $1
                      AND cs.story_type = 'onboarding_context'

                    ORDER BY question_json_id
                """, user_id)

                result = [row['question_json_id'] for row in rows]
                logger.info(f"✅ DEBUG: get_user_answered_questions returned {len(result)} questions, includes system_context_story: {'system_context_story' in result}")
                return result

        except Exception as e:
            logger.error(f"❌ Error getting answered questions for user {user_id}: {e}")
            return []

    async def get_user_stats(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получить полную статистику пользователя

        Returns:
            {
                'user_id': int,
                'total_answers_lifetime': int,
                'first_answer_at': datetime,
                'updated_at': datetime
            }
        """

        try:
            async with self.db.get_connection() as conn:
                row = await conn.fetchrow("""
                    SELECT user_id, total_answers_lifetime, first_answer_at, updated_at
                    FROM user_stats
                    WHERE user_id = $1
                """, user_id)

                if row:
                    return dict(row)
                return None

        except Exception as e:
            logger.error(f"❌ Error getting user stats for user {user_id}: {e}")
            return None

    async def update_vectorization_status(
        self,
        analysis_id: int,
        status: str,
        error: Optional[str] = None
    ) -> None:
        """
        Обновить статус векторизации для analysis

        Args:
            analysis_id: ID записи анализа
            status: Статус (success, failed, skipped)
            error: Текст ошибки (если есть)
        """

        try:
            async with self.db.get_connection() as conn:
                await conn.execute("""
                    UPDATE answer_analysis
                    SET vectorization_status = $2,
                        vectorization_error = $3,
                        vectorization_completed_at = NOW()
                    WHERE id = $1
                """, analysis_id, status, error)

                logger.debug(f"✅ Updated vectorization status to '{status}' for analysis {analysis_id}")

        except Exception as e:
            logger.error(f"❌ Error updating vectorization status for analysis {analysis_id}: {e}")
            raise

    async def update_dp_update_status(
        self,
        analysis_id: int,
        status: str,
        error: Optional[str] = None
    ) -> None:
        """
        Обновить статус обновления Digital Personality для analysis

        Args:
            analysis_id: ID записи анализа
            status: Статус (success, failed, skipped)
            error: Текст ошибки (если есть)
        """

        try:
            async with self.db.get_connection() as conn:
                await conn.execute("""
                    UPDATE answer_analysis
                    SET dp_update_status = $2,
                        dp_update_error = $3,
                        dp_update_completed_at = NOW()
                    WHERE id = $1
                """, analysis_id, status, error)

                logger.debug(f"✅ Updated DP status to '{status}' for analysis {analysis_id}")

        except Exception as e:
            logger.error(f"❌ Error updating DP status for analysis {analysis_id}: {e}")
            raise

    async def mark_background_task_completed(
        self,
        analysis_id: int,
        duration_ms: int,
        success: bool = True
    ) -> None:
        """
        Пометить завершение background task для analysis

        Args:
            analysis_id: ID записи анализа
            duration_ms: Длительность выполнения в миллисекундах
            success: True если task завершился успешно
        """

        try:
            async with self.db.get_connection() as conn:
                await conn.execute("""
                    UPDATE answer_analysis
                    SET background_task_completed = $2,
                        background_task_duration_ms = $3
                    WHERE id = $1
                """, analysis_id, success, duration_ms)

                logger.debug(f"✅ Marked background task completed for analysis {analysis_id} ({duration_ms}ms)")

        except Exception as e:
            logger.error(f"❌ Error marking background task completed for analysis {analysis_id}: {e}")
            raise

    async def increment_retry_count(
        self,
        analysis_id: int
    ) -> None:
        """
        Инкремент счетчика повторных попыток для analysis

        Args:
            analysis_id: ID записи анализа
        """

        try:
            async with self.db.get_connection() as conn:
                await conn.execute("""
                    UPDATE answer_analysis
                    SET retry_count = retry_count + 1,
                        last_retry_at = NOW()
                    WHERE id = $1
                """, analysis_id)

                logger.debug(f"✅ Incremented retry count for analysis {analysis_id}")

        except Exception as e:
            logger.error(f"❌ Error incrementing retry count for analysis {analysis_id}: {e}")

    async def get_session_answers(self, session_id: int) -> List[Dict[str, Any]]:
        """
        Получить все ответы пользователя в сессии (для восстановления истории)

        Args:
            session_id: ID сессии

        Returns:
            Список ответов с метаданными вопросов
        """
        try:
            async with self.db.get_connection() as conn:
                rows = await conn.fetch("""
                    SELECT
                        ua.id,
                        ua.question_json_id,
                        ua.raw_answer,
                        ua.answered_at,
                        qm.domain,
                        qm.depth_level,
                        qm.energy
                    FROM user_answers_new ua
                    LEFT JOIN questions_metadata qm ON qm.json_id = ua.question_json_id
                    WHERE ua.session_id = $1
                    ORDER BY ua.answered_at ASC
                """, session_id)

                answers = []
                for row in rows:
                    answers.append({
                        'answer_id': row['id'],
                        'question_id': row['question_json_id'],
                        'answer': row['raw_answer'],
                        'answered_at': row['answered_at'].isoformat() if row['answered_at'] else None,
                        'domain': row['domain'],
                        'depth_level': row['depth_level'],
                        'energy': row['energy']
                    })

                logger.debug(f"📚 Retrieved {len(answers)} answers for session {session_id}")
                return answers

        except Exception as e:
            logger.error(f"❌ Error getting session answers for session {session_id}: {e}")
            return []

    # ============================================================================
    # CONTEXT STORIES API - для работы с произвольными рассказами пользователя
    # ============================================================================

    async def save_context_story(
        self,
        user_id: int,
        session_id: Optional[int],
        story_text: str,
        story_type: str = 'onboarding_intro',
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Сохранить контекстную историю пользователя

        Args:
            user_id: ID пользователя
            session_id: ID сессии онбординга (может быть None для внесессионных историй)
            story_text: Текст истории
            story_type: Тип истории (onboarding_intro, crisis_context, goal_setting, etc.)
            metadata: Дополнительные метаданные (tags, sentiment, etc.)

        Returns:
            ID созданной записи истории
        """
        try:
            async with self.db.get_connection() as conn:
                story_id = await conn.fetchval("""
                    INSERT INTO user_context_stories (
                        user_id, session_id, story_text,
                        story_type, metadata
                    ) VALUES ($1, $2, $3, $4, $5)
                    RETURNING id
                """,
                    user_id,
                    session_id,
                    story_text,
                    story_type,
                    json.dumps(metadata or {}, ensure_ascii=False)
                )

                logger.info(f"📖 Saved context story {story_id} for user {user_id} (type: {story_type})")
                return story_id

        except Exception as e:
            logger.error(f"❌ Error saving context story for user {user_id}: {e}")
            raise

    async def save_context_story_analysis(
        self,
        context_story_id: int,
        analysis_result: Dict[str, Any]
    ) -> int:
        """
        Сохранить AI анализ контекстной истории

        Переиспользует всю инфраструктуру answer_analysis, но вместо user_answer_id
        использует context_story_id

        Args:
            context_story_id: ID контекстной истории
            analysis_result: Результат анализа из AnswerAnalyzer

        Returns:
            ID созданной записи анализа
        """
        try:
            processing_meta = analysis_result.get("processing_metadata", {})
            quality_meta = analysis_result.get("quality_metadata", {})
            psychological = analysis_result.get("psychological_analysis", {})
            traits = analysis_result.get("personality_traits", {})
            router_rec = analysis_result.get("router_recommendations", {})

            async with self.db.get_connection() as conn:
                analysis_id = await conn.fetchval("""
                    INSERT INTO answer_analysis (
                        context_story_id, analysis_version, psychological_insights,
                        trait_scores, emotional_state, fatigue_level,
                        next_question_hints, ai_model_used, processing_time_ms,
                        raw_ai_response, debug_priority, quality_score,
                        confidence_score, special_situation, is_milestone
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                    RETURNING id
                """,
                    context_story_id,
                    analysis_result.get("analysis_version", "2.0"),
                    json.dumps(psychological.get("insights", {}), ensure_ascii=False),
                    json.dumps(traits, ensure_ascii=False),
                    psychological.get("emotional_assessment", {}).get("primary", "neutral"),
                    quality_meta.get("fatigue_indicators", 0.0),
                    json.dumps(router_rec, ensure_ascii=False),
                    processing_meta.get("model_used", "unknown"),
                    processing_meta.get("processing_time_ms", 0),
                    json.dumps(analysis_result, ensure_ascii=False),
                    1 if processing_meta.get("special_situation") else 0,
                    quality_meta.get("overall_reliability", 0.0),
                    quality_meta.get("data_completeness", 0.0),
                    processing_meta.get("special_situation"),
                    processing_meta.get("special_situation") == "breakthrough"
                )

                logger.info(f"💾 Saved context story analysis {analysis_id} for story {context_story_id}")
                return analysis_id

        except Exception as e:
            logger.error(f"❌ Error saving context story analysis for story {context_story_id}: {e}")
            raise

    async def get_user_context_stories(
        self,
        user_id: int,
        story_type: Optional[str] = None,
        limit: int = 10,
        include_analysis: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Получить контекстные истории пользователя

        Args:
            user_id: ID пользователя
            story_type: Фильтр по типу истории (опционально)
            limit: Максимальное количество записей
            include_analysis: Включить результаты анализа

        Returns:
            Список историй с опциональным анализом
        """
        try:
            async with self.db.get_connection() as conn:
                if include_analysis:
                    # Используем готовую view для получения историй с анализом
                    if story_type:
                        rows = await conn.fetch("""
                            SELECT * FROM context_stories_with_analysis
                            WHERE user_id = $1 AND story_type = $2
                            ORDER BY created_at DESC
                            LIMIT $3
                        """, user_id, story_type, limit)
                    else:
                        rows = await conn.fetch("""
                            SELECT * FROM context_stories_with_analysis
                            WHERE user_id = $1
                            ORDER BY created_at DESC
                            LIMIT $2
                        """, user_id, limit)
                else:
                    # Только базовые данные историй
                    if story_type:
                        rows = await conn.fetch("""
                            SELECT id, user_id, session_id, story_text, story_type,
                                   story_source, created_at, metadata
                            FROM user_context_stories
                            WHERE user_id = $1 AND story_type = $2 AND is_active = true
                            ORDER BY created_at DESC
                            LIMIT $3
                        """, user_id, story_type, limit)
                    else:
                        rows = await conn.fetch("""
                            SELECT id, user_id, session_id, story_text, story_type,
                                   story_source, created_at, metadata
                            FROM user_context_stories
                            WHERE user_id = $1 AND is_active = true
                            ORDER BY created_at DESC
                            LIMIT $2
                        """, user_id, limit)

                stories = [dict(row) for row in rows]
                logger.debug(f"📚 Retrieved {len(stories)} context stories for user {user_id}")
                return stories

        except Exception as e:
            logger.error(f"❌ Error getting context stories for user {user_id}: {e}")
            return []

    async def search_context_stories(
        self,
        user_id: int,
        search_query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Полнотекстовый поиск по контекстным историям пользователя

        Args:
            user_id: ID пользователя
            search_query: Поисковый запрос
            limit: Максимальное количество результатов

        Returns:
            Список найденных историй с relevance score
        """
        try:
            async with self.db.get_connection() as conn:
                rows = await conn.fetch("""
                    SELECT * FROM search_user_context_stories($1, $2, $3)
                """, user_id, search_query, limit)

                results = []
                for row in rows:
                    results.append({
                        'story_id': row['story_id'],
                        'story_text': row['story_text'],
                        'story_type': row['story_type'],
                        'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                        'relevance': float(row['relevance'])
                    })

                logger.debug(f"🔍 Found {len(results)} stories for query '{search_query}' (user {user_id})")
                return results

        except Exception as e:
            logger.error(f"❌ Error searching context stories for user {user_id}: {e}")
            return []

    async def deactivate_context_story(self, story_id: int) -> None:
        """
        Деактивировать (мягкое удаление) контекстной истории

        Args:
            story_id: ID истории для деактивации
        """
        try:
            async with self.db.get_connection() as conn:
                await conn.execute("""
                    UPDATE user_context_stories
                    SET is_active = false, updated_at = NOW()
                    WHERE id = $1
                """, story_id)

                logger.info(f"🗑️ Deactivated context story {story_id}")

        except Exception as e:
            logger.error(f"❌ Error deactivating context story {story_id}: {e}")
            raise

    async def get_session_context_story(self, session_id: int) -> Optional[Dict[str, Any]]:
        """
        Получить контекстную историю для конкретной сессии онбординга

        Args:
            session_id: ID сессии

        Returns:
            Данные истории с анализом (если есть) или None
        """
        try:
            async with self.db.get_connection() as conn:
                row = await conn.fetchrow("""
                    SELECT * FROM context_stories_with_analysis
                    WHERE session_id = $1
                    ORDER BY created_at DESC
                    LIMIT 1
                """, session_id)

                if row:
                    return dict(row)
                return None

        except Exception as e:
            logger.error(f"❌ Error getting context story for session {session_id}: {e}")
            return None
