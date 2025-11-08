#!/usr/bin/env python3
"""
Скрипт для перевекторизации context story с обновленным кодом

Исправления в коде:
1. Добавлен personality_summary в emergency_handler
2. Добавлены psychology поля в CONTEXT_STORY_QUESTION
"""

import asyncio
import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from selfology_bot.database.service import DatabaseService
from selfology_bot.database.onboarding_dao import OnboardingDAO
from selfology_bot.analysis.embedding_creator import EmbeddingCreator
from selfology_bot.database import DigitalPersonalityDAO
from selfology_bot.analysis.personality_extractor import PersonalityExtractor


async def get_context_story_analysis(context_story_id: int):
    """Получить анализ context story из БД"""

    db_service = DatabaseService(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        user=os.getenv("DB_USER", "n8n"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "n8n"),
        schema="selfology"
    )

    await db_service.initialize()

    async with db_service.get_connection() as conn:
        result = await conn.fetchrow("""
            SELECT
                aa.id as analysis_id,
                aa.context_story_id,
                aa.raw_ai_response,
                aa.ai_model_used,
                aa.vectorization_status,
                cs.user_id,
                cs.story_text
            FROM selfology.answer_analysis aa
            JOIN selfology.user_context_stories cs ON aa.context_story_id = cs.id
            WHERE cs.id = $1
        """, context_story_id)

    await db_service.close()
    return result


async def reprocess_context_story(context_story_id: int):
    """Перевекторизация context story с обновленным кодом"""

    print(f"\n🔄 Reprocessing context story ID: {context_story_id}")
    print("="*60)

    # 1. Получаем анализ из БД
    story_data = await get_context_story_analysis(context_story_id)

    if not story_data:
        print(f"❌ Context story {context_story_id} не найден в БД")
        return False

    print(f"\n📊 Story Data:")
    print(f"   User ID: {story_data['user_id']}")
    print(f"   Analysis ID: {story_data['analysis_id']}")
    print(f"   Model used: {story_data['ai_model_used']}")
    print(f"   Current vectorization: {story_data['vectorization_status']}")
    print(f"   Story text: {story_data['story_text'][:100]}...")

    # 2. Парсим анализ
    try:
        analysis_result = json.loads(story_data['raw_ai_response'])
        print(f"\n✅ Analysis parsed successfully")

        # Проверяем наличие personality_summary
        if "personality_summary" in analysis_result:
            print(f"   ✅ personality_summary present")
            summary = analysis_result["personality_summary"]
            print(f"      - nano: {summary.get('nano', 'missing')[:50]}")
            print(f"      - narrative: {len(summary.get('narrative', ''))} chars")
        else:
            print(f"   ❌ personality_summary MISSING")
            print(f"   Available keys: {list(analysis_result.keys())}")

            # Если emergency_handler - предупреждаем что нужно переанализировать
            if analysis_result.get('processing_metadata', {}).get('model_used') == 'emergency_handler':
                print(f"\n   ⚠️  This is emergency_handler analysis - need FULL reanalysis with updated code")
                print(f"   ℹ️  Emergency_handler now has personality_summary, but better to reanalyze with real AI")

            return False

    except Exception as e:
        print(f"❌ Failed to parse analysis: {e}")
        return False

    # 3. Создаем векторы
    print(f"\n📈 Creating vectors...")

    embedding_creator = EmbeddingCreator()

    try:
        # Проверяем что Qdrant доступен
        if not embedding_creator.qdrant_client:
            print(f"❌ Qdrant client not available")
            return False

        # Создаем векторы
        vector_success = await embedding_creator.create_personality_vector(
            user_id=story_data['user_id'],
            analysis_result=analysis_result,
            is_update=True  # Обновление, т.к. у пользователя уже есть данные
        )

        if vector_success:
            print(f"✅ Vectors created successfully")

            # Обновляем статус в БД
            db_service = DatabaseService(
                host=os.getenv("DB_HOST", "localhost"),
                port=int(os.getenv("DB_PORT", 5432)),
                user=os.getenv("DB_USER", "n8n"),
                password=os.getenv("DB_PASSWORD"),
                database=os.getenv("DB_NAME", "n8n"),
                schema="selfology"
            )

            await db_service.initialize()
            dao = OnboardingDAO(db_service)

            await dao.update_vectorization_status(
                story_data['analysis_id'],
                "success",
                None
            )

            await db_service.close()
            print(f"✅ Database updated: vectorization_status = success")

        else:
            print(f"❌ Vector creation failed")
            return False

    except Exception as e:
        print(f"❌ Vectorization error: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 4. Обновляем digital personality
    print(f"\n🧬 Updating digital personality...")

    try:
        db_service = DatabaseService(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 5432)),
            user=os.getenv("DB_USER", "n8n"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME", "n8n"),
            schema="selfology"
        )

        await db_service.initialize()

        personality_dao = DigitalPersonalityDAO(db_service)
        personality_extractor = PersonalityExtractor()

        # Получаем существующую личность
        existing_personality = await personality_dao.get_personality(story_data['user_id'])

        # Извлекаем из context story
        extracted = await personality_extractor.extract_from_answer(
            question_text="Context story",
            user_answer=story_data['story_text'],
            question_metadata={"domain": "SYSTEM", "depth_level": "META"},
            existing_personality=existing_personality
        )

        # Объединяем
        if existing_personality:
            merged = personality_extractor.merge_extractions(existing_personality, extracted)
            await personality_dao.update_personality(story_data['user_id'], merged, merge=True)
            print(f"✅ Digital personality updated (merged)")
        else:
            await personality_dao.create_personality(story_data['user_id'], extracted)
            print(f"✅ Digital personality created")

        # Обновляем статус в БД
        dao = OnboardingDAO(db_service)
        await dao.update_dp_update_status(
            story_data['analysis_id'],
            "success",
            None
        )

        await db_service.close()
        print(f"✅ Database updated: dp_update_status = success")

    except Exception as e:
        print(f"❌ DP update error: {e}")
        import traceback
        traceback.print_exc()
        return False

    print(f"\n" + "="*60)
    print(f"🎉 Context story {context_story_id} reprocessed successfully!")
    print(f"="*60)

    return True


async def main():
    """Main function"""

    # ID последнего активного context story для user 98005572
    context_story_id = 4

    print(f"\n🚀 Starting context story reprocessing")
    print(f"   Story ID: {context_story_id}")
    print(f"   Time: {datetime.now().isoformat()}\n")

    success = await reprocess_context_story(context_story_id)

    if success:
        print(f"\n✅ SUCCESS!")
    else:
        print(f"\n❌ FAILED - check logs above")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
