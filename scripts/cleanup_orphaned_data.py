#!/usr/bin/env python3
"""
Очистка orphaned данных в БД

Удаляет:
1. Ответы помеченные как 'analyzed' но без реального AI анализа
2. Старые abandoned сессии
"""

import asyncio
import asyncpg
from datetime import datetime

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "n8n",
    "password": "sS67wM+1zMBRFHAW4kj9HwFl5J6+veo7Nirx0/I+oiU=",
    "database": "n8n"
}


async def cleanup_orphaned_answers(conn, dry_run=True):
    """Удалить ответы без анализа"""

    print("\n🧹 ОЧИСТКА ORPHANED ANSWERS")
    print("="*60)

    # Найти orphaned answers
    orphaned = await conn.fetch("""
        SELECT ua.id, ua.question_json_id, ua.analysis_status, ua.answered_at
        FROM selfology.user_answers_new ua
        LEFT JOIN selfology.answer_analysis aa ON ua.id = aa.user_answer_id
        WHERE ua.analysis_status IN ('analyzed', 'completed')
          AND aa.id IS NULL
        ORDER BY ua.id
    """)

    if not orphaned:
        print("✅ Orphaned answers не найдены")
        return 0

    print(f"📊 Найдено orphaned answers: {len(orphaned)}")
    for row in orphaned[:10]:  # Показываем первые 10
        print(f"  - ID {row['id']}: {row['question_json_id']}, статус={row['analysis_status']}")

    if len(orphaned) > 10:
        print(f"  ... и еще {len(orphaned) - 10}")

    if dry_run:
        print("\n⚠️ DRY RUN MODE - данные НЕ будут удалены")
        print(f"Будет удалено: {len(orphaned)} записей")
        return len(orphaned)

    # Удаляем
    deleted = await conn.execute("""
        DELETE FROM selfology.user_answers_new ua
        USING (
            SELECT ua.id
            FROM selfology.user_answers_new ua
            LEFT JOIN selfology.answer_analysis aa ON ua.id = aa.user_answer_id
            WHERE ua.analysis_status IN ('analyzed', 'completed')
              AND aa.id IS NULL
        ) AS orphaned
        WHERE ua.id = orphaned.id
    """)

    count = int(deleted.split()[-1])
    print(f"✅ Удалено orphaned answers: {count}")
    return count


async def cleanup_abandoned_sessions(conn, dry_run=True):
    """Удалить старые abandoned сессии без ответов"""

    print("\n🧹 ОЧИСТКА ABANDONED SESSIONS")
    print("="*60)

    # Найти пустые abandoned сессии
    empty_sessions = await conn.fetch("""
        SELECT os.id, os.started_at, os.status, COUNT(ua.id) as answers_count
        FROM selfology.onboarding_sessions os
        LEFT JOIN selfology.user_answers_new ua ON os.id = ua.session_id
        WHERE os.status = 'abandoned'
        GROUP BY os.id, os.started_at, os.status
        HAVING COUNT(ua.id) = 0
        ORDER BY os.started_at
    """)

    if not empty_sessions:
        print("✅ Пустые abandoned сессии не найдены")
        return 0

    print(f"📊 Найдено пустых abandoned сессий: {len(empty_sessions)}")
    for row in empty_sessions[:5]:
        print(f"  - Session #{row['id']}: {row['started_at']}, answers={row['answers_count']}")

    if dry_run:
        print("\n⚠️ DRY RUN MODE - данные НЕ будут удалены")
        print(f"Будет удалено: {len(empty_sessions)} сессий")
        return len(empty_sessions)

    # Удаляем
    session_ids = [row['id'] for row in empty_sessions]
    deleted = await conn.execute("""
        DELETE FROM selfology.onboarding_sessions
        WHERE id = ANY($1::int[])
    """, session_ids)

    count = int(deleted.split()[-1])
    print(f"✅ Удалено пустых сессий: {count}")
    return count


async def reset_pending_statuses(conn, dry_run=True):
    """Сбросить статус 'pending' на ответах без анализа"""

    print("\n🔄 СБРОС PENDING СТАТУСОВ")
    print("="*60)

    # Найти ответы в pending без анализа
    pending = await conn.fetch("""
        SELECT ua.id, ua.question_json_id, ua.analysis_status
        FROM selfology.user_answers_new ua
        LEFT JOIN selfology.answer_analysis aa ON ua.id = aa.user_answer_id
        WHERE ua.analysis_status = 'pending'
          AND aa.id IS NULL
    """)

    if not pending:
        print("✅ Pending ответы корректны")
        return 0

    print(f"📊 Найдено pending ответов без анализа: {len(pending)}")

    if dry_run:
        print("\n⚠️ DRY RUN MODE")
        return len(pending)

    # Они уже pending, ничего не делаем
    print("✅ Статусы корректны")
    return 0


async def show_final_stats(conn):
    """Показать итоговую статистику"""

    print("\n📊 ИТОГОВАЯ СТАТИСТИКА")
    print("="*60)

    stats = await conn.fetchrow("""
        SELECT
            COUNT(DISTINCT os.id) as total_sessions,
            COUNT(ua.id) as total_answers,
            COUNT(DISTINCT ua.question_json_id) as unique_questions,
            COUNT(aa.id) as answers_with_analysis,
            COUNT(ua.id) - COUNT(aa.id) as answers_without_analysis,
            COUNT(*) FILTER (WHERE os.status = 'active') as active_sessions,
            COUNT(*) FILTER (WHERE os.status = 'completed') as completed_sessions,
            COUNT(*) FILTER (WHERE os.status = 'abandoned') as abandoned_sessions
        FROM selfology.onboarding_sessions os
        LEFT JOIN selfology.user_answers_new ua ON os.id = ua.session_id
        LEFT JOIN selfology.answer_analysis aa ON ua.id = aa.user_answer_id
        WHERE os.user_id = 98005572
    """)

    print(f"Всего сессий:              {stats['total_sessions']}")
    print(f"  - Active:                {stats['active_sessions']}")
    print(f"  - Completed:             {stats['completed_sessions']}")
    print(f"  - Abandoned:             {stats['abandoned_sessions']}")
    print(f"\nВсего ответов:             {stats['total_answers']}")
    print(f"Уникальных вопросов:       {stats['unique_questions']}")
    print(f"С анализом:                {stats['answers_with_analysis']}")
    print(f"Без анализа:               {stats['answers_without_analysis']}")


async def main():
    """Точка входа"""

    print("\n" + "🧹"*30)
    print("ОЧИСТКА ДАННЫХ SELFOLOGY")
    print("🧹"*30)

    print("\n⚠️ РЕЖИМ: DRY RUN")
    print("Данные НЕ будут изменены, только показан отчет")
    print("\nДля реального удаления запустите: python cleanup_orphaned_data.py --execute")

    conn = await asyncpg.connect(**DB_CONFIG)

    try:
        # Показываем что будет очищено
        orphaned_count = await cleanup_orphaned_answers(conn, dry_run=True)
        empty_sessions_count = await cleanup_abandoned_sessions(conn, dry_run=True)
        pending_count = await reset_pending_statuses(conn, dry_run=True)

        print("\n" + "="*60)
        print("📋 SUMMARY")
        print("="*60)
        print(f"Orphaned answers для удаления:  {orphaned_count}")
        print(f"Пустые сессии для удаления:     {empty_sessions_count}")
        print(f"Pending для проверки:           {pending_count}")

        # Показываем текущую статистику
        await show_final_stats(conn)

        print("\n" + "="*60)
        print("💡 ДЛЯ ВЫПОЛНЕНИЯ ОЧИСТКИ:")
        print("python scripts/cleanup_orphaned_data.py --execute")
        print("="*60)

    finally:
        await conn.close()


async def execute_cleanup():
    """Выполнить реальную очистку"""

    print("\n" + "🧹"*30)
    print("ВЫПОЛНЕНИЕ ОЧИСТКИ ДАННЫХ")
    print("🧹"*30)

    conn = await asyncpg.connect(**DB_CONFIG)

    try:
        # Выполняем очистку
        orphaned_count = await cleanup_orphaned_answers(conn, dry_run=False)
        empty_sessions_count = await cleanup_abandoned_sessions(conn, dry_run=False)

        print("\n" + "="*60)
        print("✅ ОЧИСТКА ЗАВЕРШЕНА")
        print("="*60)
        print(f"Удалено orphaned answers:  {orphaned_count}")
        print(f"Удалено пустых сессий:     {empty_sessions_count}")

        # Показываем новую статистику
        await show_final_stats(conn)

    finally:
        await conn.close()


if __name__ == "__main__":
    import sys

    if "--execute" in sys.argv:
        print("\n⚠️⚠️⚠️ РЕЖИМ ВЫПОЛНЕНИЯ ⚠️⚠️⚠️")
        print("Данные БУДУТ удалены!")
        print("\nБудет удалено:")
        print("- 25 orphaned answers")
        print("- 17 пустых abandoned сессий")

        confirm = input("\nВы уверены? Введите 'YES' для подтверждения: ")
        if confirm == "YES":
            asyncio.run(execute_cleanup())
        else:
            print("❌ Отменено")
    else:
        asyncio.run(main())
