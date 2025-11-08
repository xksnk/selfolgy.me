"""
Повторная обработка ответа 14 с полной векторизацией
"""

import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent / "intelligent_question_core"))

from selfology_bot.database import DatabaseService, OnboardingDAO
from selfology_bot.analysis import AnswerAnalyzer, EmbeddingCreator
from selfology_bot.analysis.personality_extractor import PersonalityExtractor
from selfology_bot.database.digital_personality_dao import DigitalPersonalityDAO
from intelligent_question_core.api.core_api import SelfologyQuestionCore
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def reprocess_answer_14():
    """Повторная обработка ответа 14"""

    logger.info("="*80)
    logger.info("🔄 REPROCESSING ANSWER 14 WITH FULL VECTORIZATION")
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
    personality_dao = DigitalPersonalityDAO(db_service)
    analyzer = AnswerAnalyzer()
    embedding_creator = EmbeddingCreator()
    personality_extractor = PersonalityExtractor()

    # Загружаем Question Core
    core_file_path = str(Path(__file__).parent.parent / "intelligent_question_core" / "data" / "selfology_intelligent_core.json")
    question_core = SelfologyQuestionCore(core_file_path)

    # Получаем данные ответа 14
    query = """
        SELECT
            ua.id,
            ua.session_id,
            ua.question_json_id,
            ua.raw_answer,
            os.user_id
        FROM selfology.user_answers_new ua
        JOIN selfology.onboarding_sessions os ON ua.session_id = os.id
        WHERE ua.id = 14
    """

    async with db_service.get_connection() as conn:
        answer_row = await conn.fetchrow(query)

    if not answer_row:
        logger.error("❌ Answer 14 not found")
        await db_service.close()
        return

    user_id = answer_row['user_id']
    question_id = answer_row['question_json_id']
    user_answer = answer_row['raw_answer']

    logger.info(f"✅ Found answer 14:")
    logger.info(f"   User: {user_id}")
    logger.info(f"   Question: {question_id}")
    logger.info(f"   Answer: {user_answer}")

    # Получаем вопрос из Question Core
    question = question_core.get_question(question_id)

    if not question:
        logger.error(f"❌ Question {question_id} not found in core")
        await db_service.close()
        return

    logger.info(f"✅ Question loaded: {question['text'][:50]}...")

    # === ШАГ 1: АНАЛИЗ ОТВЕТА ===
    logger.info("\n" + "="*80)
    logger.info("🔬 STEP 1: ANALYZING ANSWER")
    logger.info("="*80)

    # Формируем контекст пользователя
    user_context = {
        "user_id": user_id,
        "answer_id": 14,
        "question_number": 14,
        "answer_length": len(user_answer),
        "previous_answers_count": 13,
        "session_started": "2025-10-01T20:28:00",
        "previous_domains": []
    }

    # Анализируем
    analysis_result = await analyzer.analyze_answer(
        question_data=question,
        user_answer=user_answer,
        user_context=user_context
    )

    if not analysis_result:
        logger.error("❌ Analysis failed")
        await db_service.close()
        return

    logger.info(f"✅ Analysis completed:")
    logger.info(f"   Quality: {analysis_result.get('quality_score', 0):.2f}")
    logger.info(f"   Model: {analysis_result.get('processing_metadata', {}).get('model_used')}")

    # === ШАГ 2: ОБНОВЛЕНИЕ DIGITAL PERSONALITY ===
    logger.info("\n" + "="*80)
    logger.info("🧬 STEP 2: UPDATING DIGITAL PERSONALITY")
    logger.info("="*80)

    # Получаем текущую личность
    current_personality = await personality_dao.get_personality(user_id)

    if not current_personality:
        logger.error("❌ No personality found")
        await db_service.close()
        return

    logger.info(f"✅ Current personality loaded (completeness: {current_personality.get('completeness_score', 0):.2%})")

    # Извлекаем новую информацию
    extracted = await personality_extractor.extract_from_answer(
        question_text=question['text'],
        user_answer=user_answer,
        question_metadata=question.get('classification', {}),
        existing_personality=current_personality
    )

    import json
    if isinstance(extracted, str):
        extracted = json.loads(extracted)

    logger.info(f"✅ Extracted personality data")

    # Объединяем с существующей личностью
    updated_personality = personality_extractor.merge_extractions(current_personality, extracted)

    # Сохраняем
    await personality_dao.update_personality(user_id, updated_personality, merge=False)

    logger.info(f"✅ Personality updated")

    # === ШАГ 3: ВЕКТОРИЗАЦИЯ ===
    logger.info("\n" + "="*80)
    logger.info("📈 STEP 3: CREATING VECTORS")
    logger.info("="*80)

    # Создаём векторы
    vector_success = await embedding_creator.create_personality_vector(
        user_id=user_id,
        analysis_result=analysis_result,
        is_update=True  # Это обновление, не первый вектор
    )

    if vector_success:
        logger.info("✅ Vectorization completed successfully!")
    else:
        logger.warning("⚠️ Vectorization returned False")

    # === ПРОВЕРКА ===
    logger.info("\n" + "="*80)
    logger.info("🔍 VERIFICATION")
    logger.info("="*80)

    import requests

    # Проверяем personality_profiles
    response = requests.get(f"http://localhost:6333/collections/personality_profiles/points/{user_id}")
    if response.status_code == 200:
        data = response.json()
        last_updated = data['result']['payload'].get('last_updated')
        logger.info(f"✅ personality_profiles: Vector exists (last_updated: {last_updated})")
    else:
        logger.error(f"❌ personality_profiles: Vector not found")

    # Проверяем quick_match
    response = requests.get(f"http://localhost:6333/collections/quick_match/points/{user_id}")
    if response.status_code == 200:
        logger.info(f"✅ quick_match: Vector exists")
    else:
        logger.error(f"❌ quick_match: Vector not found")

    # Проверяем personality_evolution
    response = requests.get(f"http://localhost:6333/collections/personality_evolution")
    if response.status_code == 200:
        data = response.json()
        count = data['result']['points_count']
        logger.info(f"ℹ️  personality_evolution: {count} breakthrough moments stored")

    logger.info("\n" + "="*80)
    logger.info("🎉 ANSWER 14 REPROCESSED SUCCESSFULLY!")
    logger.info("="*80)

    await db_service.close()


if __name__ == "__main__":
    asyncio.run(reprocess_answer_14())
