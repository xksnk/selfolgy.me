#!/usr/bin/env python3
"""
Применение миграции 001 и заполнение таблиц данными из selfology_programs_v2.json

Использование:
    python scripts/migrations/apply_001_programs.py

Операции:
    1. Применяет SQL миграцию (создание таблиц)
    2. Загружает данные из JSON
    3. Заполняет таблицы программ, блоков, вопросов
    4. Выводит статистику
"""

import json
import asyncio
from pathlib import Path
import asyncpg


# Настройки подключения к БД (selfology)
DB_CONFIG = {
    'host': 'localhost',
    'port': 5434,
    'database': 'selfology',
    'user': 'selfology_user',
    'password': 'selfology_secure_2024'
}

# Пути к файлам
MIGRATION_SQL = Path('scripts/migrations/001_programs_structure.sql')
PROGRAMS_JSON = Path('intelligent_question_core/data/selfology_programs_v2.json')


async def apply_migration(conn: asyncpg.Connection) -> None:
    """Применить SQL миграцию"""
    print("📦 Применяю миграцию 001_programs_structure.sql...")

    sql = MIGRATION_SQL.read_text(encoding='utf-8')
    await conn.execute(sql)

    print("✅ Миграция применена успешно")


async def load_programs_data() -> dict:
    """Загрузить данные программ из JSON"""
    print(f"📄 Загружаю данные из {PROGRAMS_JSON}...")

    with open(PROGRAMS_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"✅ Загружено: {data['metadata']['total_programs']} программ, "
          f"{data['metadata']['total_blocks']} блоков, "
          f"{data['metadata']['total_questions']} вопросов")

    return data


async def insert_programs(conn: asyncpg.Connection, programs: list) -> int:
    """Вставить программы в БД"""
    print("📘 Вставляю программы...")

    count = 0
    for prog in programs:
        await conn.execute("""
            INSERT INTO selfology.onboarding_programs
            (program_id, name, status, priority)
            VALUES ($1, $2, 'active', $3)
            ON CONFLICT (program_id) DO UPDATE SET
                name = EXCLUDED.name,
                updated_at = NOW()
        """, prog['id'], prog['name'], count)
        count += 1

    print(f"✅ Вставлено {count} программ")
    return count


async def insert_blocks(conn: asyncpg.Connection, programs: list) -> int:
    """Вставить блоки в БД"""
    print("📦 Вставляю блоки...")

    count = 0
    for prog in programs:
        for block in prog['blocks']:
            metadata = block.get('block_metadata', {})

            await conn.execute("""
                INSERT INTO selfology.program_blocks
                (block_id, program_id, name, description, block_type, sequence,
                 base_journey_stage, base_depth_range, base_energy_dynamic,
                 base_safety_minimum, base_complexity_range, base_emotional_weight_range)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                ON CONFLICT (block_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    block_type = EXCLUDED.block_type
            """,
                block['id'],
                prog['id'],
                block['name'],
                block.get('description', ''),
                block['type'],
                block['sequence'],
                metadata.get('base_journey_stage'),
                json.dumps(metadata.get('base_depth_range', [])),
                metadata.get('base_energy_dynamic'),
                metadata.get('base_safety_minimum'),
                json.dumps(metadata.get('base_complexity_range', [])),
                json.dumps(metadata.get('base_emotional_weight_range', []))
            )
            count += 1

    print(f"✅ Вставлено {count} блоков")
    return count


async def insert_questions(conn: asyncpg.Connection, programs: list) -> int:
    """Вставить вопросы в БД"""
    print("❓ Вставляю вопросы...")

    count = 0
    for prog in programs:
        position_in_block = 0
        current_block = None

        for block in prog['blocks']:
            if current_block != block['id']:
                position_in_block = 0
                current_block = block['id']

            for q in block['questions']:
                position_in_block += 1

                # Определяем journey_stage из типа блока
                journey_stage_map = {
                    'Foundation': 'ENTRY',
                    'Exploration': 'EXPLORATION',
                    'Integration': 'INTEGRATION'
                }
                journey_stage = journey_stage_map.get(block['type'], 'EXPLORATION')

                await conn.execute("""
                    INSERT INTO selfology.program_questions
                    (question_id, block_id, program_id, position, position_in_block,
                     text, format, journey_stage, needs_human_review)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (question_id) DO UPDATE SET
                        text = EXCLUDED.text,
                        format = EXCLUDED.format,
                        updated_at = NOW()
                """,
                    q['id'],
                    block['id'],
                    prog['id'],
                    q['position'],
                    position_in_block,
                    q['text'],
                    q.get('format', 'both'),
                    journey_stage,
                    True  # Все вопросы требуют ревью пока нет AI метаданных
                )
                count += 1

    print(f"✅ Вставлено {count} вопросов")
    return count


async def verify_data(conn: asyncpg.Connection) -> None:
    """Проверить вставленные данные"""
    print("\n📊 Проверка данных...")

    # Количество программ
    programs_count = await conn.fetchval(
        "SELECT COUNT(*) FROM selfology.onboarding_programs"
    )

    # Количество блоков по типам
    blocks_by_type = await conn.fetch("""
        SELECT block_type, COUNT(*) as cnt
        FROM selfology.program_blocks
        GROUP BY block_type
        ORDER BY block_type
    """)

    # Количество вопросов по форматам
    questions_by_format = await conn.fetch("""
        SELECT format, COUNT(*) as cnt
        FROM selfology.program_questions
        GROUP BY format
        ORDER BY format
    """)

    # Общее количество вопросов
    total_questions = await conn.fetchval(
        "SELECT COUNT(*) FROM selfology.program_questions"
    )

    print(f"\n{'='*50}")
    print("📈 СТАТИСТИКА В БД:")
    print(f"{'='*50}")
    print(f"Программ: {programs_count}")
    print(f"\nБлоков по типам:")
    for row in blocks_by_type:
        print(f"  {row['block_type']}: {row['cnt']}")
    print(f"\nВопросов по форматам:")
    for row in questions_by_format:
        print(f"  {row['format']}: {row['cnt']}")
    print(f"\nВсего вопросов: {total_questions}")
    print(f"{'='*50}")


async def main():
    print("="*60)
    print("🚀 ПРИМЕНЕНИЕ МИГРАЦИИ 001: Блочная структура программ")
    print("="*60)

    # Проверка файлов
    if not MIGRATION_SQL.exists():
        print(f"❌ Файл миграции не найден: {MIGRATION_SQL}")
        return

    if not PROGRAMS_JSON.exists():
        print(f"❌ JSON файл не найден: {PROGRAMS_JSON}")
        return

    # Подключение к БД
    print(f"\n🔗 Подключаюсь к БД: {DB_CONFIG['database']}...")
    try:
        conn = await asyncpg.connect(**DB_CONFIG)
        print("✅ Подключение установлено")
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return

    try:
        # 1. Применяем миграцию
        await apply_migration(conn)

        # 2. Загружаем данные
        data = await load_programs_data()

        # 3. Вставляем данные в транзакции
        print("\n📝 Начинаю транзакцию...")
        async with conn.transaction():
            await insert_programs(conn, data['programs'])
            await insert_blocks(conn, data['programs'])
            await insert_questions(conn, data['programs'])

        print("✅ Транзакция завершена успешно")

        # 4. Проверяем данные
        await verify_data(conn)

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()
        print("\n🔒 Соединение закрыто")

    print("\n✅ Миграция завершена!")


if __name__ == '__main__':
    asyncio.run(main())
