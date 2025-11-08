"""
Примеры использования системы счетчиков Selfology

Демонстрирует правильные и неправильные подходы к работе со счетчиками ответов.
"""

import asyncio
import asyncpg
from typing import Dict, Optional
from datetime import datetime


# ============================================================================
# ✅ ПРАВИЛЬНЫЕ ПРИМЕРЫ (Best Practices)
# ============================================================================


class CorrectCounterUsage:
    """Правильное использование триггер-based счетчиков"""

    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool

    async def save_answer(
        self,
        session_id: int,
        question_id: str,
        answer_text: str
    ) -> int:
        """
        ✅ ПРАВИЛЬНО: Простой INSERT - триггер обновит ВСЕ счетчики автоматически

        Триггер update_all_answer_counters() автоматически:
        - Инкрементирует user_stats.total_answers_lifetime
        - Инкрементирует onboarding_sessions.questions_answered
        - Инкрементирует digital_personality.total_answers_analyzed
        """

        async with self.db.acquire() as conn:
            answer_id = await conn.fetchval("""
                INSERT INTO selfology.user_answers_new (
                    session_id,
                    question_json_id,
                    raw_answer,
                    answer_length,
                    answered_at
                )
                VALUES ($1, $2, $3, $4, NOW())
                RETURNING id
            """, session_id, question_id, answer_text, len(answer_text))

            # ✅ Триггер уже обновил все счетчики!
            # Не нужно делать дополнительных UPDATE запросов

            return answer_id

    async def save_answer_with_transaction(
        self,
        session_id: int,
        question_id: str,
        answer_text: str
    ) -> Dict[str, any]:
        """
        ✅ ПРАВИЛЬНО: INSERT в транзакции для атомарности

        Гарантирует, что:
        - Либо вставка и все обновления счетчиков выполнены
        - Либо ничего не изменилось (ROLLBACK)
        """

        async with self.db.acquire() as conn:
            async with conn.transaction():
                # Вставка ответа
                answer_id = await conn.fetchval("""
                    INSERT INTO selfology.user_answers_new (
                        session_id,
                        question_json_id,
                        raw_answer,
                        answer_length
                    )
                    VALUES ($1, $2, $3, $4)
                    RETURNING id
                """, session_id, question_id, answer_text, len(answer_text))

                # Триггер уже сработал внутри транзакции

                # Читаем обновленные счетчики
                stats = await conn.fetchrow("""
                    SELECT
                        us.total_answers_lifetime,
                        os.questions_answered as session_answers
                    FROM selfology.onboarding_sessions os
                    JOIN selfology.user_stats us ON us.user_id = os.user_id
                    WHERE os.id = $1
                """, session_id)

                return {
                    'answer_id': answer_id,
                    'total_answers': stats['total_answers_lifetime'],
                    'session_answers': stats['session_answers']
                }

    async def get_user_total_answers(self, user_id: int) -> int:
        """
        ✅ ПРАВИЛЬНО: Чтение из оптимизированной таблицы user_stats

        Быстро (индексированный lookup), всегда актуально.
        """

        async with self.db.acquire() as conn:
            total = await conn.fetchval("""
                SELECT total_answers_lifetime
                FROM selfology.user_stats
                WHERE user_id = $1
            """, user_id)

            return total if total is not None else 0

    async def get_session_stats(self, session_id: int) -> Dict[str, any]:
        """
        ✅ ПРАВИЛЬНО: Объединенный запрос для всех метрик сессии

        Получаем все счетчики одним запросом.
        """

        async with self.db.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT
                    os.id as session_id,
                    os.user_id,
                    os.questions_asked,
                    os.questions_answered,
                    us.total_answers_lifetime,
                    dp.total_answers_analyzed
                FROM selfology.onboarding_sessions os
                LEFT JOIN selfology.user_stats us ON us.user_id = os.user_id
                LEFT JOIN selfology.digital_personality dp ON dp.user_id = os.user_id
                WHERE os.id = $1
            """, session_id)

            if stats:
                return dict(stats)
            return None

    async def batch_save_answers(
        self,
        answers: list[Dict[str, any]]
    ) -> list[int]:
        """
        ✅ ПРАВИЛЬНО: Batch insert с триггерами

        Триггер срабатывает для каждой строки, но в одной транзакции.
        Все счетчики обновляются атомарно.
        """

        async with self.db.acquire() as conn:
            async with conn.transaction():
                answer_ids = []

                for answer in answers:
                    answer_id = await conn.fetchval("""
                        INSERT INTO selfology.user_answers_new (
                            session_id,
                            question_json_id,
                            raw_answer
                        )
                        VALUES ($1, $2, $3)
                        RETURNING id
                    """,
                        answer['session_id'],
                        answer['question_id'],
                        answer['text']
                    )

                    answer_ids.append(answer_id)

                # Триггер обновил счетчики для каждого INSERT
                return answer_ids


# ============================================================================
# ❌ НЕПРАВИЛЬНЫЕ ПРИМЕРЫ (Anti-Patterns)
# ============================================================================


class IncorrectCounterUsage:
    """Примеры неправильного использования - НЕ ДЕЛАЙТЕ ТАК!"""

    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool

    async def save_answer_with_manual_update(
        self,
        session_id: int,
        question_id: str,
        answer_text: str
    ) -> int:
        """
        ❌ НЕПРАВИЛЬНО: Manual UPDATE после INSERT

        Проблемы:
        1. Дублирование логики триггера
        2. Триггер УЖЕ обновил счетчик - получится двойное инкрементирование!
        3. Race condition при concurrent inserts
        """

        async with self.db.acquire() as conn:
            # INSERT активирует триггер
            answer_id = await conn.fetchval("""
                INSERT INTO selfology.user_answers_new (
                    session_id, question_json_id, raw_answer
                )
                VALUES ($1, $2, $3)
                RETURNING id
            """, session_id, question_id, answer_text)

            # ❌ ОШИБКА: Триггер уже инкрементировал!
            # Этот UPDATE даст ДВОЙНОЙ инкремент
            await conn.execute("""
                UPDATE selfology.onboarding_sessions
                SET questions_answered = questions_answered + 1
                WHERE id = $1
            """, session_id)

            # ❌ ОШИБКА: И здесь тоже двойной инкремент
            await conn.execute("""
                UPDATE selfology.user_stats
                SET total_answers_lifetime = total_answers_lifetime + 1
                WHERE user_id = (
                    SELECT user_id FROM selfology.onboarding_sessions WHERE id = $1
                )
            """, session_id)

            return answer_id

    async def get_total_with_count(self, user_id: int) -> int:
        """
        ❌ НЕПРАВИЛЬНО: COUNT(*) вместо чтения из user_stats

        Проблемы:
        1. Очень медленно при большом количестве ответов
        2. Full table scan + JOIN
        3. Зачем считать если уже есть готовый счетчик?
        """

        async with self.db.acquire() as conn:
            # ❌ МЕДЛЕННО: O(N) сложность
            total = await conn.fetchval("""
                SELECT COUNT(*)
                FROM selfology.user_answers_new ua
                JOIN selfology.onboarding_sessions os ON ua.session_id = os.id
                WHERE os.user_id = $1
            """, user_id)

            return total or 0

    async def save_without_transaction(
        self,
        session_id: int,
        question_id: str,
        answer_text: str
    ) -> int:
        """
        ⚠️ ПОТЕНЦИАЛЬНО ОПАСНО: INSERT без транзакции при сложной логике

        Проблемы:
        1. Если последующий код упадет - счетчики уже обновлены
        2. Частичная консистентность данных
        3. Сложно откатить изменения
        """

        async with self.db.acquire() as conn:
            # Вставка ответа (триггер сработал)
            answer_id = await conn.fetchval("""
                INSERT INTO selfology.user_answers_new (
                    session_id, question_json_id, raw_answer
                )
                VALUES ($1, $2, $3)
                RETURNING id
            """, session_id, question_id, answer_text)

            # ⚠️ ОПАСНО: Если следующий код упадет, счетчики уже обновлены!
            # Но answer_metadata не создан
            try:
                await conn.execute("""
                    INSERT INTO answer_metadata (answer_id, some_field)
                    VALUES ($1, $2)
                """, answer_id, "some_value")
            except Exception:
                # ⚠️ Счетчики уже обновлены, но metadata нет!
                # Консистентность нарушена
                raise

            return answer_id

    async def disable_trigger_for_bulk(
        self,
        answers: list[Dict[str, any]]
    ):
        """
        ❌ ОЧЕНЬ ПЛОХО: Отключение триггера для bulk operations

        Проблемы:
        1. Счетчики не обновятся!
        2. Нарушение консистентности данных
        3. Требует ручного пересчета после
        """

        async with self.db.acquire() as conn:
            # ❌ НИКОГДА НЕ ДЕЛАЙТЕ ТАК!
            await conn.execute("""
                ALTER TABLE selfology.user_answers_new
                DISABLE TRIGGER update_all_answer_counters_trigger
            """)

            # Bulk insert
            await conn.executemany("""
                INSERT INTO selfology.user_answers_new (
                    session_id, question_json_id, raw_answer
                )
                VALUES ($1, $2, $3)
            """, [(a['session_id'], a['question_id'], a['text']) for a in answers])

            # ❌ Счетчики НЕ обновились!

            # Включаем триггер обратно
            await conn.execute("""
                ALTER TABLE selfology.user_answers_new
                ENABLE TRIGGER update_all_answer_counters_trigger
            """)

            # ⚠️ Теперь нужен manual recount - сложно и опасно!


# ============================================================================
# 🔧 УТИЛИТЫ И HELPER ФУНКЦИИ
# ============================================================================


class CounterUtilities:
    """Полезные утилиты для работы со счетчиками"""

    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool

    async def verify_counter_consistency(self, user_id: int) -> Dict[str, any]:
        """
        Проверка консистентности счетчиков для пользователя

        Returns:
            {
                'user_id': int,
                'stats_count': int,
                'actual_count': int,
                'personality_count': int,
                'is_consistent': bool,
                'drift': int
            }
        """

        async with self.db.acquire() as conn:
            result = await conn.fetchrow("""
                SELECT
                    $1 as user_id,
                    us.total_answers_lifetime as stats_count,
                    COUNT(ua.id) as actual_count,
                    dp.total_answers_analyzed as personality_count,
                    us.total_answers_lifetime = COUNT(ua.id) as is_consistent,
                    ABS(us.total_answers_lifetime - COUNT(ua.id)) as drift
                FROM selfology.user_stats us
                LEFT JOIN selfology.onboarding_sessions os ON os.user_id = us.user_id
                LEFT JOIN selfology.user_answers_new ua ON ua.session_id = os.id
                LEFT JOIN selfology.digital_personality dp ON dp.user_id = us.user_id
                WHERE us.user_id = $1
                GROUP BY us.user_id, us.total_answers_lifetime, dp.total_answers_analyzed
            """, user_id)

            if result:
                return dict(result)
            return None

    async def repair_user_counters(self, user_id: int) -> bool:
        """
        Исправление несогласованных счетчиков для пользователя

        Returns:
            True если счетчики были исправлены
        """

        async with self.db.acquire() as conn:
            async with conn.transaction():
                # Подсчитываем фактическое количество ответов
                actual_count = await conn.fetchval("""
                    SELECT COUNT(*)
                    FROM selfology.user_answers_new ua
                    JOIN selfology.onboarding_sessions os ON ua.session_id = os.id
                    WHERE os.user_id = $1
                """, user_id)

                # Обновляем user_stats
                await conn.execute("""
                    UPDATE selfology.user_stats
                    SET
                        total_answers_lifetime = $2,
                        updated_at = NOW()
                    WHERE user_id = $1
                """, user_id, actual_count)

                # Обновляем digital_personality
                await conn.execute("""
                    UPDATE selfology.digital_personality
                    SET
                        total_answers_analyzed = $2,
                        last_updated = NOW()
                    WHERE user_id = $1
                """, user_id, actual_count)

                # Обновляем счетчики в каждой сессии
                await conn.execute("""
                    UPDATE selfology.onboarding_sessions os
                    SET questions_answered = (
                        SELECT COUNT(*)
                        FROM selfology.user_answers_new ua
                        WHERE ua.session_id = os.id
                    )
                    WHERE os.user_id = $1
                """, user_id)

                return True

    async def get_counter_statistics(self) -> Dict[str, any]:
        """
        Глобальная статистика счетчиков системы

        Returns:
            {
                'total_users': int,
                'total_answers': int,
                'avg_answers_per_user': float,
                'users_with_inconsistency': int,
                'max_drift': int
            }
        """

        async with self.db.acquire() as conn:
            stats = await conn.fetchrow("""
                WITH counter_check AS (
                    SELECT
                        us.user_id,
                        us.total_answers_lifetime as stats_count,
                        COUNT(ua.id) as actual_count,
                        ABS(us.total_answers_lifetime - COUNT(ua.id)) as drift
                    FROM selfology.user_stats us
                    LEFT JOIN selfology.onboarding_sessions os ON os.user_id = us.user_id
                    LEFT JOIN selfology.user_answers_new ua ON ua.session_id = os.id
                    GROUP BY us.user_id, us.total_answers_lifetime
                )
                SELECT
                    COUNT(DISTINCT user_id) as total_users,
                    SUM(stats_count) as total_answers,
                    AVG(stats_count) as avg_answers_per_user,
                    COUNT(*) FILTER (WHERE drift > 0) as users_with_inconsistency,
                    MAX(drift) as max_drift
                FROM counter_check
            """)

            return dict(stats) if stats else {}


# ============================================================================
# 📚 ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ
# ============================================================================


async def example_correct_workflow():
    """Пример правильного рабочего процесса"""

    # Подключение к БД
    db_pool = await asyncpg.create_pool(
        host='localhost',
        port=5432,
        database='n8n',
        user='postgres',
        password='your_password',
        min_size=5,
        max_size=20
    )

    correct = CorrectCounterUsage(db_pool)

    # ✅ Сохранение ответа (триггер обновит счетчики)
    answer_id = await correct.save_answer(
        session_id=123,
        question_id="Q001",
        answer_text="Мой ответ на вопрос"
    )

    print(f"✅ Answer saved: {answer_id}")

    # ✅ Чтение глобального счетчика
    total = await correct.get_user_total_answers(user_id=456)
    print(f"✅ User total answers: {total}")

    # ✅ Получение всех метрик сессии
    stats = await correct.get_session_stats(session_id=123)
    print(f"✅ Session stats: {stats}")

    await db_pool.close()


async def example_consistency_check():
    """Пример проверки и исправления консистентности"""

    db_pool = await asyncpg.create_pool(
        host='localhost',
        port=5432,
        database='n8n',
        user='postgres',
        password='your_password'
    )

    utils = CounterUtilities(db_pool)

    # Проверка консистентности для пользователя
    check = await utils.verify_counter_consistency(user_id=456)

    if not check['is_consistent']:
        print(f"⚠️  Inconsistency detected! Drift: {check['drift']}")

        # Автоматическое исправление
        repaired = await utils.repair_user_counters(user_id=456)

        if repaired:
            print("✅ Counters repaired successfully")

    # Глобальная статистика
    stats = await utils.get_counter_statistics()
    print(f"📊 System stats: {stats}")

    await db_pool.close()


if __name__ == '__main__':
    # Запуск примеров
    asyncio.run(example_correct_workflow())
    asyncio.run(example_consistency_check())
