#!/usr/bin/env python3
"""
Тестирование создания векторов в Qdrant

Использует анализ #65 с корректным personality_summary
"""

import asyncio
import asyncpg
import aiohttp
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from selfology_bot.analysis.embedding_creator import EmbeddingCreator

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "n8n",
    "password": "sS67wM+1zMBRFHAW4kj9HwFl5J6+veo7Nirx0/I+oiU=",
    "database": "n8n"
}

QDRANT_URL = "http://localhost:6333"


async def check_vectors_before():
    """Проверка количества векторов ДО создания"""

    print("\n📊 Векторы в Qdrant ДО теста:")
    print("="*60)

    counts = {}
    # ✅ ИСПРАВЛЕНО: используем РЕАЛЬНЫЕ имена коллекций из embedding_creator.py
    collections = ["quick_match", "personality_profiles", "personality_evolution"]

    async with aiohttp.ClientSession() as session:
        for collection in collections:
            try:
                async with session.get(f"{QDRANT_URL}/collections/{collection}") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        count = data["result"]["points_count"]
                        counts[collection] = count
                        print(f"  {collection}: {count} vectors")
                    else:
                        print(f"  {collection}: ERROR (status {resp.status})")
                        counts[collection] = 0
            except Exception as e:
                print(f"  {collection}: ERROR ({e})")
                counts[collection] = 0

    return counts


async def get_analysis_data(analysis_id: int):
    """Получить данные анализа из БД"""

    print(f"\n🔍 Загрузка анализа #{analysis_id}...")
    print("="*60)

    conn = await asyncpg.connect(**DB_CONFIG)

    try:
        row = await conn.fetchrow("""
            SELECT
                aa.id,
                aa.user_answer_id,
                aa.raw_ai_response,
                ua.session_id,
                os.user_id
            FROM selfology.answer_analysis aa
            JOIN selfology.user_answers_new ua ON aa.user_answer_id = ua.id
            JOIN selfology.onboarding_sessions os ON ua.session_id = os.id
            WHERE aa.id = $1
        """, analysis_id)

        if not row:
            print(f"❌ Анализ #{analysis_id} не найден")
            return None

        # Парсим JSON
        analysis_result = row['raw_ai_response']
        if isinstance(analysis_result, str):
            analysis_result = json.loads(analysis_result)

        print(f"✅ Найден анализ для пользователя {row['user_id']}")
        print(f"📋 Ключи в analysis_result: {list(analysis_result.keys())}")

        # Проверяем personality_summary
        if "personality_summary" in analysis_result:
            summary = analysis_result["personality_summary"]
            print(f"\n✅ personality_summary найден:")
            print(f"  - nano: {summary.get('nano', 'N/A')[:60]}...")
            print(f"  - narrative: {summary.get('narrative', 'N/A')[:60]}...")
            print(f"  - embedding_prompt: {summary.get('embedding_prompt', 'N/A')[:60]}...")
        else:
            print(f"\n❌ personality_summary ОТСУТСТВУЕТ!")
            return None

        return {
            "user_id": row['user_id'],
            "analysis_result": analysis_result
        }

    finally:
        await conn.close()


async def create_vectors(user_id: int, analysis_result: dict):
    """Создать векторы через EmbeddingCreator"""

    print(f"\n🧬 Создание векторов для пользователя {user_id}...")
    print("="*60)

    try:
        creator = EmbeddingCreator()

        # 🔍 ДИАГНОСТИКА: Проверяем инициализацию Qdrant client
        print(f"\n🔍 ДИАГНОСТИКА EmbeddingCreator:")
        print(f"  - Qdrant client initialized: {creator.qdrant_client is not None}")
        if creator.qdrant_client:
            print(f"  - Qdrant client type: {type(creator.qdrant_client)}")
        else:
            print(f"  ❌ Qdrant client is None - векторы НЕ будут созданы!")

        success = await creator.create_personality_vector(
            user_id=user_id,
            analysis_result=analysis_result,
            is_update=False
        )

        if success:
            print("✅ EmbeddingCreator вернул success=True")
            return True
        else:
            print("❌ EmbeddingCreator вернул success=False")
            return False

    except Exception as e:
        print(f"❌ Ошибка при создании векторов: {e}")
        import traceback
        traceback.print_exc()
        return False


async def check_vectors_after():
    """Проверка количества векторов ПОСЛЕ создания"""

    print("\n📊 Векторы в Qdrant ПОСЛЕ теста:")
    print("="*60)

    counts = {}
    # ✅ ИСПРАВЛЕНО: используем РЕАЛЬНЫЕ имена коллекций из embedding_creator.py
    collections = ["quick_match", "personality_profiles", "personality_evolution"]

    async with aiohttp.ClientSession() as session:
        for collection in collections:
            try:
                async with session.get(f"{QDRANT_URL}/collections/{collection}") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        count = data["result"]["points_count"]
                        counts[collection] = count
                        print(f"  {collection}: {count} vectors")
                    else:
                        print(f"  {collection}: ERROR (status {resp.status})")
                        counts[collection] = 0
            except Exception as e:
                print(f"  {collection}: ERROR ({e})")
                counts[collection] = 0

    return counts


async def main():
    """Точка входа"""

    print("\n" + "🧬"*30)
    print("ТЕСТИРОВАНИЕ СОЗДАНИЯ ВЕКТОРОВ В QDRANT")
    print("🧬"*30)

    # 1. Проверяем векторы ДО
    counts_before = await check_vectors_before()

    # 2. Загружаем данные анализа
    data = await get_analysis_data(65)

    if not data:
        print("\n❌ Не удалось загрузить данные анализа")
        return 1

    # 3. Создаем векторы
    success = await create_vectors(data["user_id"], data["analysis_result"])

    # 4. Даем время на сохранение
    await asyncio.sleep(2)

    # 5. Проверяем векторы ПОСЛЕ
    counts_after = await check_vectors_after()

    # 6. Анализируем результаты
    print("\n" + "="*60)
    print("📈 РЕЗУЛЬТАТЫ")
    print("="*60)

    total_before = sum(counts_before.values())
    total_after = sum(counts_after.values())
    added = total_after - total_before

    print(f"\nВекторов ДО:     {total_before}")
    print(f"Векторов ПОСЛЕ:  {total_after}")
    print(f"Добавлено:       {added}")

    for collection in counts_before.keys():
        before = counts_before.get(collection, 0)
        after = counts_after.get(collection, 0)
        diff = after - before
        if diff > 0:
            print(f"\n✅ {collection}: +{diff} vectors")

    print("\n" + "="*60)
    if added > 0:
        print("🎉 УСПЕХ! Векторы созданы в Qdrant!")
        print("="*60)
        return 0
    else:
        print("❌ ОШИБКА! Векторы НЕ созданы")
        print("="*60)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
