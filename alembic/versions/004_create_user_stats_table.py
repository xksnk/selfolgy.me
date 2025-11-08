"""create user_stats table for normalized statistics

Revision ID: 004
Revises: 003
Create Date: 2025-10-01 16:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    """
    Рефакторинг архитектуры: Перенос total_answers_lifetime в отдельную таблицу user_stats.

    Проблема старой архитектуры:
    - total_answers_lifetime хранился в onboarding_sessions
    - Дублирование данных: одно значение во ВСЕХ сессиях пользователя
    - Нарушение нормализации БД

    Новая архитектура:
    - Создаётся таблица user_stats для хранения статистики пользователя
    - total_answers_lifetime хранится один раз на пользователя
    - Триггер обновляет user_stats вместо всех сессий

    Changes:
    1. Создаёт таблицу user_stats
    2. Мигрирует существующие данные
    3. Обновляет триггер для работы с user_stats
    4. (Опционально) Удаляет старое поле из onboarding_sessions
    """

    # 1. Создаём таблицу user_stats
    op.execute("""
        CREATE TABLE IF NOT EXISTS selfology.user_stats (
            user_id INTEGER PRIMARY KEY,
            total_answers_lifetime INTEGER DEFAULT 0 NOT NULL,
            first_answer_at TIMESTAMP,
            updated_at TIMESTAMP DEFAULT NOW() NOT NULL
        )
    """)

    # 2. Создаём индексы
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_stats_total_answers
        ON selfology.user_stats(total_answers_lifetime)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_stats_first_answer
        ON selfology.user_stats(first_answer_at)
    """)

    # 3. Мигрируем существующие данные
    op.execute("""
        INSERT INTO selfology.user_stats (user_id, total_answers_lifetime, first_answer_at, updated_at)
        SELECT
            os.user_id,
            COUNT(ua.id) as total_answers,
            MIN(ua.answered_at) as first_answer,
            NOW()
        FROM selfology.onboarding_sessions os
        LEFT JOIN selfology.user_answers_new ua ON ua.session_id = os.id
        GROUP BY os.user_id
        ON CONFLICT (user_id) DO UPDATE SET
            total_answers_lifetime = EXCLUDED.total_answers_lifetime,
            first_answer_at = EXCLUDED.first_answer_at,
            updated_at = NOW()
    """)

    # 4. Удаляем старую триггерную функцию
    op.execute("""
        DROP TRIGGER IF EXISTS update_lifetime_answers_trigger
        ON selfology.user_answers_new
    """)

    op.execute("""
        DROP FUNCTION IF EXISTS selfology.update_lifetime_answer_count()
    """)

    # 5. Создаём новую триггерную функцию для user_stats
    op.execute("""
        CREATE OR REPLACE FUNCTION selfology.update_user_stats_on_answer()
        RETURNS TRIGGER AS $$
        DECLARE
            v_user_id INTEGER;
        BEGIN
            -- Получаем user_id из сессии
            SELECT user_id INTO v_user_id
            FROM selfology.onboarding_sessions
            WHERE id = NEW.session_id;

            -- Вставляем или обновляем статистику пользователя
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

    # 6. Создаём новый триггер
    op.execute("""
        CREATE TRIGGER update_user_stats_trigger
        AFTER INSERT ON selfology.user_answers_new
        FOR EACH ROW
        EXECUTE FUNCTION selfology.update_user_stats_on_answer()
    """)

    # 7. (Опционально) Удаляем старое поле из sessions
    # Закомментировано для обратной совместимости
    # op.execute("""
    #     ALTER TABLE selfology.onboarding_sessions
    #     DROP COLUMN IF EXISTS total_answers_lifetime
    # """)


def downgrade():
    """
    Откатывает изменения: восстанавливает старую архитектуру с total_answers_lifetime в sessions.
    """

    # Удаляем новый триггер
    op.execute("""
        DROP TRIGGER IF EXISTS update_user_stats_trigger
        ON selfology.user_answers_new
    """)

    # Удаляем новую функцию
    op.execute("""
        DROP FUNCTION IF EXISTS selfology.update_user_stats_on_answer()
    """)

    # Восстанавливаем старый триггер и функцию (если нужно)
    op.execute("""
        CREATE OR REPLACE FUNCTION selfology.update_lifetime_answer_count()
        RETURNS TRIGGER AS $$
        DECLARE
            v_user_id INTEGER;
            v_total_count INTEGER;
        BEGIN
            SELECT user_id INTO v_user_id
            FROM selfology.onboarding_sessions
            WHERE id = NEW.session_id;

            SELECT COUNT(*) INTO v_total_count
            FROM selfology.user_answers_new ua
            JOIN selfology.onboarding_sessions os ON ua.session_id = os.id
            WHERE os.user_id = v_user_id;

            UPDATE selfology.onboarding_sessions
            SET total_answers_lifetime = v_total_count
            WHERE user_id = v_user_id;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER update_lifetime_answers_trigger
        AFTER INSERT ON selfology.user_answers_new
        FOR EACH ROW
        EXECUTE FUNCTION selfology.update_lifetime_answer_count()
    """)

    # Удаляем индексы
    op.execute("""
        DROP INDEX IF EXISTS selfology.idx_user_stats_total_answers
    """)

    op.execute("""
        DROP INDEX IF EXISTS selfology.idx_user_stats_first_answer
    """)

    # Удаляем таблицу
    op.execute("""
        DROP TABLE IF EXISTS selfology.user_stats
    """)
