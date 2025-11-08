#!/usr/bin/env python3
"""Тест create_personality_vector с детальным traceback"""

import asyncio
import os
import sys
import asyncpg
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from selfology_bot.analysis.embedding_creator import EmbeddingCreator


async def test_one_answer():
    """Тест для одного ответа"""

    # Получаем данные из БД
    conn = await asyncpg.connect(
        host="localhost",
        port=5432,
        user="n8n",
        password="sS67wM+1zMBRFHAW4kj9HwFl5J6+veo7Nirx0/I+oiU=",
        database="n8n"
    )

    row = await conn.fetchrow("""
        SELECT
            aa.id,
            aa.user_answer_id,
            aa.raw_ai_response,
            ua.raw_answer,
            ua.question_json_id
        FROM selfology.answer_analysis aa
        JOIN selfology.user_answers_new ua ON aa.user_answer_id = ua.id
        WHERE aa.id = 101
    """)

    await conn.close()

    raw_ai_response = row['raw_ai_response']
    if isinstance(raw_ai_response, str):
        raw_ai_response = json.loads(raw_ai_response)

    personality_summary = raw_ai_response.get('personality_summary', {})
    personality_traits = raw_ai_response.get('personality_traits', {})

    analysis_result = {
        "personality_summary": personality_summary,
        "personality_traits": personality_traits,
        "answer_text": row['raw_answer'],
        "question_id": row['question_json_id'],
        "timestamp": datetime.now().isoformat()
    }

    print(f"📝 Testing answer #{row['user_answer_id']}")
    print(f"   personality_summary keys: {list(personality_summary.keys())}")
    print(f"   narrative: {personality_summary.get('narrative', '')[:50]}...")
    print(f"   nano: {personality_summary.get('nano', '')}")

    # Создаем векторы
    creator = EmbeddingCreator()

    print(f"\n🔬 Вызываем create_personality_vector...")

    try:
        result = await creator.create_personality_vector(
            user_id=98005572,
            analysis_result=analysis_result,
            is_update=True
        )

        print(f"\n✅ Результат: {result}")

        if result:
            print("🎉 УСПЕХ!")
        else:
            print("❌ Возвращен False")

            # Проверяем статистику embeddings
            print(f"\n📊 Статистика embeddings:")
            print(f"   API calls success: {creator.embedding_stats.get('api_calls_success', 0)}")
            print(f"   API calls failed: {creator.embedding_stats.get('api_calls_failed', 0)}")
            print(f"   Cache hits: {creator.embedding_stats.get('cache_hits', 0)}")
            print(f"   Total cost: ${creator.embedding_stats.get('total_cost', 0):.6f}")

    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_one_answer())
