"""add global answer counter trigger

Revision ID: 003
Revises: 002
Create Date: 2025-10-01 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    """
    Добавляет глобальный счётчик ответов для пользователя.

    Changes:
    1. Добавляет поле total_answers_lifetime в onboarding_sessions
    2. Создаёт триггерную функцию для автоматического обновления счётчика
    3. Создаёт триггер на INSERT в user_answers_new
    4. Заполняет существующие данные
    """

    # 1. Добавляем новое поле для глобального счётчика
    op.execute("""
        ALTER TABLE selfology.onboarding_sessions
        ADD COLUMN IF NOT EXISTS total_answers_lifetime INTEGER DEFAULT 0
    """)

    # 2. Создаём функцию триггера
    op.execute("""
        CREATE OR REPLACE FUNCTION selfology.update_lifetime_answer_count()
        RETURNS TRIGGER AS $$
        DECLARE
            v_user_id INTEGER;
            v_total_count INTEGER;
        BEGIN
            -- Получаем user_id из сессии
            SELECT user_id INTO v_user_id
            FROM selfology.onboarding_sessions
            WHERE id = NEW.session_id;

            -- Считаем общее количество ответов пользователя
            SELECT COUNT(*) INTO v_total_count
            FROM selfology.user_answers_new ua
            JOIN selfology.onboarding_sessions os ON ua.session_id = os.id
            WHERE os.user_id = v_user_id;

            -- Обновляем счётчик во ВСЕХ сессиях пользователя
            UPDATE selfology.onboarding_sessions
            SET total_answers_lifetime = v_total_count
            WHERE user_id = v_user_id;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # 3. Создаём триггер
    op.execute("""
        DROP TRIGGER IF EXISTS update_lifetime_answers_trigger
        ON selfology.user_answers_new;

        CREATE TRIGGER update_lifetime_answers_trigger
        AFTER INSERT ON selfology.user_answers_new
        FOR EACH ROW
        EXECUTE FUNCTION selfology.update_lifetime_answer_count();
    """)

    # 4. Заполняем существующие данные для всех пользователей
    op.execute("""
        UPDATE selfology.onboarding_sessions os
        SET total_answers_lifetime = (
            SELECT COUNT(*)
            FROM selfology.user_answers_new ua
            JOIN selfology.onboarding_sessions os2 ON ua.session_id = os2.id
            WHERE os2.user_id = os.user_id
        );
    """)

    # 5. Создаём индекс для производительности
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_lifetime_answers
        ON selfology.onboarding_sessions(user_id, total_answers_lifetime);
    """)


def downgrade():
    """
    Откатывает изменения глобального счётчика.
    """

    # Удаляем триггер
    op.execute("""
        DROP TRIGGER IF EXISTS update_lifetime_answers_trigger
        ON selfology.user_answers_new;
    """)

    # Удаляем функцию триггера
    op.execute("""
        DROP FUNCTION IF EXISTS selfology.update_lifetime_answer_count();
    """)

    # Удаляем индекс
    op.execute("""
        DROP INDEX IF EXISTS selfology.idx_sessions_lifetime_answers;
    """)

    # Удаляем поле
    op.execute("""
        ALTER TABLE selfology.onboarding_sessions
        DROP COLUMN IF EXISTS total_answers_lifetime;
    """)
