#!/usr/bin/env python3
"""
Скрипт для ПОЛНОЙ переаналитики context story с обновленным кодом

Что делает:
1. Получает context story из БД
2. Заново анализирует через AnswerAnalyzer (с исправленным CONTEXT_STORY_QUESTION)
3. Сохраняет новый анализ
4. Векторизует
5. Обновляет digital personality
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
from selfology_bot.analysis.answer_analyzer import AnswerAnalyzer
from selfology_bot.analysis.embedding_creator import EmbeddingCreator
from selfology_bot.database import DigitalPersonalityDAO
from selfology_bot.analysis.personality_extractor import PersonalityExtractor


async def get_context_story(context_story_id: int):
    """Получить context story из БД"""

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
                cs.id,
                cs.user_id,
                cs.session_id,
                cs.story_text,
                cs.created_at,
                os.questions_asked
            FROM selfology.user_context_stories cs
            JOIN selfology.onboarding_sessions os ON cs.session_id = os.id
            WHERE cs.id = $1
        """, context_story_id)

    await db_service.close()
    return result


async def reanalyze_context_story(context_story_id: int):
    """Полная переаналитика context story"""

    print(f"\n🔬 FULL REANALYSIS of context story ID: {context_story_id}")
    print("="*60)

    # 1. Получаем context story
    story = await get_context_story(context_story_id)

    if not story:
        print(f"❌ Context story {context_story_id} not found")
        return False

    print(f"\n📊 Story Data:")
    print(f"   User ID: {story['user_id']}")
    print(f"   Session ID: {story['session_id']}")
    print(f"   Questions asked: {story['questions_asked']}")
    print(f"   Story text: {story['story_text'][:100]}...")
    print(f"   Created: {story['created_at']}")

    # 2. Подготавливаем question_data с ИСПРАВЛЕННОЙ структурой
    # (как в обновленном CONTEXT_STORY_QUESTION)
    question_data = {
        "id": "system_context_story",
        "type": "system",
        "text": "Если хотите, расскажите что-то важное о себе — то, что обычно не попадает в анкеты, но помогло бы мне лучше вас понять.",
        "classification": {
            "domain": "SYSTEM",
            "depth_level": "META",
            "energy_dynamic": "OPENING"
        },
        "psychology": {
            "complexity": 3,
            "emotional_weight": 2,
            "insight_potential": 5,
            "trust_requirement": 3,
            "safety_level": 4
        }
    }

    print(f"\n✅ question_data prepared with psychology fields")

    # 3. Подготавливаем user_context
    user_context = {
        "user_id": story['user_id'],
        "question_number": story['questions_asked'],
        "session_history": [],
        "trust_level": 0.6,
        "energy_level": 0.7,
        "fatigue_level": 0.3,
        "time_of_day": datetime.now().hour,
        "response_time_seconds": 120
    }

    # 4. АНАЛИЗИРУЕМ через AnswerAnalyzer
    print(f"\n🧠 Running AI analysis...")

    analyzer = AnswerAnalyzer()

    try:
        analysis_result = await analyzer.analyze_answer(
            question_data=question_data,
            user_answer=story['story_text'],
            user_context=user_context
        )

        print(f"✅ Analysis completed!")
        print(f"   Model: {analysis_result.get('processing_metadata', {}).get('model_used', 'unknown')}")

        # Проверяем personality_summary
        if "personality_summary" in analysis_result:
            print(f"   ✅ personality_summary present")
            summary = analysis_result["personality_summary"]
            print(f"      - nano: {summary.get('nano', '')[:50]}")
            print(f"      - narrative length: {len(summary.get('narrative', ''))} chars")
        else:
            print(f"   ❌ personality_summary MISSING!")
            print(f"   ⚠️  Still using old emergency_handler without fix")
            return False

    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 5. Сохраняем новый анализ в БД
    print(f"\n💾 Saving new analysis to DB...")

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

    # Сохраняем как context story analysis
    new_analysis_id = await dao.save_context_story_analysis(
        context_story_id=context_story_id,
        analysis_result=analysis_result
    )

    print(f"✅ New analysis saved with ID: {new_analysis_id}")

    # 6. Векторизация
    print(f"\n📈 Creating vectors...")

    embedding_creator = EmbeddingCreator()

    try:
        vector_success = await embedding_creator.create_personality_vector(
            user_id=story['user_id'],
            analysis_result=analysis_result,
            is_update=True
        )

        if vector_success:
            print(f"✅ Vectors created successfully")
            await dao.update_vectorization_status(new_analysis_id, "success", None)
        else:
            print(f"❌ Vector creation failed")
            await dao.update_vectorization_status(
                new_analysis_id,
                "failed",
                "create_personality_vector returned False"
            )
            return False

    except Exception as e:
        print(f"❌ Vectorization error: {e}")
        await dao.update_vectorization_status(new_analysis_id, "failed", str(e)[:500])
        import traceback
        traceback.print_exc()
        return False

    # 7. Digital Personality
    print(f"\n🧬 Updating digital personality...")

    try:
        personality_dao = DigitalPersonalityDAO(db_service)
        personality_extractor = PersonalityExtractor()

        existing_personality = await personality_dao.get_personality(story['user_id'])

        extracted = await personality_extractor.extract_from_answer(
            question_text=question_data['text'],
            user_answer=story['story_text'],
            question_metadata=question_data['classification'],
            existing_personality=existing_personality
        )

        if existing_personality:
            merged = personality_extractor.merge_extractions(existing_personality, extracted)
            await personality_dao.update_personality(story['user_id'], merged, merge=True)
            print(f"✅ Digital personality updated")
        else:
            await personality_dao.create_personality(story['user_id'], extracted)
            print(f"✅ Digital personality created")

        await dao.update_dp_update_status(new_analysis_id, "success", None)

    except Exception as e:
        print(f"❌ DP update error: {e}")
        await dao.update_dp_update_status(new_analysis_id, "failed", str(e)[:500])
        import traceback
        traceback.print_exc()
        return False

    finally:
        await db_service.close()

    print(f"\n" + "="*60)
    print(f"🎉 Context story {context_story_id} FULLY reanalyzed!")
    print(f"   New analysis ID: {new_analysis_id}")
    print(f"   Vectorization: ✅")
    print(f"   Digital Personality: ✅")
    print(f"="*60)

    return True


async def main():
    """Main function"""

    # ID последнего активного context story
    context_story_id = 4

    print(f"\n🚀 Starting FULL context story reanalysis")
    print(f"   Story ID: {context_story_id}")
    print(f"   Time: {datetime.now().isoformat()}\n")

    success = await reanalyze_context_story(context_story_id)

    if success:
        print(f"\n✅ SUCCESS!")
    else:
        print(f"\n❌ FAILED - check logs above")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
