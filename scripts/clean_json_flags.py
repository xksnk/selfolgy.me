#!/usr/bin/env python3
"""
Скрипт очистки JSON от runtime флагов

Удаляет поля needs_review, admin_flagged из всех вопросов в JSON
после миграции в PostgreSQL
"""

import json
import sys
from pathlib import Path
from datetime import datetime


def clean_json_flags():
    """Удалить runtime флаги из JSON"""

    print("🧹 Начинаю очистку JSON от runtime флагов\n")

    # Путь к JSON
    json_path = Path(__file__).parent.parent / "intelligent_question_core" / "data" / "selfology_intelligent_core.json"

    if not json_path.exists():
        print(f"❌ JSON файл не найден: {json_path}")
        return

    # Создаем бэкап
    backup_path = json_path.with_suffix(f'.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
    print(f"💾 Создаю бэкап: {backup_path.name}")

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    with open(backup_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ Бэкап создан\n")

    # Удаляем runtime поля
    runtime_fields = ['needs_review', 'admin_flagged', 'flagged_at', 'flagged_by']
    removed_count = 0
    cleaned_questions = []

    questions = data.get('questions', [])
    print(f"📖 Обрабатываю {len(questions)} вопросов...")

    for q in questions:
        had_flags = False
        for field in runtime_fields:
            if field in q:
                del q[field]
                had_flags = True

        if had_flags:
            removed_count += 1
            cleaned_questions.append(q['id'])

    # Сохраняем очищенный JSON
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n📊 Результаты:")
    print(f"  ✅ Очищено вопросов: {removed_count}")
    print(f"  📝 Удалено полей: {runtime_fields}")

    if cleaned_questions:
        print(f"\n🚩 Очищенные вопросы: {', '.join(cleaned_questions)}")

    print(f"\n✅ JSON очищен от runtime флагов!")
    print(f"💾 Оригинал сохранен: {backup_path.name}\n")


if __name__ == "__main__":
    clean_json_flags()
