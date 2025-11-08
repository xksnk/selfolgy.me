"""
Извлечение цифровой личности из существующих ответов

Берёт все ответы пользователя и создаёт детальную цифровую личность
с конкретной информацией (увлечения, страхи, цели, барьеры, отношения)
"""

import asyncio
import logging
import sys
import json
from pathlib import Path

# Добавляем пути
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent / "intelligent_question_core"))

from selfology_bot.database import DatabaseService, OnboardingDAO, DigitalPersonalityDAO
from selfology_bot.analysis import PersonalityExtractor
from intelligent_question_core.api.core_api import SelfologyQuestionCore

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def extract_personality_from_answers(user_id: int = None):
    """
    Извлекает цифровую личность из всех ответов пользователя

    Args:
        user_id: ID пользователя (если None - все пользователи)
    """

    # Инициализация компонентов
    logger.info("🔧 Initializing components...")

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
    extractor = PersonalityExtractor()

    # Загружаем Question Core для получения текстов вопросов
    core_file_path = str(Path(__file__).parent.parent / "intelligent_question_core" / "data" / "selfology_intelligent_core.json")
    question_core = SelfologyQuestionCore(core_file_path)

    logger.info("✅ Components initialized")

    # Получаем все ответы
    async with db_service.get_connection() as conn:
        if user_id:
            query = """
                SELECT
                    ua.id as answer_id,
                    ua.session_id,
                    ua.question_json_id,
                    ua.raw_answer,
                    os.user_id
                FROM selfology.user_answers_new ua
                JOIN selfology.onboarding_sessions os ON ua.session_id = os.id
                WHERE os.user_id = $1
                ORDER BY ua.id
            """
            rows = await conn.fetch(query, user_id)
        else:
            query = """
                SELECT
                    ua.id as answer_id,
                    ua.session_id,
                    ua.question_json_id,
                    ua.raw_answer,
                    os.user_id
                FROM selfology.user_answers_new ua
                JOIN selfology.onboarding_sessions os ON ua.session_id = os.id
                ORDER BY os.user_id, ua.id
            """
            rows = await conn.fetch(query)

    total = len(rows)
    logger.info(f"📊 Found {total} answers to process")

    if total == 0:
        logger.info("✅ No answers found")
        return

    # Группируем по пользователям
    user_answers = {}
    for row in rows:
        uid = row['user_id']
        if uid not in user_answers:
            user_answers[uid] = []
        user_answers[uid].append(dict(row))

    logger.info(f"👥 Found {len(user_answers)} unique users")

    # Обрабатываем каждого пользователя
    for uid, answers in user_answers.items():
        logger.info(f"\n{'='*60}")
        logger.info(f"👤 Processing user {uid} ({len(answers)} answers)")

        # Проверяем, есть ли уже личность
        existing_personality = await personality_dao.get_personality(uid)

        if existing_personality:
            logger.info(f"   ℹ️ Found existing personality (completeness: {existing_personality.get('completeness_score', 0):.2f})")
            logger.info(f"   ℹ️ Will merge new extractions")
        else:
            logger.info(f"   ℹ️ No existing personality - will create new")

        # Обрабатываем каждый ответ
        accumulated_personality = existing_personality if existing_personality else None

        for idx, answer_data in enumerate(answers, 1):
            question_id = answer_data['question_json_id']
            user_answer = answer_data['raw_answer']

            # Получаем данные вопроса из Question Core
            question = question_core.get_question(question_id)

            if not question:
                logger.warning(f"   ⚠️ Question {question_id} not found in core - skipping")
                continue

            logger.info(f"   [{idx}/{len(answers)}] Extracting from answer to: {question['text'][:50]}...")

            try:
                # Извлекаем информацию
                extracted = await extractor.extract_from_answer(
                    question_text=question['text'],
                    user_answer=user_answer,
                    question_metadata=question.get('classification', {}),
                    existing_personality=accumulated_personality
                )

                # Парсим JSON если это строка
                if isinstance(extracted, str):
                    extracted = json.loads(extracted)

                # Объединяем с накопленной личностью
                if accumulated_personality:
                    accumulated_personality = extractor.merge_extractions(
                        accumulated_personality,
                        extracted
                    )
                else:
                    accumulated_personality = extracted

                # Логируем что извлекли
                extracted_items = sum([
                    len(extracted.get('interests', [])),
                    len(extracted.get('skills', [])),
                    len(extracted.get('goals', [])),
                    len(extracted.get('barriers', [])),
                    len(extracted.get('relationships', [])),
                    len(extracted.get('values', [])),
                    len(extracted.get('health', [])),
                    len(extracted.get('current_state', []))
                ])

                if extracted_items > 0:
                    logger.info(f"   ✅ Extracted {extracted_items} items")
                    # Показываем примеры
                    for category in ['interests', 'goals', 'barriers']:
                        items = extracted.get(category, [])
                        if items:
                            logger.info(f"      {category}: {items[:2]}")  # Первые 2
                else:
                    logger.info(f"   ℹ️ No specific items extracted (generic answer)")

            except Exception as e:
                logger.error(f"   ❌ Error extracting from answer {answer_data['answer_id']}: {e}", exc_info=True)
                continue

        # Сохраняем итоговую личность в БД
        try:
            if existing_personality:
                await personality_dao.update_personality(uid, accumulated_personality, merge=False)
                logger.info(f"\n   ✅ Updated digital personality for user {uid}")
            else:
                await personality_dao.create_personality(uid, accumulated_personality)
                logger.info(f"\n   ✅ Created digital personality for user {uid}")

            # Показываем краткое описание
            summary = await personality_dao.get_personality_summary(uid)
            if summary:
                logger.info(f"\n   📋 Personality Summary:")
                for line in summary.split('\n')[:10]:  # Первые 10 строк
                    logger.info(f"      {line}")

        except Exception as e:
            logger.error(f"   ❌ Error saving personality for user {uid}: {e}", exc_info=True)

    logger.info(f"\n{'='*60}")
    logger.info(f"🎉 Personality extraction completed!")
    logger.info(f"   Processed {len(user_answers)} users")

    await db_service.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Extract digital personality from user answers')
    parser.add_argument('--user-id', type=int, help='Specific user ID')
    args = parser.parse_args()

    asyncio.run(extract_personality_from_answers(args.user_id))
