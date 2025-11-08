#!/usr/bin/env python3
"""
Перезапуск анализа для одного ответа

Использует НОВЫЙ код AnswerAnalyzer с personality_summary
"""

import asyncio
import asyncpg
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from selfology_bot.analysis.answer_analyzer import AnswerAnalyzer
from selfology_bot.database.onboarding_dao import OnboardingDAO
from selfology_bot.database.service import DatabaseService

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "n8n",
    "password": "sS67wM+1zMBRFHAW4kj9HwFl5J6+veo7Nirx0/I+oiU=",
    "database": "n8n"
}


async def reprocess_answer(answer_id: int):
    """
    Перезапускает анализ для указанного ответа

    Args:
        answer_id: ID ответа в user_answers_new
    """

    print(f"\n🔄 Перезапуск анализа для ответа {answer_id}")
    print("="*60)

    conn = await asyncpg.connect(**DB_CONFIG)

    try:
        # 1. Получаем данные ответа
        answer_data = await conn.fetchrow("""
            SELECT
                ua.id,
                ua.raw_answer,
                ua.question_json_id,
                ua.session_id,
                os.user_id,
                os.questions_asked
            FROM selfology.user_answers_new ua
            JOIN selfology.onboarding_sessions os ON ua.session_id = os.id
            WHERE ua.id = $1
        """, answer_id)

        if not answer_data:
            print(f"❌ Ответ {answer_id} не найден")
            return False

        print(f"✅ Найден ответ пользователя {answer_data['user_id']}")
        print(f"📝 Текст ответа: {answer_data['raw_answer'][:100]}...")

        # 2. Создаем тестовый вопрос (полные вопросы в JSON файле, не в БД)
        question_full = {
            "id": answer_data['question_json_id'],
            "text": "Что самое главное было в вашем году?",
            "classification": {
                "domain": "IDENTITY",
                "depth_level": "CONSCIOUS",
                "energy_dynamic": "NEUTRAL"
            },
            "psychology": {
                "complexity": 0.6,
                "emotional_weight": 0.5,
                "insight_potential": 0.7,
                "trust_requirement": 0.4,
                "safety_level": 0.8
            }
        }

        # 3. Запускаем анализ
        print(f"\n🧠 Запуск AI анализа...")

        analyzer = AnswerAnalyzer()

        user_context = {
            "user_id": answer_data['user_id'],
            "question_number": answer_data['questions_asked'],
            "previous_domains": [],
            "trust_level": 0.5,
            "energy_level": 0.7
        }

        analysis_result = await analyzer.analyze_answer(
            question_data=question_full,
            user_answer=answer_data['raw_answer'],
            user_context=user_context
        )

        print(f"✅ Анализ завершен")
        print(f"📋 Ключи результата: {list(analysis_result.keys())}")

        # 4. Проверяем наличие personality_summary
        if "personality_summary" in analysis_result:
            print(f"✅ personality_summary СОЗДАН!")
            summary = analysis_result["personality_summary"]
            print(f"  - nano: {summary.get('nano', 'N/A')[:60]}...")
            print(f"  - narrative: {summary.get('narrative', 'N/A')[:60]}...")
        else:
            print(f"❌ personality_summary НЕ создан")
            return False

        # 5. Сохраняем в БД через DAO
        print(f"\n💾 Сохранение в БД...")

        db_service = DatabaseService(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            database=DB_CONFIG["database"]
        )
        await db_service.initialize()

        dao = OnboardingDAO(db_service)

        analysis_id = await dao.save_analysis_result(
            user_answer_id=answer_id,
            analysis_result=analysis_result
        )

        print(f"✅ Анализ сохранен с ID {analysis_id}")

        # 6. Проверяем что сохранилось
        saved = await conn.fetchrow("""
            SELECT raw_ai_response
            FROM selfology.answer_analysis
            WHERE id = $1
        """, analysis_id)

        if saved:
            raw = saved['raw_ai_response']
            if isinstance(raw, str):
                raw = json.loads(raw)

            if "personality_summary" in raw:
                print(f"✅ personality_summary СОХРАНЕН в БД!")
                return True
            else:
                print(f"❌ personality_summary НЕ сохранился в БД")
                print(f"📋 Сохраненные ключи: {list(raw.keys())}")
                return False
        else:
            print(f"❌ Анализ не найден в БД")
            return False

    finally:
        await conn.close()


async def main():
    """Точка входа"""

    if len(sys.argv) < 2:
        print("Usage: python reprocess_single_answer.py <answer_id>")
        print("\nExample:")
        print("  python reprocess_single_answer.py 35")
        sys.exit(1)

    answer_id = int(sys.argv[1])

    success = await reprocess_answer(answer_id)

    if success:
        print("\n" + "="*60)
        print("🎉 УСПЕШНО! Анализ перезапущен с personality_summary!")
        print("="*60)
        return 0
    else:
        print("\n" + "="*60)
        print("❌ ОШИБКА! Проверьте логи выше")
        print("="*60)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
