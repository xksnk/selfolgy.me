"""
Тест исправления векторизации - проверяем что _save_breakthrough_moment работает
"""

import asyncio
import sys
from pathlib import Path

# Добавляем пути
sys.path.append(str(Path(__file__).parent.parent))

from selfology_bot.database import DatabaseService, OnboardingDAO
from selfology_bot.analysis import EmbeddingCreator
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_vectorization():
    """Тестируем что векторизация не падает на breakthrough"""

    logger.info("="*80)
    logger.info("🧪 TESTING VECTORIZATION FIX")
    logger.info("="*80)

    # Инициализация
    db_service = DatabaseService(
        host="localhost",
        port=5432,
        user="n8n",
        password="sS67wM+1zMBRFHAW4kj9HwFl5J6+veo7Nirx0/I+oiU=",
        database="n8n"
    )
    await db_service.initialize()

    dao = OnboardingDAO(db_service)
    embedding_creator = EmbeddingCreator()

    # Получаем последний анализ для пользователя 98005572
    query = """
        SELECT
            aa.id,
            aa.user_answer_id,
            aa.traits,
            aa.personality_summary,
            aa.router_recommendations,
            aa.processing_metadata,
            aa.quality_score
        FROM selfology.answer_analysis aa
        JOIN selfology.user_answers_new ua ON aa.user_answer_id = ua.id
        JOIN selfology.onboarding_sessions os ON ua.session_id = os.id
        WHERE os.user_id = 98005572
        ORDER BY aa.id DESC
        LIMIT 1
    """

    async with db_service.get_connection() as conn:
        row = await conn.fetchrow(query)

    if not row:
        logger.error("❌ No analysis found for user 98005572")
        await db_service.close()
        return

    logger.info(f"✅ Found analysis record: {row['id']}")

    # Формируем analysis_result как в реальной системе
    import json

    analysis_result = {
        "personality_traits": json.loads(row['traits']) if isinstance(row['traits'], str) else row['traits'],
        "personality_summary": json.loads(row['personality_summary']) if isinstance(row['personality_summary'], str) else row['personality_summary'],
        "router_recommendations": json.loads(row['router_recommendations']) if isinstance(row['router_recommendations'], str) else row['router_recommendations'],
        "processing_metadata": json.loads(row['processing_metadata']) if isinstance(row['processing_metadata'], str) else row['processing_metadata'],
        "quality_score": row['quality_score']
    }

    logger.info(f"📊 Analysis data prepared")

    # Тестируем векторизацию с is_update=True (чтобы проверить breakthrough path)
    try:
        logger.info("🚀 Testing create_personality_vector with is_update=True...")

        success = await embedding_creator.create_personality_vector(
            user_id=98005572,
            analysis_result=analysis_result,
            is_update=True  # Это вызовет _update_existing_vectors и может вызвать breakthrough
        )

        if success:
            logger.info("✅ Vectorization completed successfully!")
        else:
            logger.warning("⚠️ Vectorization returned False (но не упала с ошибкой)")

    except Exception as e:
        logger.error(f"❌ Vectorization failed with error: {e}", exc_info=True)
        await db_service.close()
        return

    # Проверяем что вектор обновился
    logger.info("🔍 Checking if vector was updated in Qdrant...")

    import requests
    response = requests.get(f"http://localhost:6333/collections/personality_profiles/points/98005572")

    if response.status_code == 200:
        data = response.json()
        last_updated = data['result']['payload'].get('last_updated')
        logger.info(f"✅ Vector found in Qdrant, last_updated: {last_updated}")
    else:
        logger.error(f"❌ Vector not found in Qdrant")

    # Проверяем personality_evolution коллекцию
    response = requests.get(f"http://localhost:6333/collections/personality_evolution")

    if response.status_code == 200:
        data = response.json()
        count = data['result']['points_count']
        logger.info(f"📈 personality_evolution collection has {count} points")

    await db_service.close()

    logger.info("="*80)
    logger.info("🎉 TEST COMPLETED")
    logger.info("="*80)


if __name__ == "__main__":
    asyncio.run(test_vectorization())
