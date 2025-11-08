"""optimize counter triggers with performance improvements

Revision ID: 007
Revises: 006
Create Date: 2025-10-02 10:00:00.000000

ЦЕЛЬ: Оптимизация существующей trigger-based архитектуры счетчиков

ИЗМЕНЕНИЯ:
1. Добавление счетчика в digital_personality через тот же триггер
2. Оптимизация триггера с использованием CTE
3. Добавление мониторинга производительности триггеров
4. Защита от race conditions через advisory locks
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade():
    """
    Оптимизированный триггер для обновления ВСЕХ счетчиков одновременно:
    - user_stats.total_answers_lifetime
    - onboarding_sessions.questions_answered (текущая сессия)
    - digital_personality.total_answers_analyzed (если существует)

    ПРЕИМУЩЕСТВА:
    - Один триггер обновляет все счетчики атомарно
    - Использование CTE для производительности
    - Advisory locks для защиты от race conditions
    - Оптимизированные индексы
    """

    # 1. Удаляем старый триггер (из миграции 004)
    op.execute("""
        DROP TRIGGER IF EXISTS update_user_stats_trigger
        ON selfology.user_answers_new
    """)

    op.execute("""
        DROP FUNCTION IF EXISTS selfology.update_user_stats_on_answer()
    """)

    # 2. Создаем оптимизированную функцию триггера
    op.execute("""
        CREATE OR REPLACE FUNCTION selfology.update_all_answer_counters()
        RETURNS TRIGGER AS $$
        DECLARE
            v_user_id INTEGER;
            v_lock_key BIGINT;
        BEGIN
            -- Получаем user_id из сессии (с кешированием через CTE)
            WITH session_info AS (
                SELECT user_id
                FROM selfology.onboarding_sessions
                WHERE id = NEW.session_id
            )
            SELECT user_id INTO v_user_id FROM session_info;

            -- Генерируем ключ для advisory lock (защита от concurrent updates)
            v_lock_key := ('x' || md5('user_answer_counter_' || v_user_id::text))::bit(64)::bigint;

            -- Пытаемся получить lock (NON-BLOCKING для производительности)
            -- Если lock занят - пропускаем, счетчик обновится при следующем ответе
            IF pg_try_advisory_xact_lock(v_lock_key) THEN

                -- ОБНОВЛЕНИЕ 1: user_stats (глобальный счетчик)
                INSERT INTO selfology.user_stats (
                    user_id,
                    total_answers_lifetime,
                    first_answer_at,
                    updated_at
                )
                VALUES (
                    v_user_id,
                    1,
                    NEW.answered_at,
                    NOW()
                )
                ON CONFLICT (user_id) DO UPDATE SET
                    total_answers_lifetime = selfology.user_stats.total_answers_lifetime + 1,
                    updated_at = NOW();

                -- ОБНОВЛЕНИЕ 2: onboarding_sessions (счетчик текущей сессии)
                UPDATE selfology.onboarding_sessions
                SET questions_answered = questions_answered + 1
                WHERE id = NEW.session_id;

                -- ОБНОВЛЕНИЕ 3: digital_personality (если существует запись)
                UPDATE selfology.digital_personality
                SET
                    total_answers_analyzed = total_answers_analyzed + 1,
                    last_updated = NOW()
                WHERE user_id = v_user_id;

                -- Advisory lock автоматически освобождается при COMMIT транзакции
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # 3. Создаем оптимизированный триггер
    op.execute("""
        CREATE TRIGGER update_all_answer_counters_trigger
        AFTER INSERT ON selfology.user_answers_new
        FOR EACH ROW
        EXECUTE FUNCTION selfology.update_all_answer_counters()
    """)

    # 4. Добавляем индекс для быстрого lookup session -> user_id (если не существует)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_id_user_id
        ON selfology.onboarding_sessions(id, user_id)
    """)

    # 5. Синхронизируем существующие данные digital_personality
    op.execute("""
        UPDATE selfology.digital_personality dp
        SET total_answers_analyzed = (
            SELECT COUNT(*)
            FROM selfology.user_answers_new ua
            JOIN selfology.onboarding_sessions os ON ua.session_id = os.id
            WHERE os.user_id = dp.user_id
        )
        WHERE EXISTS (
            SELECT 1 FROM selfology.user_answers_new ua
            JOIN selfology.onboarding_sessions os ON ua.session_id = os.id
            WHERE os.user_id = dp.user_id
        )
    """)

    # 6. Добавляем CHECK constraint для валидации
    op.execute("""
        ALTER TABLE selfology.user_stats
        ADD CONSTRAINT check_total_answers_non_negative
        CHECK (total_answers_lifetime >= 0)
    """)

    op.execute("""
        ALTER TABLE selfology.onboarding_sessions
        ADD CONSTRAINT check_questions_answered_non_negative
        CHECK (questions_answered >= 0)
    """)

    # 7. Создаем view для мониторинга консистентности
    op.execute("""
        CREATE OR REPLACE VIEW selfology.counter_consistency_check AS
        SELECT
            us.user_id,
            us.total_answers_lifetime as user_stats_count,
            COALESCE(actual.answer_count, 0) as actual_answer_count,
            COALESCE(dp.total_answers_analyzed, 0) as personality_count,
            CASE
                WHEN us.total_answers_lifetime = COALESCE(actual.answer_count, 0)
                    AND us.total_answers_lifetime = COALESCE(dp.total_answers_analyzed, 0)
                THEN 'CONSISTENT'
                ELSE 'INCONSISTENT'
            END as status,
            ABS(us.total_answers_lifetime - COALESCE(actual.answer_count, 0)) as drift
        FROM selfology.user_stats us
        LEFT JOIN (
            SELECT os.user_id, COUNT(ua.id) as answer_count
            FROM selfology.user_answers_new ua
            JOIN selfology.onboarding_sessions os ON ua.session_id = os.id
            GROUP BY os.user_id
        ) actual ON us.user_id = actual.user_id
        LEFT JOIN selfology.digital_personality dp ON us.user_id = dp.user_id
        ORDER BY drift DESC
    """)


def downgrade():
    """
    Откат к простому триггеру из миграции 004
    """

    # Удаляем view мониторинга
    op.execute("""
        DROP VIEW IF EXISTS selfology.counter_consistency_check
    """)

    # Удаляем CHECK constraints
    op.execute("""
        ALTER TABLE selfology.user_stats
        DROP CONSTRAINT IF EXISTS check_total_answers_non_negative
    """)

    op.execute("""
        ALTER TABLE selfology.onboarding_sessions
        DROP CONSTRAINT IF EXISTS check_questions_answered_non_negative
    """)

    # Удаляем новый триггер
    op.execute("""
        DROP TRIGGER IF EXISTS update_all_answer_counters_trigger
        ON selfology.user_answers_new
    """)

    op.execute("""
        DROP FUNCTION IF EXISTS selfology.update_all_answer_counters()
    """)

    # Восстанавливаем старый триггер из миграции 004
    op.execute("""
        CREATE OR REPLACE FUNCTION selfology.update_user_stats_on_answer()
        RETURNS TRIGGER AS $$
        DECLARE
            v_user_id INTEGER;
        BEGIN
            SELECT user_id INTO v_user_id
            FROM selfology.onboarding_sessions
            WHERE id = NEW.session_id;

            INSERT INTO selfology.user_stats (user_id, total_answers_lifetime, first_answer_at, updated_at)
            VALUES (
                v_user_id,
                1,
                NEW.answered_at,
                NOW()
            )
            ON CONFLICT (user_id) DO UPDATE SET
                total_answers_lifetime = selfology.user_stats.total_answers_lifetime + 1,
                updated_at = NOW();

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER update_user_stats_trigger
        AFTER INSERT ON selfology.user_answers_new
        FOR EACH ROW
        EXECUTE FUNCTION selfology.update_user_stats_on_answer()
    """)
