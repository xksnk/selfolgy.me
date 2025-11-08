#!/usr/bin/env python3
"""
Скрипт синхронизации и валидации счетчиков ответов

Использование:
    # Проверка здоровья счетчиков
    python scripts/sync_answer_counters.py --check

    # Автоматическая коррекция критических случаев
    python scripts/sync_answer_counters.py --fix-critical

    # Полная валидация всех пользователей
    python scripts/sync_answer_counters.py --validate-all

    # Пересчет для конкретного пользователя
    python scripts/sync_answer_counters.py --recalculate --user-id 98005572

    # Мониторинг в реальном времени
    python scripts/sync_answer_counters.py --monitor
"""

import asyncio
import asyncpg
import sys
import argparse
from datetime import datetime
from typing import List, Dict, Any
import os

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "n8n",
    "password": "sS67wM+1zMBRFHAW4kj9HwFl5J6+veo7Nirx0/I+oiU=",
    "database": "n8n"
}


class CounterSyncManager:
    """Менеджер синхронизации счетчиков ответов"""

    def __init__(self):
        self.conn = None

    async def connect(self):
        """Подключение к БД"""
        self.conn = await asyncpg.connect(**DB_CONFIG)
        print("✅ Подключение к PostgreSQL установлено")

    async def close(self):
        """Закрытие подключения"""
        if self.conn:
            await self.conn.close()
            print("✅ Подключение к PostgreSQL закрыто")

    async def check_health(self) -> List[Dict[str, Any]]:
        """
        Проверка здоровья счетчиков

        Returns:
            Список пользователей с информацией о здоровье счетчиков
        """
        print("\n🔍 ПРОВЕРКА ЗДОРОВЬЯ СЧЕТЧИКОВ\n" + "="*60)

        rows = await self.conn.fetch("""
            SELECT
                user_id,
                stored_count,
                actual_count,
                drift,
                health_status,
                last_sync
            FROM selfology.answer_counter_health
            ORDER BY ABS(drift) DESC
            LIMIT 20
        """)

        if not rows:
            print("✅ Нет данных для проверки")
            return []

        results = []
        for row in rows:
            status_icon = {
                'SYNCED': '✅',
                'ACCEPTABLE': '⚠️',
                'CRITICAL': '❌'
            }.get(row['health_status'], '❓')

            print(f"{status_icon} User {row['user_id']}: "
                  f"stored={row['stored_count']}, actual={row['actual_count']}, "
                  f"drift={row['drift']:+d}, status={row['health_status']}")

            results.append(dict(row))

        # Статистика
        total = len(results)
        synced = sum(1 for r in results if r['health_status'] == 'SYNCED')
        acceptable = sum(1 for r in results if r['health_status'] == 'ACCEPTABLE')
        critical = sum(1 for r in results if r['health_status'] == 'CRITICAL')

        print("\n📊 СТАТИСТИКА:")
        print(f"   Всего проверено: {total}")
        print(f"   ✅ В синхронизации: {synced} ({synced/total*100:.1f}%)")
        print(f"   ⚠️  Приемлемый дрифт: {acceptable} ({acceptable/total*100:.1f}%)")
        print(f"   ❌ Критический дрифт: {critical} ({critical/total*100:.1f}%)")

        return results

    async def fix_critical(self) -> List[Dict[str, Any]]:
        """
        Автоматическая коррекция критических случаев

        Returns:
            Список исправленных записей
        """
        print("\n🔧 АВТОМАТИЧЕСКАЯ КОРРЕКЦИЯ КРИТИЧЕСКИХ СЛУЧАЕВ\n" + "="*60)

        rows = await self.conn.fetch("""
            SELECT * FROM selfology.auto_fix_critical_drift()
        """)

        if not rows:
            print("✅ Критических случаев не найдено")
            return []

        results = []
        for row in rows:
            print(f"✅ User {row['user_id']}: "
                  f"{row['old_count']} → {row['new_count']} "
                  f"(исправлено {abs(row['old_count'] - row['new_count'])})")
            results.append(dict(row))

        print(f"\n📊 Исправлено записей: {len(results)}")
        return results

    async def validate_all(self) -> List[Dict[str, Any]]:
        """
        Полная валидация всех пользователей

        Returns:
            Список результатов валидации
        """
        print("\n🔄 ПОЛНАЯ ВАЛИДАЦИЯ СЧЕТЧИКОВ\n" + "="*60)

        rows = await self.conn.fetch("""
            SELECT * FROM selfology.validate_all_answer_counters()
        """)

        if not rows:
            print("✅ Нет данных для валидации")
            return []

        results = []
        corrected_count = 0

        for row in rows:
            icon = "✅" if not row['corrected'] else "🔧"
            print(f"{icon} User {row['user_id']}: "
                  f"stored={row['stored_count']}, actual={row['actual_count']}, "
                  f"drift={row['drift']:+d}, "
                  f"{'ИСПРАВЛЕНО' if row['corrected'] else 'OK'}")

            if row['corrected']:
                corrected_count += 1

            results.append(dict(row))

        print(f"\n📊 ИТОГИ:")
        print(f"   Проверено: {len(results)}")
        print(f"   Исправлено: {corrected_count}")
        print(f"   Без изменений: {len(results) - corrected_count}")

        return results

    async def recalculate_user(self, user_id: int) -> int:
        """
        Пересчет счетчика для конкретного пользователя

        Args:
            user_id: ID пользователя

        Returns:
            Новое значение счетчика
        """
        print(f"\n🔄 ПЕРЕСЧЕТ СЧЕТЧИКА ДЛЯ ПОЛЬЗОВАТЕЛЯ {user_id}\n" + "="*60)

        # Получаем текущее значение
        old_count = await self.conn.fetchval("""
            SELECT total_answers_lifetime
            FROM selfology.user_stats
            WHERE user_id = $1
        """, user_id)

        # Пересчитываем
        new_count = await self.conn.fetchval("""
            SELECT selfology.recalculate_answer_count($1)
        """, user_id)

        if old_count is None:
            print(f"ℹ️  Пользователь {user_id} не найден в user_stats")
            print(f"✅ Создана запись с count={new_count}")
        elif old_count == new_count:
            print(f"✅ Счетчик корректен: {new_count}")
        else:
            drift = old_count - new_count
            print(f"🔧 Исправлено: {old_count} → {new_count} (drift: {drift:+d})")

        return new_count

    async def monitor(self, interval: int = 30):
        """
        Мониторинг в реальном времени

        Args:
            interval: Интервал между проверками в секундах
        """
        print(f"\n👁️  МОНИТОРИНГ СЧЕТЧИКОВ (интервал: {interval}s)")
        print("Нажмите Ctrl+C для остановки\n")

        try:
            while True:
                # Получаем сводку
                summary = await self.conn.fetchrow("""
                    SELECT
                        COUNT(*) as total_users,
                        COUNT(*) FILTER (WHERE health_status = 'SYNCED') as synced,
                        COUNT(*) FILTER (WHERE health_status = 'ACCEPTABLE') as acceptable,
                        COUNT(*) FILTER (WHERE health_status = 'CRITICAL') as critical,
                        MAX(ABS(drift)) as max_drift
                    FROM selfology.answer_counter_health
                """)

                timestamp = datetime.now().strftime('%H:%M:%S')
                print(f"[{timestamp}] "
                      f"Users: {summary['total_users']} | "
                      f"✅ {summary['synced']} | "
                      f"⚠️  {summary['acceptable']} | "
                      f"❌ {summary['critical']} | "
                      f"Max drift: {summary['max_drift'] or 0}")

                # Если есть критические - показываем
                if summary['critical'] > 0:
                    critical_users = await self.conn.fetch("""
                        SELECT user_id, drift
                        FROM selfology.answer_counter_health
                        WHERE health_status = 'CRITICAL'
                        LIMIT 5
                    """)
                    print(f"   ❌ Критические: {', '.join(f'User {r['user_id']} (drift: {r['drift']:+d})' for r in critical_users)}")

                await asyncio.sleep(interval)

        except KeyboardInterrupt:
            print("\n\n🛑 Мониторинг остановлен")


async def main():
    parser = argparse.ArgumentParser(
        description='Синхронизация и валидация счетчиков ответов',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('--check', action='store_true',
                       help='Проверить здоровье счетчиков')
    parser.add_argument('--fix-critical', action='store_true',
                       help='Исправить критические случаи')
    parser.add_argument('--validate-all', action='store_true',
                       help='Полная валидация всех пользователей')
    parser.add_argument('--recalculate', action='store_true',
                       help='Пересчитать счетчик для пользователя')
    parser.add_argument('--user-id', type=int,
                       help='ID пользователя для пересчета')
    parser.add_argument('--monitor', action='store_true',
                       help='Мониторинг в реальном времени')
    parser.add_argument('--interval', type=int, default=30,
                       help='Интервал мониторинга в секундах (default: 30)')

    args = parser.parse_args()

    # Если нет аргументов - показываем помощь
    if not any(vars(args).values()):
        parser.print_help()
        return

    manager = CounterSyncManager()

    try:
        await manager.connect()

        if args.check:
            await manager.check_health()

        if args.fix_critical:
            await manager.fix_critical()

        if args.validate_all:
            await manager.validate_all()

        if args.recalculate:
            if not args.user_id:
                print("❌ Ошибка: требуется --user-id для пересчета")
                return
            await manager.recalculate_user(args.user_id)

        if args.monitor:
            await manager.monitor(interval=args.interval)

    finally:
        await manager.close()


if __name__ == "__main__":
    asyncio.run(main())
