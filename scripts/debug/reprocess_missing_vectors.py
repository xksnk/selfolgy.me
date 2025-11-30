#!/usr/bin/env python3
"""
Скрипт для reprocess ответов которые:
1. Имеют AI анализ в answer_analysis
2. НО не имеют векторов в Qdrant
3. НО не обновлены в digital_personality

Это нужно для обработки старых ответов новым исправленным кодом.
"""

import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import text

# Загрузка переменных окружения
load_dotenv()

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from selfology_bot.database.service import DatabaseService
from selfology_bot.database import DigitalPersonalityDAO
from selfology_bot.analysis.embedding_creator import EmbeddingCreator
from selfology_bot.analysis.personality_extractor import PersonalityExtractor


async def get_answers_without_vectors(user_id: int):
    """Получить answer_analysis которые не имеют векторов в Qdrant"""

    db_service = DatabaseService(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        user=os.getenv("DB_USER", "n8n"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "n8n")
    )

    async with db_service.get_async_session() as session:
        # Получаем все уникальные answer_analysis (берем последний для каждого ответа)
        result = await session.execute(text("""
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
                WHERE os.user_id = :user_id
                  AND aa.raw_ai_response IS NOT NULL
            )
            SELECT id, user_answer_id, raw_ai_response, raw_answer, question_json_id
            FROM latest_analysis
            WHERE rn = 1
            ORDER BY user_answer_id
        """), {"user_id": user_id})

        return result.fetchall()


async def reprocess_single_answer(
    analysis_id: int,
    user_answer_id: int,
    raw_ai_response: dict,
    raw_answer: str,
    question_json_id: str,
    user_id: int
):
    """Reprocess одного ответа: создать векторы и обновить digital personality"""

    print(f"\n  📝 Answer #{user_answer_id} (q_{question_json_id})")
    print(f"     Analysis ID: {analysis_id}")

    try:
        # 1. Создаем векторы
        embedding_creator = EmbeddingCreator()

        # Формируем analysis_result в нужном формате
        analysis_result = {
            "personality_summary": raw_ai_response,
            "answer_text": raw_answer,
            "question_id": question_json_id,
            "timestamp": datetime.now().isoformat()
        }

        print(f"     🔬 Создаем векторы...")
        vectors_created = await embedding_creator.create_personality_vector(
            user_id=user_id,
            analysis_result=analysis_result,
            is_update=True  # Это обновление существующего профиля
        )

        if vectors_created:
            print(f"     ✅ Векторы созданы")
        else:
            print(f"     ❌ Ошибка создания векторов")
            return False

        # 2. Обновляем digital personality
        db_service = DatabaseService(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 5432)),
            user=os.getenv("DB_USER", "n8n"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME", "n8n")
        )
        personality_dao = DigitalPersonalityDAO(db_service)
        personality_extractor = PersonalityExtractor()

        print(f"     💎 Обновляем digital personality...")

        # Извлекаем личностные данные из AI response
        extracted = personality_extractor.extract_from_analysis(raw_ai_response)

        # Получаем существующую личность
        existing = await personality_dao.get_personality(user_id)

        if existing:
            # Merge с существующей
            merged = personality_extractor.merge_personality_data(existing, extracted)
            personality_updated = await personality_dao.update_personality(user_id, merged, merge=True)
        else:
            # Создаем новую
            personality_updated = await personality_dao.create_personality(user_id, extracted)

        if personality_updated:
            print(f"     ✅ Digital personality обновлена")
        else:
            print(f"     ❌ Ошибка обновления digital personality")
            return False

        print(f"     🎉 Успешно reprocessed!")
        return True

    except Exception as e:
        print(f"     ❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False


async def reprocess_user_answers(user_id: int, dry_run: bool = False):
    """Reprocess всех ответов пользователя"""

    print(f"\n{'='*60}")
    print(f"🔄 REPROCESS MISSING VECTORS")
    print(f"{'='*60}")
    print(f"\nПользователь: #{user_id}")

    if dry_run:
        print("⚠️  DRY RUN режим - изменения НЕ будут применены")

    # Получаем ответы без векторов
    answers = await get_answers_without_vectors(user_id)

    print(f"\n📊 Найдено ответов для reprocess: {len(answers)}")

    if len(answers) == 0:
        print("\n✅ Все ответы уже обработаны!")
        return

    if dry_run:
        print("\n📋 Список ответов для reprocess:")
        for row in answers:
            print(f"  - Answer #{row[1]}, Analysis #{row[0]}, Question: q_{row[4]}")
        return

    # Reprocess каждого ответа
    success_count = 0
    failed_count = 0

    print(f"\n🚀 Начинаем reprocess...")

    for row in answers:
        analysis_id = row[0]
        user_answer_id = row[1]
        raw_ai_response = row[2]
        raw_answer = row[3]
        question_json_id = row[4]

        success = await reprocess_single_answer(
            analysis_id=analysis_id,
            user_answer_id=user_answer_id,
            raw_ai_response=raw_ai_response,
            raw_answer=raw_answer,
            question_json_id=question_json_id,
            user_id=user_id
        )

        if success:
            success_count += 1
        else:
            failed_count += 1

        # Небольшая пауза между запросами
        await asyncio.sleep(0.5)

    # Итоги
    print(f"\n{'='*60}")
    print(f"📊 ИТОГИ REPROCESS")
    print(f"{'='*60}")
    print(f"✅ Успешно: {success_count}")
    print(f"❌ Ошибки: {failed_count}")
    print(f"📈 Всего: {len(answers)}")

    if success_count == len(answers):
        print(f"\n🎉 ВСЕ ОТВЕТЫ УСПЕШНО REPROCESSED!")
    else:
        print(f"\n⚠️  Некоторые ответы не удалось обработать")


async def main():
    """Точка входа"""

    # Параметры из командной строки
    if len(sys.argv) < 2:
        print("Usage: python reprocess_missing_vectors.py <user_id> [--dry-run]")
        print("\nПример:")
        print("  python reprocess_missing_vectors.py 98005572")
        print("  python reprocess_missing_vectors.py 98005572 --dry-run")
        sys.exit(1)

    user_id = int(sys.argv[1])
    dry_run = "--dry-run" in sys.argv

    await reprocess_user_answers(user_id, dry_run=dry_run)


if __name__ == "__main__":
    asyncio.run(main())
