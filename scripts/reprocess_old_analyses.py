#!/usr/bin/env python3
"""
Перезапуск старых анализов без personality_summary

Берет ответы #36, #39, #40 и создает новые анализы с personality_summary
"""

import asyncio
import asyncpg
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from selfology_bot.analysis.answer_analyzer import AnswerAnalyzer

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "n8n",
    "password": "sS67wM+1zMBRFHAW4kj9HwFl5J6+veo7Nirx0/I+oiU=",
    "database": "n8n"
}

# Answer IDs для перезапуска
ANSWERS_TO_REPROCESS = [36, 39, 40]


async def reprocess_answer(answer_id: int, conn: asyncpg.Connection, analyzer: AnswerAnalyzer):
    """Перезапустить анализ одного ответа"""

    print(f"\n🔄 Перезапуск анализа для ответа #{answer_id}")
    print("="*60)

    # Получить ответ из БД
    answer = await conn.fetchrow("""
        SELECT
            ua.id,
            ua.question_json_id,
            ua.raw_answer,
            ua.session_id,
            os.user_id
        FROM selfology.user_answers_new ua
        JOIN selfology.onboarding_sessions os ON ua.session_id = os.id
        WHERE ua.id = $1
    """, answer_id)

    if not answer:
        print(f"❌ Ответ #{answer_id} не найден")
        return False

    # Для перезапуска используем placeholder вопроса (текст не критичен для personality_summary)
    question_text = f"Вопрос из базы (ID: {answer['question_json_id']})"

    print(f"📝 Вопрос ID: {answer['question_json_id']}")
    print(f"💬 Ответ: {answer['raw_answer'][:80]}...")

    # Запустить анализ
    try:
        print(f"\n🤖 Запуск AI анализа...")

        analysis_result = await analyzer.analyze_answer(
            question_text=question_text,
            user_answer=answer['raw_answer'],
            question_metadata={
                "domain": "UNKNOWN",
                "depth_level": "surface",
                "energy_dynamic": "neutral"
            },
            context={
                "answer_history": [],
                "question_history": [],
                "user_profile": None
            }
        )

        # Проверить personality_summary
        if "personality_summary" in analysis_result:
            print(f"✅ personality_summary создан:")
            print(f"   nano: {analysis_result['personality_summary'].get('nano', 'N/A')[:60]}...")
        else:
            print(f"❌ personality_summary НЕ создан!")
            return False

        # Сохранить новый анализ
        print(f"\n💾 Сохранение анализа в БД...")

        analysis_id = await conn.fetchval("""
            INSERT INTO selfology.answer_analysis (
                user_answer_id,
                raw_ai_response,
                model_used,
                analysis_version,
                status
            ) VALUES ($1, $2, $3, $4, $5)
            RETURNING id
        """,
            answer_id,
            json.dumps(analysis_result, ensure_ascii=False),
            analysis_result['processing_metadata']['model_used'],
            analysis_result.get('analysis_version', '2.0'),
            'completed'
        )

        print(f"✅ Новый анализ сохранен с ID: {analysis_id}")

        # Обновить статус ответа
        await conn.execute("""
            UPDATE selfology.user_answers_new
            SET analysis_status = 'analyzed'
            WHERE id = $1
        """, answer_id)

        print(f"✅ Статус обновлен на 'analyzed'")

        return True

    except Exception as e:
        print(f"❌ Ошибка при анализе: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Точка входа"""

    print("\n" + "🔄"*30)
    print("ПЕРЕЗАПУСК СТАРЫХ АНАЛИЗОВ")
    print("🔄"*30)

    print(f"\nБудут перезапущены ответы: {ANSWERS_TO_REPROCESS}")
    print("Старые анализы НЕ будут удалены (для истории)")

    # Инициализация
    conn = await asyncpg.connect(**DB_CONFIG)
    analyzer = AnswerAnalyzer()

    try:
        results = []

        for answer_id in ANSWERS_TO_REPROCESS:
            success = await reprocess_answer(answer_id, conn, analyzer)
            results.append((answer_id, success))

        # Итоги
        print("\n" + "="*60)
        print("📊 ИТОГИ ПЕРЕЗАПУСКА")
        print("="*60)

        success_count = sum(1 for _, success in results if success)

        for answer_id, success in results:
            status = "✅ OK" if success else "❌ FAIL"
            print(f"  Ответ #{answer_id}: {status}")

        print(f"\nУспешно: {success_count}/{len(results)}")

        if success_count == len(results):
            print("\n🎉 Все анализы успешно перезапущены!")
        else:
            print("\n⚠️ Некоторые анализы не удалось перезапустить")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
