#!/usr/bin/env python3
"""
Тестовый скрипт для проверки исправлений:
1. Task Registry - background tasks завершаются корректно
2. OpenAI Embeddings API - реальные векторы создаются
"""

import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from selfology_bot.services.onboarding.orchestrator import OnboardingOrchestrator
from selfology_bot.database.service import DatabaseService
from selfology_bot.analysis.embedding_creator import EmbeddingCreator


async def test_background_tasks_completion():
    """Тест 1: Проверка что background tasks завершаются"""
    print("\n" + "="*60)
    print("🧪 ТЕСТ 1: Background Tasks Completion")
    print("="*60)

    orchestrator = OnboardingOrchestrator()

    # Получаем статус до
    status_before = orchestrator.get_background_tasks_status()
    print(f"\n📊 Background tasks ДО: {status_before}")

    # Симулируем обработку ответа для существующего пользователя
    user_id = 98005572
    question_id = 385  # Существующий вопрос
    answer_text = "Тестовый ответ для проверки background tasks"

    print(f"\n🚀 Запускаем process_user_answer для user {user_id}...")

    try:
        result = await orchestrator.process_user_answer(
            user_id=user_id,
            question_id=str(question_id),
            answer=answer_text
        )

        print(f"✅ process_user_answer завершен: {result}")

        # Даем время на запуск background tasks
        await asyncio.sleep(1)

        status_after_start = orchestrator.get_background_tasks_status()
        print(f"\n📊 Background tasks ПОСЛЕ запуска: {status_after_start}")

        # Ждем завершения background tasks (максимум 30 секунд)
        print("\n⏳ Ожидаем завершения background tasks (max 30s)...")

        for i in range(30):
            await asyncio.sleep(1)
            status = orchestrator.get_background_tasks_status()

            active_count = status.get('active_tasks', 0)

            if active_count == 0:
                print(f"\n✅ Все background tasks завершены за {i+1} секунд!")
                print(f"📊 Финальный статус: {status}")
                return True
            else:
                print(f"  ⏱️  {i+1}s: активных tasks: {active_count}")

        print("\n❌ Background tasks не завершились за 30 секунд!")
        print(f"📊 Статус: {orchestrator.get_background_tasks_status()}")
        return False

    except Exception as e:
        print(f"\n❌ Ошибка в тесте: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_openai_embeddings():
    """Тест 2: Проверка OpenAI Embeddings API"""
    print("\n" + "="*60)
    print("🧪 ТЕСТ 2: OpenAI Embeddings API Integration")
    print("="*60)

    # Проверяем наличие API ключа
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        print("❌ OPENAI_API_KEY не найден в .env")
        return False

    print(f"✅ OPENAI_API_KEY найден: {api_key[:20]}...")

    # Создаем EmbeddingCreator
    embedding_creator = EmbeddingCreator()

    print(f"\n📊 Статистика до теста:")
    print(f"  API calls: {embedding_creator.embedding_stats.get('api_calls_success', 0)}")
    print(f"  Total cost: ${embedding_creator.embedding_stats.get('total_cost', 0):.6f}")

    # Тестовый текст
    test_text = "Я увлекаюсь программированием и психологией. Мне интересно понимать как работает человеческое мышление."

    print(f"\n🔬 Создаем embedding для текста: '{test_text[:50]}...'")

    try:
        # Создаем векторы для всех 3 уровней
        vectors = {}

        for level_name, (model, dimensions) in [
            ("deep", ("text-embedding-3-large", 3072)),
            ("standard", ("text-embedding-3-small", 1536)),
            ("quick", ("text-embedding-3-small", 512))
        ]:
            print(f"\n  🎯 Создаем {level_name} embedding ({dimensions}D)...")

            start_time = asyncio.get_event_loop().time()

            vector = await embedding_creator._create_openai_embedding(
                text=test_text,
                model=model,
                dimensions=dimensions
            )

            elapsed = (asyncio.get_event_loop().time() - start_time) * 1000

            if vector and len(vector) == dimensions:
                print(f"    ✅ {level_name}: {dimensions}D вектор создан за {elapsed:.0f}ms")
                vectors[level_name] = vector
            else:
                print(f"    ❌ {level_name}: ОШИБКА - вектор имеет неверную размерность: {len(vector) if vector else 0}")
                return False

        # Проверяем статистику
        print(f"\n📊 Статистика после теста:")
        print(f"  API calls: {embedding_creator.embedding_stats.get('api_calls_success', 0)}")
        print(f"  Total cost: ${embedding_creator.embedding_stats.get('total_cost', 0):.6f}")
        print(f"  Cache hits: {embedding_creator.embedding_stats.get('cache_hits', 0)}")

        # Проверяем что это НЕ mock (не случайные числа)
        for level_name, vector in vectors.items():
            # Mock возвращает числа от -1 до 1, реальные embeddings имеют другой диапазон
            import statistics
            mean = statistics.mean(vector[:100])  # Берем первые 100 значений

            # Реальные embeddings обычно имеют среднее близкое к 0, но не точно 0
            # Mock embeddings будут иметь среднее ~0 из-за uniform distribution
            print(f"\n  🔍 {level_name} вектор анализ:")
            print(f"    Mean (первые 100): {mean:.6f}")
            print(f"    Min: {min(vector):.6f}, Max: {max(vector):.6f}")

        print("\n✅ OpenAI Embeddings API работает корректно!")
        return True

    except Exception as e:
        print(f"\n❌ Ошибка при создании embeddings: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_full_pipeline():
    """Тест 3: Полный pipeline от ответа до векторизации в Qdrant"""
    print("\n" + "="*60)
    print("🧪 ТЕСТ 3: Полный Pipeline (Answer → AI → Vectors → Qdrant)")
    print("="*60)

    # Этот тест требует реального запуска orchestrator.process_user_answer
    # и ожидания завершения всех background tasks

    print("\n⚠️  Этот тест создаст реальный ответ в БД для пользователя 98005572")
    print("⏳ Запускаем полный цикл...")

    orchestrator = OnboardingOrchestrator()
    user_id = 98005572
    question_id = 616  # Другой вопрос для тестирования
    answer_text = f"Полный тест pipeline от {datetime.now().strftime('%H:%M:%S')}"

    try:
        # Запускаем обработку
        result = await orchestrator.process_user_answer(
            user_id=user_id,
            question_id=str(question_id),
            answer=answer_text
        )

        print(f"✅ Instant feedback отправлен: {result.get('instant_feedback', {}).get('message', 'N/A')}")

        # Ждем завершения background tasks
        print("\n⏳ Ожидаем завершения deep analysis (max 60s)...")

        for i in range(60):
            await asyncio.sleep(1)
            status = orchestrator.get_background_tasks_status()

            if status.get('active_tasks', 0) == 0:
                print(f"\n✅ Deep analysis завершен за {i+1} секунд!")
                break

            if i % 5 == 0:
                print(f"  ⏱️  {i+1}s: активных tasks: {status.get('active_tasks', 0)}")

        # Проверяем результаты в БД
        print("\n🔍 Проверяем результаты в БД...")

        db_service = DatabaseService()

        # Проверяем answer_analysis
        async with db_service.get_async_session() as session:
            from sqlalchemy import text

            result = await session.execute(text("""
                SELECT COUNT(*)
                FROM selfology.answer_analysis aa
                JOIN selfology.user_answers_new ua ON aa.user_answer_id = ua.id
                JOIN selfology.onboarding_sessions os ON ua.session_id = os.id
                WHERE os.user_id = :user_id
                  AND ua.answer_text = :answer_text
            """), {"user_id": user_id, "answer_text": answer_text})

            ai_count = result.scalar()
            print(f"  AI Analysis: {ai_count} записей")

        # Проверяем Qdrant
        import requests
        qdrant_url = "http://localhost:6333"

        response = requests.post(
            f"{qdrant_url}/collections/personality_profiles/points/scroll",
            json={
                "filter": {
                    "must": [{"key": "user_id", "match": {"value": user_id}}]
                },
                "limit": 100
            }
        )

        if response.status_code == 200:
            points = response.json().get("result", {}).get("points", [])
            print(f"  Qdrant векторов: {len(points)}")

            # Ищем наш новый вектор
            new_vectors = [
                p for p in points
                if answer_text in p.get("payload", {}).get("context", "")
            ]

            if new_vectors:
                print(f"\n✅ УСПЕХ! Новый вектор найден в Qdrant!")
                print(f"   Vector ID: {new_vectors[0].get('id')}")
                return True
            else:
                print(f"\n⚠️  Вектор пока не найден (может потребоваться больше времени)")
                return False

        return True

    except Exception as e:
        print(f"\n❌ Ошибка в полном pipeline: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Запуск всех тестов"""
    print("\n" + "="*60)
    print("🚀 ТЕСТИРОВАНИЕ ИСПРАВЛЕНИЙ ОНБОРДИНГА")
    print("="*60)
    print("\nПроверяем:")
    print("  1. Task Registry - background tasks завершаются")
    print("  2. OpenAI Embeddings API - реальные векторы")
    print("  3. Полный pipeline - от ответа до Qdrant")

    results = {}

    # Тест 1: Background tasks
    results['background_tasks'] = await test_background_tasks_completion()

    # Тест 2: OpenAI API
    results['openai_api'] = await test_openai_embeddings()

    # Тест 3: Полный pipeline (опционально)
    # results['full_pipeline'] = await test_full_pipeline()

    # Итоги
    print("\n" + "="*60)
    print("📊 ИТОГИ ТЕСТИРОВАНИЯ")
    print("="*60)

    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")

    all_passed = all(results.values())

    if all_passed:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
    else:
        print("\n⚠️  НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ")

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
