#!/usr/bin/env python3
"""
Counter Health Check - мониторинг консистентности счетчиков

Использование:
    python scripts/counter_health_check.py check          # Проверка консистентности
    python scripts/counter_health_check.py repair         # Автоматическое исправление
    python scripts/counter_health_check.py stats          # Статистика триггеров
"""

import asyncio
import asyncpg
from typing import Dict, List, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CounterHealthChecker:
    """Мониторинг и восстановление консистентности счетчиков"""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.conn: Optional[asyncpg.Connection] = None

    async def connect(self):
        """Подключение к базе данных"""
        self.conn = await asyncpg.connect(self.db_url)
        logger.info("✅ Connected to database")

    async def close(self):
        """Закрытие соединения"""
        if self.conn:
            await self.conn.close()
            logger.info("🔌 Database connection closed")

    async def check_consistency(self) -> Dict[str, any]:
        """
        Проверка консистентности всех счетчиков

        Returns:
            {
                'total_users': int,
                'consistent_users': int,
                'inconsistent_users': int,
                'max_drift': int,
                'issues': List[Dict]
            }
        """

        logger.info("🔍 Checking counter consistency...")

        query = """
            SELECT
                us.user_id,
                us.total_answers_lifetime as stats_count,
                COALESCE(actual.answer_count, 0) as actual_count,
                COALESCE(dp.total_answers_analyzed, 0) as personality_count,
                ABS(us.total_answers_lifetime - COALESCE(actual.answer_count, 0)) as drift
            FROM selfology.user_stats us
            LEFT JOIN (
                SELECT os.user_id, COUNT(ua.id) as answer_count
                FROM selfology.user_answers_new ua
                JOIN selfology.onboarding_sessions os ON ua.session_id = os.id
                GROUP BY os.user_id
            ) actual ON us.user_id = actual.user_id
            LEFT JOIN selfology.digital_personality dp ON us.user_id = dp.user_id
            WHERE us.total_answers_lifetime != COALESCE(actual.answer_count, 0)
                OR us.total_answers_lifetime != COALESCE(dp.total_answers_analyzed, 0)
            ORDER BY drift DESC
        """

        rows = await self.conn.fetch(query)

        # Подсчитываем общую статистику
        total_users_query = "SELECT COUNT(*) FROM selfology.user_stats"
        total_users = await self.conn.fetchval(total_users_query)

        inconsistent_users = len(rows)
        consistent_users = total_users - inconsistent_users

        issues = []
        max_drift = 0

        for row in rows:
            drift = row['drift']
            if drift > max_drift:
                max_drift = drift

            issues.append({
                'user_id': row['user_id'],
                'stats_count': row['stats_count'],
                'actual_count': row['actual_count'],
                'personality_count': row['personality_count'],
                'drift': drift
            })

        result = {
            'total_users': total_users,
            'consistent_users': consistent_users,
            'inconsistent_users': inconsistent_users,
            'max_drift': max_drift,
            'issues': issues
        }

        # Вывод отчета
        logger.info(f"📊 CONSISTENCY REPORT:")
        logger.info(f"  Total users: {total_users}")
        logger.info(f"  ✅ Consistent: {consistent_users} ({consistent_users/total_users*100:.1f}%)")
        logger.info(f"  ❌ Inconsistent: {inconsistent_users} ({inconsistent_users/total_users*100:.1f}%)")
        logger.info(f"  📉 Max drift: {max_drift}")

        if inconsistent_users > 0:
            logger.warning(f"⚠️  Found {inconsistent_users} users with inconsistent counters!")
            for issue in issues[:5]:  # Показываем первые 5
                logger.warning(
                    f"  User {issue['user_id']}: "
                    f"stats={issue['stats_count']}, "
                    f"actual={issue['actual_count']}, "
                    f"personality={issue['personality_count']} "
                    f"(drift={issue['drift']})"
                )
        else:
            logger.info("✅ All counters are consistent!")

        return result

    async def repair_counters(self, dry_run: bool = False) -> int:
        """
        Автоматическое исправление несогласованных счетчиков

        Args:
            dry_run: Если True, только показывает что будет исправлено

        Returns:
            Количество исправленных пользователей
        """

        logger.info("🔧 Repairing inconsistent counters...")

        if dry_run:
            logger.info("🔍 DRY RUN MODE - no changes will be made")

        # Получаем список проблемных пользователей
        issues = (await self.check_consistency())['issues']

        if not issues:
            logger.info("✅ No repairs needed!")
            return 0

        repaired_count = 0

        for issue in issues:
            user_id = issue['user_id']
            actual_count = issue['actual_count']

            if dry_run:
                logger.info(
                    f"  Would repair user {user_id}: "
                    f"{issue['stats_count']} → {actual_count}"
                )
            else:
                # Исправляем user_stats
                await self.conn.execute("""
                    UPDATE selfology.user_stats
                    SET
                        total_answers_lifetime = $2,
                        updated_at = NOW()
                    WHERE user_id = $1
                """, user_id, actual_count)

                # Исправляем digital_personality (если существует)
                await self.conn.execute("""
                    UPDATE selfology.digital_personality
                    SET
                        total_answers_analyzed = $2,
                        last_updated = NOW()
                    WHERE user_id = $1
                """, user_id, actual_count)

                logger.info(
                    f"  ✅ Repaired user {user_id}: "
                    f"{issue['stats_count']} → {actual_count}"
                )

            repaired_count += 1

        if not dry_run:
            logger.info(f"✅ Successfully repaired {repaired_count} users!")
        else:
            logger.info(f"🔍 Would repair {repaired_count} users")

        return repaired_count

    async def get_trigger_stats(self) -> Dict[str, any]:
        """
        Получить статистику работы триггеров

        Returns:
            Статистика триггеров и производительности
        """

        logger.info("📊 Fetching trigger statistics...")

        # Проверка существования триггера
        trigger_check = await self.conn.fetchrow("""
            SELECT
                tgname as trigger_name,
                tgenabled as enabled,
                proname as function_name
            FROM pg_trigger t
            JOIN pg_proc p ON t.tgfoid = p.oid
            WHERE t.tgname = 'update_all_answer_counters_trigger'
                OR t.tgname = 'update_user_stats_trigger'
        """)

        if not trigger_check:
            logger.error("❌ No counter update trigger found!")
            return {
                'trigger_exists': False,
                'trigger_name': None,
                'enabled': False
            }

        trigger_name = trigger_check['trigger_name']
        enabled = trigger_check['enabled'] == 'O'  # 'O' = enabled
        function_name = trigger_check['function_name']

        logger.info(f"  Trigger: {trigger_name}")
        logger.info(f"  Function: {function_name}")
        logger.info(f"  Status: {'✅ Enabled' if enabled else '❌ Disabled'}")

        # Статистика вставок (приблизительная производительность)
        recent_inserts = await self.conn.fetchval("""
            SELECT COUNT(*)
            FROM selfology.user_answers_new
            WHERE answered_at > NOW() - INTERVAL '1 hour'
        """)

        logger.info(f"  Recent inserts (1h): {recent_inserts}")

        # Проверка advisory locks (активные блокировки)
        active_locks = await self.conn.fetch("""
            SELECT
                locktype,
                objid,
                mode,
                granted
            FROM pg_locks
            WHERE locktype = 'advisory'
        """)

        logger.info(f"  Active advisory locks: {len(active_locks)}")

        return {
            'trigger_exists': True,
            'trigger_name': trigger_name,
            'function_name': function_name,
            'enabled': enabled,
            'recent_inserts_1h': recent_inserts,
            'active_advisory_locks': len(active_locks)
        }

    async def benchmark_trigger_performance(self, iterations: int = 100) -> Dict[str, float]:
        """
        Бенчмарк производительности триггера

        Args:
            iterations: Количество тестовых вставок

        Returns:
            Статистика производительности
        """

        logger.info(f"⚡ Benchmarking trigger performance ({iterations} iterations)...")

        # Создаем тестовую сессию
        test_user_id = 999999  # Тестовый пользователь
        session_id = await self.conn.fetchval("""
            INSERT INTO selfology.onboarding_sessions (user_id, status)
            VALUES ($1, 'active')
            RETURNING id
        """, test_user_id)

        start_time = datetime.now()

        # Вставляем тестовые ответы
        for i in range(iterations):
            await self.conn.execute("""
                INSERT INTO selfology.user_answers_new (session_id, question_json_id, raw_answer)
                VALUES ($1, $2, $3)
            """, session_id, f"TEST_{i}", f"Test answer {i}")

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Очищаем тестовые данные
        await self.conn.execute("""
            DELETE FROM selfology.onboarding_sessions
            WHERE user_id = $1
        """, test_user_id)

        await self.conn.execute("""
            DELETE FROM selfology.user_stats
            WHERE user_id = $1
        """, test_user_id)

        avg_time_ms = (duration / iterations) * 1000
        throughput = iterations / duration

        logger.info(f"  Total time: {duration:.2f}s")
        logger.info(f"  Average time per insert: {avg_time_ms:.2f}ms")
        logger.info(f"  Throughput: {throughput:.1f} inserts/sec")

        return {
            'total_time_sec': duration,
            'avg_time_ms': avg_time_ms,
            'throughput_per_sec': throughput,
            'iterations': iterations
        }


async def main():
    """Главная функция CLI"""
    import sys

    # Конфигурация подключения к БД
    DB_URL = "postgresql://postgres:sS67wM+1zMBRFHAW4kj9HwFl5J6+veo7Nirx0/I+oiU=@localhost:5432/n8n"

    checker = CounterHealthChecker(DB_URL)
    await checker.connect()

    try:
        command = sys.argv[1] if len(sys.argv) > 1 else 'check'

        if command == 'check':
            await checker.check_consistency()

        elif command == 'repair':
            dry_run = '--dry-run' in sys.argv
            await checker.repair_counters(dry_run=dry_run)

        elif command == 'stats':
            await checker.get_trigger_stats()

        elif command == 'benchmark':
            iterations = int(sys.argv[2]) if len(sys.argv) > 2 else 100
            await checker.benchmark_trigger_performance(iterations)

        else:
            print(f"Unknown command: {command}")
            print("Available commands: check, repair, stats, benchmark")

    finally:
        await checker.close()


if __name__ == '__main__':
    asyncio.run(main())
