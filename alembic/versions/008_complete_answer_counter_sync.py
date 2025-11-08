"""Complete answer counter synchronization with INSERT/UPDATE/DELETE triggers

Revision ID: 008
Revises: 007
Create Date: 2025-10-02 20:00:00.000000

ЦЕЛЬ: Полная синхронизация счетчика user_stats.total_answers_lifetime

РЕШЕНИЕ:
1. Триггеры на все операции (INSERT, UPDATE, DELETE)
2. Автоматическая коррекция при рассинхронизации
3. Периодическая валидация через CRON
4. Monitoring view для отслеживания дрифта

ПРЕИМУЩЕСТВА:
- Счетчик ВСЕГДА актуален (INSERT/DELETE/UPDATE)
- Защита от race conditions через advisory locks
- Автоматическое восстановление при сбоях
- Мониторинг консистентности данных
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade():
    """
    Создание комплексной системы синхронизации счетчиков
    """

    # 1. Удаляем старый триггер (только на INSERT)
    op.execute("""
        DROP TRIGGER IF EXISTS update_user_stats_trigger
        ON selfology.user_answers_new
    """)

    op.execute("""
        DROP FUNCTION IF EXISTS selfology.update_user_stats_on_answer()
    """)

    # 2. Создаем универсальную функцию для синхронизации счетчика
    op.execute("""
        CREATE OR REPLACE FUNCTION selfology.sync_answer_counter()
        RETURNS TRIGGER AS $$
        DECLARE
            v_user_id INTEGER;
            v_lock_key BIGINT;
            v_operation TEXT;
        BEGIN
            -- Определяем user_id в зависимости от операции
            IF TG_OP = 'DELETE' THEN
                -- При DELETE используем OLD
                SELECT user_id INTO v_user_id
                FROM selfology.onboarding_sessions
                WHERE id = OLD.session_id;
                v_operation := 'DELETE';
            ELSE
                -- При INSERT/UPDATE используем NEW
                SELECT user_id INTO v_user_id
                FROM selfology.onboarding_sessions
                WHERE id = NEW.session_id;
                v_operation := TG_OP;
            END IF;

            -- Генерируем уникальный ключ для advisory lock
            v_lock_key := ('x' || md5('user_answer_counter_' || v_user_id::text))::bit(64)::bigint;

            -- Получаем блокировку для предотвращения race conditions
            -- Используем BLOCKING lock для гарантии консистентности
            PERFORM pg_advisory_xact_lock(v_lock_key);

            -- ВАРИАНТ 1: Инкрементальное обновление (быстрее)
            -- Подходит для 99% случаев
            IF TG_OP = 'INSERT' THEN
                -- Увеличиваем счетчик при вставке
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

            ELSIF TG_OP = 'DELETE' THEN
                -- Уменьшаем счетчик при удалении
                UPDATE selfology.user_stats
                SET
                    total_answers_lifetime = GREATEST(total_answers_lifetime - 1, 0),
                    updated_at = NOW()
                WHERE user_id = v_user_id;

            ELSIF TG_OP = 'UPDATE' THEN
                -- При UPDATE session_id - нужно пересчитать для обоих пользователей
                IF OLD.session_id != NEW.session_id THEN
                    DECLARE
                        v_old_user_id INTEGER;
                        v_new_user_id INTEGER;
                    BEGIN
                        SELECT user_id INTO v_old_user_id
                        FROM selfology.onboarding_sessions WHERE id = OLD.session_id;

                        SELECT user_id INTO v_new_user_id
                        FROM selfology.onboarding_sessions WHERE id = NEW.session_id;

                        -- Уменьшаем для старого пользователя
                        UPDATE selfology.user_stats
                        SET total_answers_lifetime = GREATEST(total_answers_lifetime - 1, 0)
                        WHERE user_id = v_old_user_id;

                        -- Увеличиваем для нового пользователя
                        INSERT INTO selfology.user_stats (user_id, total_answers_lifetime, updated_at)
                        VALUES (v_new_user_id, 1, NOW())
                        ON CONFLICT (user_id) DO UPDATE SET
                            total_answers_lifetime = selfology.user_stats.total_answers_lifetime + 1;
                    END;
                END IF;
            END IF;

            -- ВАРИАНТ 2: Точный пересчет (для защиты от дрифта)
            -- Автоматически срабатывает раз в N операций
            -- Используем случайность для распределения нагрузки
            IF random() < 0.01 THEN  -- 1% вероятность (каждые ~100 операций)
                PERFORM selfology.recalculate_answer_count(v_user_id);
            END IF;

            -- Возвращаем результат в зависимости от операции
            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            ELSE
                RETURN NEW;
            END IF;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # 3. Создаем функцию точного пересчета (fallback для коррекции дрифта)
    op.execute("""
        CREATE OR REPLACE FUNCTION selfology.recalculate_answer_count(p_user_id INTEGER)
        RETURNS INTEGER AS $$
        DECLARE
            v_actual_count INTEGER;
        BEGIN
            -- Точный подсчет из user_answers_new
            SELECT COUNT(*) INTO v_actual_count
            FROM selfology.user_answers_new ua
            JOIN selfology.onboarding_sessions os ON ua.session_id = os.id
            WHERE os.user_id = p_user_id;

            -- Обновляем счетчик точным значением
            UPDATE selfology.user_stats
            SET
                total_answers_lifetime = v_actual_count,
                updated_at = NOW()
            WHERE user_id = p_user_id;

            RETURN v_actual_count;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # 4. Создаем триггеры на все операции
    op.execute("""
        CREATE TRIGGER sync_answer_counter_insert
        AFTER INSERT ON selfology.user_answers_new
        FOR EACH ROW
        EXECUTE FUNCTION selfology.sync_answer_counter()
    """)

    op.execute("""
        CREATE TRIGGER sync_answer_counter_delete
        AFTER DELETE ON selfology.user_answers_new
        FOR EACH ROW
        EXECUTE FUNCTION selfology.sync_answer_counter()
    """)

    op.execute("""
        CREATE TRIGGER sync_answer_counter_update
        AFTER UPDATE OF session_id ON selfology.user_answers_new
        FOR EACH ROW
        WHEN (OLD.session_id IS DISTINCT FROM NEW.session_id)
        EXECUTE FUNCTION selfology.sync_answer_counter()
    """)

    # 5. Создаем функцию для массового пересчета (для периодических проверок)
    op.execute("""
        CREATE OR REPLACE FUNCTION selfology.validate_all_answer_counters()
        RETURNS TABLE(
            user_id INTEGER,
            stored_count INTEGER,
            actual_count INTEGER,
            drift INTEGER,
            corrected BOOLEAN
        ) AS $$
        DECLARE
            v_user_record RECORD;
            v_actual_count INTEGER;
            v_drift INTEGER;
        BEGIN
            -- Проходим по всем пользователям с ответами
            FOR v_user_record IN
                SELECT DISTINCT os.user_id
                FROM selfology.user_answers_new ua
                JOIN selfology.onboarding_sessions os ON ua.session_id = os.id
            LOOP
                -- Получаем хранимое значение
                SELECT COALESCE(us.total_answers_lifetime, 0)
                INTO stored_count
                FROM selfology.user_stats us
                WHERE us.user_id = v_user_record.user_id;

                -- Получаем актуальное значение
                SELECT COUNT(*)
                INTO actual_count
                FROM selfology.user_answers_new ua
                JOIN selfology.onboarding_sessions os ON ua.session_id = os.id
                WHERE os.user_id = v_user_record.user_id;

                drift := stored_count - actual_count;

                -- Если есть дрифт - корректируем
                IF drift != 0 THEN
                    UPDATE selfology.user_stats
                    SET
                        total_answers_lifetime = actual_count,
                        updated_at = NOW()
                    WHERE selfology.user_stats.user_id = v_user_record.user_id;

                    corrected := TRUE;
                ELSE
                    corrected := FALSE;
                END IF;

                user_id := v_user_record.user_id;

                RETURN NEXT;
            END LOOP;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # 6. Создаем view для мониторинга в реальном времени
    op.execute("""
        CREATE OR REPLACE VIEW selfology.answer_counter_health AS
        SELECT
            us.user_id,
            us.total_answers_lifetime as stored_count,
            actual.answer_count as actual_count,
            us.total_answers_lifetime - COALESCE(actual.answer_count, 0) as drift,
            CASE
                WHEN us.total_answers_lifetime = COALESCE(actual.answer_count, 0)
                THEN 'SYNCED'
                WHEN ABS(us.total_answers_lifetime - COALESCE(actual.answer_count, 0)) <= 1
                THEN 'ACCEPTABLE'
                ELSE 'CRITICAL'
            END as health_status,
            us.updated_at as last_sync
        FROM selfology.user_stats us
        LEFT JOIN (
            SELECT os.user_id, COUNT(ua.id) as answer_count
            FROM selfology.user_answers_new ua
            JOIN selfology.onboarding_sessions os ON ua.session_id = os.id
            GROUP BY os.user_id
        ) actual ON us.user_id = actual.user_id
        ORDER BY ABS(us.total_answers_lifetime - COALESCE(actual.answer_count, 0)) DESC
    """)

    # 7. Создаем функцию для автоматической коррекции критических случаев
    op.execute("""
        CREATE OR REPLACE FUNCTION selfology.auto_fix_critical_drift()
        RETURNS TABLE(
            user_id INTEGER,
            old_count INTEGER,
            new_count INTEGER,
            fixed_at TIMESTAMP
        ) AS $$
        BEGIN
            RETURN QUERY
            WITH critical_cases AS (
                SELECT *
                FROM selfology.answer_counter_health
                WHERE health_status = 'CRITICAL'
            )
            UPDATE selfology.user_stats us
            SET
                total_answers_lifetime = cc.actual_count,
                updated_at = NOW()
            FROM critical_cases cc
            WHERE us.user_id = cc.user_id
            RETURNING
                us.user_id,
                cc.stored_count as old_count,
                cc.actual_count as new_count,
                NOW() as fixed_at;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # 8. Инициализация: пересчитываем все существующие счетчики
    op.execute("""
        DO $$
        DECLARE
            v_user_id INTEGER;
            v_count INTEGER;
        BEGIN
            FOR v_user_id IN
                SELECT DISTINCT os.user_id
                FROM selfology.user_answers_new ua
                JOIN selfology.onboarding_sessions os ON ua.session_id = os.id
            LOOP
                PERFORM selfology.recalculate_answer_count(v_user_id);
            END LOOP;
        END $$;
    """)


def downgrade():
    """
    Откат к старому триггеру (только INSERT)
    """

    # Удаляем новые триггеры
    op.execute("""
        DROP TRIGGER IF EXISTS sync_answer_counter_insert ON selfology.user_answers_new
    """)

    op.execute("""
        DROP TRIGGER IF EXISTS sync_answer_counter_delete ON selfology.user_answers_new
    """)

    op.execute("""
        DROP TRIGGER IF EXISTS sync_answer_counter_update ON selfology.user_answers_new
    """)

    # Удаляем функции
    op.execute("""
        DROP FUNCTION IF EXISTS selfology.sync_answer_counter()
    """)

    op.execute("""
        DROP FUNCTION IF EXISTS selfology.recalculate_answer_count(INTEGER)
    """)

    op.execute("""
        DROP FUNCTION IF EXISTS selfology.validate_all_answer_counters()
    """)

    op.execute("""
        DROP FUNCTION IF EXISTS selfology.auto_fix_critical_drift()
    """)

    # Удаляем view
    op.execute("""
        DROP VIEW IF EXISTS selfology.answer_counter_health
    """)

    # Восстанавливаем старый триггер
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
