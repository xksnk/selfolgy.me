#!/usr/bin/env python3
"""
Скрипт для загрузки метаданных вопросов из JSON в таблицу questions_metadata

Загружает все вопросы из intelligent_question_core.json в таблицу
selfology.questions_metadata для управления флагами и админскими функциями.
"""

import asyncio
import json
import sys
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent))

from selfology_bot.database import DatabaseService


# Database config
DB_HOST = "localhost"
DB_PORT = 5432
DB_USER = "n8n"
DB_PASSWORD = "sS67wM+1zMBRFHAW4kj9HwFl5J6+veo7Nirx0/I+oiU="
DB_NAME = "n8n"
DB_SCHEMA = "selfology"


async def load_questions_from_json():
    """Загружает вопросы из JSON файла"""

    json_path = Path(__file__).parent.parent / "intelligent_question_core" / "data" / "selfology_intelligent_core.json"

    print(f"📖 Загружаю вопросы из {json_path}")

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    questions = data.get('questions', [])
    print(f"✅ Загружено {len(questions)} вопросов")

    return questions


async def populate_metadata(db: DatabaseService, questions: list):
    """Загружает метаданные вопросов в БД"""

    inserted = 0
    skipped = 0

    print(f"\n📝 Начинаю загрузку в selfology.questions_metadata...")

    async with db.get_connection() as conn:
        for question in questions:
            question_id = question.get('id')
            classification = question.get('classification', {})

            domain = classification.get('domain', 'UNKNOWN')
            depth_level = classification.get('depth_level', 'UNKNOWN')
            energy = classification.get('energy_dynamic', 'UNKNOWN')

            try:
                # Проверяем существует ли уже
                existing = await conn.fetchval(
                    "SELECT id FROM selfology.questions_metadata WHERE json_id = $1",
                    question_id
                )

                if existing:
                    skipped += 1
                    continue

                # Вставляем новую запись
                await conn.execute("""
                    INSERT INTO selfology.questions_metadata
                    (json_id, domain, depth_level, energy, is_flagged)
                    VALUES ($1, $2, $3, $4, false)
                """, question_id, domain, depth_level, energy)

                inserted += 1

                if inserted % 100 == 0:
                    print(f"   ✅ Загружено {inserted} вопросов...")

            except Exception as e:
                print(f"❌ Ошибка при загрузке {question_id}: {e}")

    print(f"\n🎉 Загрузка завершена!")
    print(f"   ✅ Вставлено: {inserted}")
    print(f"   ⏭️  Пропущено (уже существуют): {skipped}")
    print(f"   📊 Всего вопросов: {len(questions)}")


async def main():
    """Главная функция"""

    print("🚀 Загрузка метаданных вопросов в БД")
    print("=" * 50)

    # Инициализируем БД
    db = DatabaseService(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        schema=DB_SCHEMA
    )

    try:
        # Подключаемся к БД
        await db.initialize()
        print(f"✅ Подключено к БД: {DB_NAME}.{DB_SCHEMA}")

        # Загружаем вопросы из JSON
        questions = await load_questions_from_json()

        # Загружаем метаданные в БД
        await populate_metadata(db, questions)

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        raise
    finally:
        await db.close()
        print("\n✅ Соединение с БД закрыто")


if __name__ == "__main__":
    asyncio.run(main())
