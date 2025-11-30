#!/usr/bin/env python3
"""
Обработать один конкретный ответ с нуля (создать analysis + векторы + DP)
"""

import asyncio
import os
import sys
import asyncpg
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from selfology_bot.services.onboarding.orchestrator import OnboardingOrchestrator
from selfology_bot.database.service import DatabaseService


async def process_answer(answer_id: int):
    """Обработать answer с нуля"""

    print(f"\n{'='*60}")
    print(f"🔄 PROCESSING ANSWER #{answer_id}")
    print(f"{'='*60}\n")

    # Подключаемся к БД
    conn = await asyncpg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        user=os.getenv("DB_USER", "n8n"),
        password=os.getenv("DB_PASSWORD", "sS67wM+1zMBRFHAW4kj9HwFl5J6+veo7Nirx0/I+oiU="),
        database=os.getenv("DB_NAME", "n8n")
    )

    try:
        # Получаем данные ответа
        row = await conn.fetchrow("""
            SELECT
                ua.id,
                ua.raw_answer,
                ua.question_json_id,
                os.user_id,
                os.id as session_id
            FROM selfology.user_answers_new ua
            JOIN selfology.onboarding_sessions os ON ua.session_id = os.id
            WHERE ua.id = $1
        """, answer_id)

        if not row:
            print(f"❌ Answer #{answer_id} not found!")
            return False

        user_id = row['user_id']
        raw_answer = row['raw_answer']
        question_json_id = row['question_json_id']
        session_id = row['session_id']

        print(f"📝 Answer details:")
        print(f"   User ID: {user_id}")
        print(f"   Question: {question_json_id}")
        print(f"   Answer length: {len(raw_answer)} chars")
        print(f"   Session ID: {session_id}")

        # Загружаем данные вопроса из question core
        print(f"\n🔍 Loading question data...")
        from intelligent_question_core.api.core_api import SelfologyQuestionCore
        question_core = SelfologyQuestionCore()
        question_data = question_core.get_question(question_json_id)

        if not question_data:
            print(f"❌ Question {question_json_id} not found in core!")
            return False

        print(f"✅ Question loaded: {question_data.get('text', '')[:50]}...")

        # Инициализируем Orchestrator
        print(f"\n🚀 Initializing Orchestrator...")
        orchestrator = OnboardingOrchestrator()

        # Инициализируем Database вручную (как в start_onboarding)
        orchestrator.db_service = DatabaseService(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 5432)),
            user=os.getenv("DB_USER", "n8n"),
            password=os.getenv("DB_PASSWORD", "sS67wM+1zMBRFHAW4kj9HwFl5J6+veo7Nirx0/I+oiU="),
            database=os.getenv("DB_NAME", "n8n"),
            schema="selfology"
        )
        await orchestrator.db_service.initialize()

        # Создаем DAOs
        from selfology_bot.database.onboarding_dao import OnboardingDAO
        from selfology_bot.database.digital_personality_dao import DigitalPersonalityDAO

        orchestrator.onboarding_dao = OnboardingDAO(orchestrator.db_service)
        orchestrator.personality_dao = DigitalPersonalityDAO(orchestrator.db_service)

        # Создаём минимальную сессию в памяти для обработки
        mock_session = {
            "user_id": user_id,
            "session_id": session_id,
            "answer_history": [],  # Пустая - не критично для анализа
            "question_history": []
        }

        print(f"\n🔬 Starting deep analysis pipeline...")

        # Запускаем deep_analysis_pipeline напрямую
        await orchestrator._deep_analysis_pipeline(
            user_id=user_id,
            question_id=question_json_id,
            answer=raw_answer,
            question_data=question_data,
            session=mock_session,
            answer_id=answer_id
        )

        print(f"\n{'='*60}")
        print(f"✅ PROCESSING COMPLETED!")
        print(f"{'='*60}\n")

        return True

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        await conn.close()


async def main():
    if len(sys.argv) < 2:
        print("Usage: python process_single_answer.py <answer_id>")
        print("\nExample:")
        print("  python process_single_answer.py 41")
        sys.exit(1)

    answer_id = int(sys.argv[1])
    success = await process_answer(answer_id)

    if success:
        print("💡 Теперь проверьте через monitor_onboarding.py")
    else:
        print("❌ Обработка не удалась")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
