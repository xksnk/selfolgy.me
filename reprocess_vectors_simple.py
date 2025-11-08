#!/usr/bin/env python3
"""
Упрощенный скрипт для пересоздания векторов в Qdrant
для существующих answer_analysis которые не имеют векторов.
"""

import asyncio
import os
import sys
import asyncpg
import json
from datetime import datetime
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from selfology_bot.analysis.embedding_creator import EmbeddingCreator


async def get_analyses_for_user(user_id: int):
    """Получить все answer_analysis для пользователя (уникальные по user_answer_id)"""

    conn = await asyncpg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        user=os.getenv("DB_USER", "n8n"),
        password=os.getenv("DB_PASSWORD", "sS67wM+1zMBRFHAW4kj9HwFl5J6+veo7Nirx0/I+oiU="),
        database=os.getenv("DB_NAME", "n8n")
    )

    try:
        rows = await conn.fetch("""
            WITH latest_analysis AS (
                SELECT
                    aa.id,
                    aa.user_answer_id,
                    aa.raw_ai_response,
                    ua.raw_answer,
                    ua.question_json_id,
                    ROW_NUMBER() OVER (PARTITION BY aa.user_answer_id ORDER BY aa.id DESC) as rn
                FROM selfology.answer_analysis aa
                JOIN selfology.user_answers_new ua ON aa.user_answer_id = ua.id
                JOIN selfology.onboarding_sessions os ON ua.session_id = os.id
                WHERE os.user_id = $1
                  AND aa.raw_ai_response IS NOT NULL
            )
            SELECT id, user_answer_id, raw_ai_response, raw_answer, question_json_id
            FROM latest_analysis
            WHERE rn = 1
            ORDER BY user_answer_id
        """, user_id)

        return rows

    finally:
        await conn.close()


async def create_vectors_for_analysis(
    analysis_id: int,
    user_answer_id: int,
    raw_ai_response: dict,
    raw_answer: str,
    question_json_id: str,
    user_id: int
):
    """Создать векторы в Qdrant для одного analysis"""

    print(f"\n  📝 Answer #{user_answer_id} (q_{question_json_id})")
    print(f"     Analysis ID: {analysis_id}")

    try:
        embedding_creator = EmbeddingCreator()
        print(f"     🔍 OpenAI client initialized: {embedding_creator.openai_client is not None}")
        print(f"     🔍 Qdrant client initialized: {embedding_creator.qdrant_client is not None}")

        # raw_ai_response может быть строкой JSON - конвертируем
        if isinstance(raw_ai_response, str):
            try:
                raw_ai_response = json.loads(raw_ai_response)
            except json.JSONDecodeError:
                print(f"     ❌ Не удалось распарсить raw_ai_response")
                return False

        # Извлекаем personality_summary для проверки
        personality_summary = raw_ai_response.get('personality_summary', {})

        if not personality_summary:
            print(f"     ❌ personality_summary пуст в raw_ai_response")
            return False

        # Используем весь raw_ai_response + добавляем недостающие поля
        analysis_result = dict(raw_ai_response)  # Копируем все поля
        analysis_result["answer_text"] = raw_answer
        analysis_result["question_id"] = question_json_id
        analysis_result["timestamp"] = datetime.now().isoformat()

        print(f"     🔬 Создаем векторы в Qdrant...")
        print(f"     🔍 personality_summary keys: {list(personality_summary.keys())}")
        print(f"     🔍 has 'narrative': {'narrative' in personality_summary}")
        print(f"     🔍 has 'nano': {'nano' in personality_summary}")
        print(f"     🔍 narrative length: {len(str(personality_summary.get('narrative', '')))}")
        print(f"     🔍 nano length: {len(str(personality_summary.get('nano', '')))}")

        # Создаем векторы (is_update=True чтобы не ругался на существующие)
        success = await embedding_creator.create_personality_vector(
            user_id=user_id,
            analysis_result=analysis_result,
            is_update=True
        )

        print(f"     🔍 create_personality_vector returned: {success}")

        if success:
            print(f"     ✅ Векторы созданы")
            return True
        else:
            print(f"     ❌ Ошибка создания векторов (check logs)")
            # Добавим дебаг информацию
            print(f"     🔍 Debug: analysis_result keys = {list(analysis_result.keys())}")
            print(f"     🔍 Debug: personality_summary type = {type(analysis_result['personality_summary'])}")
            if isinstance(analysis_result['personality_summary'], dict):
                print(f"     🔍 Debug: personality_summary keys = {list(analysis_result['personality_summary'].keys())}")
            return False

    except Exception as e:
        print(f"     ❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return False


async def reprocess_vectors(user_id: int, dry_run: bool = False):
    """Пересоздать векторы для всех analyses пользователя"""

    print(f"\n{'='*60}")
    print(f"🔄 REPROCESS VECTORS FOR USER {user_id}")
    print(f"{'='*60}")

    if dry_run:
        print("⚠️  DRY RUN режим - изменения НЕ будут применены\n")

    # Получаем все analyses
    print("📊 Получаем analyses из БД...")
    analyses = await get_analyses_for_user(user_id)

    print(f"   Найдено: {len(analyses)} уникальных analyses")

    if len(analyses) == 0:
        print("\n✅ Нет analyses для обработки!")
        return

    if dry_run:
        print("\n📋 Список analyses для reprocess:")
        for row in analyses:
            print(f"  - Analysis #{row['id']}, Answer #{row['user_answer_id']}, Question: q_{row['question_json_id']}")
        print(f"\nДля запуска reprocess удалите флаг --dry-run")
        return

    # Reprocess каждого
    success_count = 0
    failed_count = 0

    print(f"\n🚀 Начинаем reprocess...\n")

    for row in analyses:
        success = await create_vectors_for_analysis(
            analysis_id=row['id'],
            user_answer_id=row['user_answer_id'],
            raw_ai_response=row['raw_ai_response'],
            raw_answer=row['raw_answer'],
            question_json_id=row['question_json_id'],
            user_id=user_id
        )

        if success:
            success_count += 1
        else:
            failed_count += 1

        # Пауза между запросами
        await asyncio.sleep(1)

    # Итоги
    print(f"\n{'='*60}")
    print(f"📊 ИТОГИ REPROCESS")
    print(f"{'='*60}")
    print(f"✅ Успешно: {success_count}")
    print(f"❌ Ошибки: {failed_count}")
    print(f"📈 Всего: {len(analyses)}")

    if success_count == len(analyses):
        print(f"\n🎉 ВСЕ ВЕКТОРЫ УСПЕШНО СОЗДАНЫ!")
        print(f"\n💡 Теперь запустите /onboarding_profile в Telegram для проверки")
    else:
        print(f"\n⚠️  Некоторые векторы не удалось создать")


async def main():
    """Точка входа"""

    if len(sys.argv) < 2:
        print("Usage: python reprocess_vectors_simple.py <user_id> [--dry-run]")
        print("\nПример:")
        print("  python reprocess_vectors_simple.py 98005572")
        print("  python reprocess_vectors_simple.py 98005572 --dry-run")
        sys.exit(1)

    user_id = int(sys.argv[1])
    dry_run = "--dry-run" in sys.argv

    await reprocess_vectors(user_id, dry_run=dry_run)


if __name__ == "__main__":
    asyncio.run(main())
