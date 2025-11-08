"""
Ретроспективный анализ существующих ответов

Запускает полный анализ для всех ответов со статусом 'pending'
"""

import asyncio
import logging
import sys
from pathlib import Path

# Добавляем пути
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent / "intelligent_question_core"))

from selfology_bot.database import DatabaseService, OnboardingDAO
from selfology_bot.analysis import AnswerAnalyzer
from intelligent_question_core.api.core_api import SelfologyQuestionCore

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def analyze_pending_answers(user_id: int = None):
    """
    Анализирует все ответы со статусом 'pending'

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
    analyzer = AnswerAnalyzer()

    # Загружаем вопросы
    questions_file = str(Path(__file__).parent.parent / "intelligent_question_core" / "data" / "selfology_intelligent_core.json")
    question_core = SelfologyQuestionCore(questions_file)

    logger.info("✅ Components initialized")

    # Получаем pending ответы
    async with db_service.get_connection() as conn:
        if user_id:
            query = """
                SELECT ua.id, ua.session_id, ua.question_json_id, ua.raw_answer, os.user_id
                FROM selfology.user_answers_new ua
                JOIN selfology.onboarding_sessions os ON ua.session_id = os.id
                WHERE ua.analysis_status = 'pending' AND os.user_id = $1
                ORDER BY ua.answered_at
            """
            rows = await conn.fetch(query, user_id)
        else:
            query = """
                SELECT ua.id, ua.session_id, ua.question_json_id, ua.raw_answer, os.user_id
                FROM selfology.user_answers_new ua
                JOIN selfology.onboarding_sessions os ON ua.session_id = os.id
                WHERE ua.analysis_status = 'pending'
                ORDER BY ua.answered_at
            """
            rows = await conn.fetch(query)

    total = len(rows)
    logger.info(f"📊 Found {total} pending answers to analyze")

    if total == 0:
        logger.info("✅ No pending answers - all done!")
        return

    # Анализируем каждый ответ
    for idx, row in enumerate(rows, 1):
        answer_id = row['id']
        session_id = row['session_id']
        question_id = row['question_json_id']
        answer_text = row['raw_answer']
        uid = row['user_id']

        logger.info(f"\n{'='*60}")
        logger.info(f"🔬 Analyzing answer {idx}/{total}")
        logger.info(f"   User: {uid}, Answer ID: {answer_id}, Question: {question_id}")
        logger.info(f"   Answer: {answer_text[:80]}...")

        try:
            # Получаем данные вопроса
            question_data = question_core.get_question(question_id)

            if not question_data:
                logger.error(f"❌ Question {question_id} not found in question core")
                continue

            # Минимальный контекст для анализа
            user_context = {
                "user_id": uid,
                "answer_id": answer_id,
                "question_number": idx,
                "session_started": None,
                "previous_answers_count": idx - 1,
                "trust_level": 0.5,
                "energy_level": 0.7,
                "fatigue_level": 0.0
            }

            # Запускаем анализ
            logger.info("   🧠 Running AI analysis...")
            analysis_result = await analyzer.analyze_answer(
                question_data=question_data,
                user_answer=answer_text,
                user_context=user_context
            )

            # Сохраняем результат
            logger.info("   💾 Saving analysis to database...")
            analysis_id = await dao.save_analysis_result(answer_id, analysis_result)

            logger.info(f"   ✅ Analysis saved with ID {analysis_id}")
            logger.info(f"   📊 Quality score: {analysis_result.get('quality_metadata', {}).get('overall_reliability', 0):.2f}")

        except Exception as e:
            logger.error(f"   ❌ Failed to analyze answer {answer_id}: {e}", exc_info=True)
            continue

    logger.info(f"\n{'='*60}")
    logger.info(f"🎉 Retroactive analysis completed!")
    logger.info(f"   Processed: {total} answers")

    # Финальная статистика
    async with db_service.get_connection() as conn:
        analyzed_count = await conn.fetchval("""
            SELECT COUNT(*) FROM selfology.answer_analysis
        """)

        logger.info(f"   Total analyses in DB: {analyzed_count}")

    await db_service.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Retroactive answer analysis')
    parser.add_argument('--user-id', type=int, help='Specific user ID to analyze')
    args = parser.parse_args()

    asyncio.run(analyze_pending_answers(args.user_id))
