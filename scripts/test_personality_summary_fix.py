#!/usr/bin/env python3
"""
Тестирование исправления personality_summary

Проверяет:
1. AnswerAnalyzer создает personality_summary
2. Сохранение полного analysis_result в БД
3. EmbeddingCreator создает векторы
"""

import asyncio
import asyncpg
import sys
import os
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from selfology_bot.analysis.answer_analyzer import AnswerAnalyzer
from selfology_bot.analysis.embedding_creator import EmbeddingCreator

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "n8n",
    "password": "sS67wM+1zMBRFHAW4kj9HwFl5J6+veo7Nirx0/I+oiU=",
    "database": "n8n"
}

async def test_personality_summary_creation():
    """Тест 1: AnswerAnalyzer создает personality_summary"""

    print("\n" + "="*60)
    print("🧪 TEST 1: AnswerAnalyzer creates personality_summary")
    print("="*60)

    analyzer = AnswerAnalyzer()

    # Тестовый вопрос и ответ
    question_data = {
        "id": "test_001",
        "text": "Что самое главное было в вашем году?",
        "classification": {
            "domain": "IDENTITY",
            "depth_level": "CONSCIOUS",
            "energy_dynamic": "NEUTRAL"
        },
        "psychology": {
            "complexity": 0.6,
            "emotional_weight": 0.5,
            "insight_potential": 0.7,
            "trust_requirement": 0.4,
            "safety_level": 0.8
        }
    }

    user_answer = "Главным было понимание того, что я могу менять свою жизнь. Я начал заниматься спортом, улучшил отношения с семьей и нашел новое хобби."

    user_context = {
        "user_id": 98005572,
        "question_number": 5,
        "previous_domains": ["IDENTITY", "EMOTIONS"],
        "trust_level": 0.6,
        "energy_level": 0.7
    }

    # Запускаем анализ
    result = await analyzer.analyze_answer(question_data, user_answer, user_context)

    # Проверяем наличие personality_summary
    if "personality_summary" in result:
        print("✅ personality_summary СОЗДАН")
        summary = result["personality_summary"]

        required_keys = ["nano", "narrative", "embedding_prompt"]
        missing = [k for k in required_keys if k not in summary]

        if missing:
            print(f"❌ ПРОБЛЕМА: Отсутствуют ключи {missing}")
            return False
        else:
            print(f"✅ Все обязательные ключи присутствуют: {required_keys}")
            print(f"\n📝 personality_summary:")
            print(f"  - nano: {summary['nano'][:80]}...")
            print(f"  - narrative: {summary['narrative'][:80]}...")
            print(f"  - embedding_prompt: {summary['embedding_prompt'][:80]}...")
            return True
    else:
        print("❌ personality_summary НЕ создан")
        print(f"📋 Доступные ключи: {list(result.keys())}")
        return False


async def test_database_save(user_id: int = 98005572):
    """Тест 2: Проверка сохранения в БД"""

    print("\n" + "="*60)
    print("🧪 TEST 2: Database saves full analysis_result")
    print("="*60)

    conn = await asyncpg.connect(**DB_CONFIG)

    try:
        # Берем последний анализ пользователя
        last_analysis = await conn.fetchrow("""
            SELECT aa.id, aa.raw_ai_response
            FROM selfology.answer_analysis aa
            JOIN selfology.user_answers_new ua ON aa.user_answer_id = ua.id
            JOIN selfology.onboarding_sessions os ON ua.session_id = os.id
            WHERE os.user_id = $1
            ORDER BY aa.id DESC
            LIMIT 1
        """, user_id)

        if not last_analysis:
            print(f"⚠️ Нет анализов для пользователя {user_id}")
            return False

        analysis_id = last_analysis['id']
        raw_response = last_analysis['raw_ai_response']

        # PostgreSQL может вернуть JSON как строку
        if isinstance(raw_response, str):
            raw_response = json.loads(raw_response)

        print(f"\n📊 Анализ ID: {analysis_id}")
        print(f"📋 Ключи в raw_ai_response: {list(raw_response.keys())}")

        # Проверяем наличие personality_summary
        if "personality_summary" in raw_response:
            print("✅ personality_summary СОХРАНЕН в БД")

            summary = raw_response["personality_summary"]
            required_keys = ["nano", "narrative", "embedding_prompt"]
            missing = [k for k in required_keys if k not in summary]

            if missing:
                print(f"❌ ПРОБЛЕМА: Отсутствуют ключи {missing}")
                return False
            else:
                print(f"✅ Все обязательные ключи присутствуют")
                return True
        else:
            print("❌ personality_summary НЕ сохранен в БД")
            print(f"\n📄 Содержимое raw_ai_response:")
            print(json.dumps(raw_response, indent=2, ensure_ascii=False)[:500])
            return False

    finally:
        await conn.close()


async def test_vector_creation(user_id: int = 98005572):
    """Тест 3: Создание векторов в Qdrant"""

    print("\n" + "="*60)
    print("🧪 TEST 3: EmbeddingCreator creates vectors in Qdrant")
    print("="*60)

    # Проверяем количество векторов ДО
    import aiohttp
    async with aiohttp.ClientSession() as session:
        collections = ["selfology_answers_small", "selfology_answers_medium", "selfology_answers_large"]

        print("\n📊 Векторы ДО теста:")
        counts_before = {}
        for collection in collections:
            try:
                async with session.get(f"http://localhost:6333/collections/{collection}") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        count = data["result"]["points_count"]
                        counts_before[collection] = count
                        print(f"  - {collection}: {count} vectors")
            except:
                counts_before[collection] = 0

        # Получаем последний анализ
        conn = await asyncpg.connect(**DB_CONFIG)
        try:
            last_analysis = await conn.fetchrow("""
                SELECT aa.raw_ai_response
                FROM selfology.answer_analysis aa
                JOIN selfology.user_answers_new ua ON aa.user_answer_id = ua.id
                JOIN selfology.onboarding_sessions os ON ua.session_id = os.id
                WHERE os.user_id = $1
                ORDER BY aa.id DESC
                LIMIT 1
            """, user_id)

            if not last_analysis:
                print("⚠️ Нет анализа для тестирования")
                return False

            # Парсим JSON если строка
            analysis_result = last_analysis['raw_ai_response']
            if isinstance(analysis_result, str):
                analysis_result = json.loads(analysis_result)

            if "personality_summary" not in analysis_result:
                print("⚠️ Нет personality_summary в анализе")
                print(f"📋 Доступные ключи: {list(analysis_result.keys())}")
                return False

            # Создаем векторы
            embedding_creator = EmbeddingCreator()

            success = await embedding_creator.create_personality_vector(
                user_id=user_id,
                analysis_result=analysis_result,
                is_update=False
            )

            if success:
                print("\n✅ EmbeddingCreator вернул success=True")
            else:
                print("\n❌ EmbeddingCreator вернул success=False")
                return False

        finally:
            await conn.close()

        # Проверяем количество векторов ПОСЛЕ
        await asyncio.sleep(1)  # Даем время на сохранение

        print("\n📊 Векторы ПОСЛЕ теста:")
        counts_after = {}
        for collection in collections:
            try:
                async with session.get(f"http://localhost:6333/collections/{collection}") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        count = data["result"]["points_count"]
                        counts_after[collection] = count
                        diff = count - counts_before.get(collection, 0)
                        print(f"  - {collection}: {count} vectors (+{diff})")
            except:
                counts_after[collection] = 0

        # Проверяем что хотя бы в одной коллекции добавились векторы
        total_added = sum(counts_after.get(c, 0) - counts_before.get(c, 0) for c in collections)

        if total_added > 0:
            print(f"\n✅ Добавлено {total_added} векторов!")
            return True
        else:
            print("\n❌ Ни один вектор не был создан")
            return False


async def main():
    """Запуск всех тестов"""

    print("\n" + "🧬"*30)
    print("ТЕСТИРОВАНИЕ ИСПРАВЛЕНИЯ personality_summary")
    print("🧬"*30)

    results = {}

    # Тест 1
    try:
        results['test1_analyzer'] = await test_personality_summary_creation()
    except Exception as e:
        print(f"\n❌ TEST 1 FAILED: {e}")
        results['test1_analyzer'] = False

    # Тест 2
    try:
        results['test2_database'] = await test_database_save()
    except Exception as e:
        print(f"\n❌ TEST 2 FAILED: {e}")
        results['test2_database'] = False

    # Тест 3
    try:
        results['test3_vectors'] = await test_vector_creation()
    except Exception as e:
        print(f"\n❌ TEST 3 FAILED: {e}")
        results['test3_vectors'] = False

    # Итоговый отчет
    print("\n" + "="*60)
    print("📊 ИТОГОВЫЙ ОТЧЕТ")
    print("="*60)

    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")

    all_passed = all(results.values())

    print("\n" + "="*60)
    if all_passed:
        print("🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
        print("="*60)
        return 0
    else:
        print("⚠️ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОШЛИ")
        print("="*60)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
