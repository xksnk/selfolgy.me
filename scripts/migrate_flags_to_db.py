#!/usr/bin/env python3
"""
Скрипт миграции флагов на доработку из JSON в PostgreSQL

Цель: Перенести runtime флаги (needs_review, admin_flagged) из JSON
в таблицу questions_metadata согласно best practice "Database as Single Source of Truth"
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent))

from selfology_bot.database.service import DatabaseService
from selfology_bot.database.onboarding_dao import OnboardingDAO


async def migrate_flags():
    """Основная функция миграции"""

    print("🚀 Начинаем миграцию флагов из JSON в PostgreSQL\n")

    # Путь к JSON
    json_path = Path(__file__).parent.parent / "intelligent_question_core" / "data" / "selfology_intelligent_core.json"

    if not json_path.exists():
        print(f"❌ JSON файл не найден: {json_path}")
        return

    # 1. Читаем JSON
    print(f"📖 Читаю JSON: {json_path}")
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    questions = data.get('questions', [])
    print(f"✅ Загружено {len(questions)} вопросов\n")

    # 2. Находим помеченные вопросы
    flagged_questions = []
    for q in questions:
        if q.get('needs_review', False) or q.get('admin_flagged', False):
            flagged_questions.append({
                'id': q['id'],
                'text': q['text'][:60] + '...',
                'needs_review': q.get('needs_review', False),
                'admin_flagged': q.get('admin_flagged', False)
            })

    print(f"🚩 Найдено {len(flagged_questions)} помеченных вопросов:")
    for fq in flagged_questions:
        print(f"  • {fq['id']}: {fq['text']}")
    print()

    if not flagged_questions:
        print("✅ Нет вопросов для миграции")
        return

    # 3. Подключаемся к БД
    print("🔌 Подключаюсь к базе данных...")

    # Используем параметры из n8n PostgreSQL
    db_service = DatabaseService(
        host='localhost',
        port=5432,
        user='n8n',
        password='sS67wM+1zMBRFHAW4kj9HwFl5J6+veo7Nirx0/I+oiU=',
        database='n8n',
        schema='selfology'
    )
    await db_service.initialize()

    dao = OnboardingDAO(db_service)

    # 4. Переносим флаги в БД
    print(f"\n💾 Переношу {len(flagged_questions)} флагов в БД...")

    migrated_count = 0
    failed_count = 0

    for fq in flagged_questions:
        question_id = fq['id']
        reason = "Migrated from JSON: needs_review=True (admin flagged before DB migration)"
        admin_id = 98005572  # Default admin

        success = await dao.flag_question(question_id, reason, admin_id)

        if success:
            migrated_count += 1
            print(f"  ✅ {question_id} → БД")
        else:
            failed_count += 1
            print(f"  ❌ {question_id} → Ошибка")

    print(f"\n📊 Результаты миграции:")
    print(f"  ✅ Успешно: {migrated_count}")
    print(f"  ❌ Ошибок: {failed_count}")

    # 5. Проверяем результат в БД
    print(f"\n🔍 Проверяю БД...")
    async with db_service.get_connection() as conn:
        rows = await conn.fetch("""
            SELECT json_id, is_flagged, flag_reason, flagged_at
            FROM selfology.questions_metadata
            WHERE is_flagged = true
            ORDER BY json_id
        """)

        print(f"✅ В БД найдено {len(rows)} помеченных вопросов:")
        for row in rows:
            print(f"  • {row['json_id']}: flagged_at={row['flagged_at']}")

    await db_service.close()

    print("\n" + "="*60)
    print("✅ МИГРАЦИЯ ЗАВЕРШЕНА!")
    print("="*60)
    print("\n📝 Следующие шаги:")
    print("  1. Запустить scripts/clean_json_flags.py для очистки JSON")
    print("  2. Изменить callback_flag_question для использования DAO")
    print("  3. Перезапустить бота\n")


if __name__ == "__main__":
    asyncio.run(migrate_flags())
