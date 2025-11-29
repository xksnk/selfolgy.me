#!/usr/bin/env python3
"""
Backfill существующих ответов в episodic_memory коллекцию Qdrant

Читает из selfology.user_answers_new и создает embeddings через RuBERT
"""

import asyncio
import asyncpg
from tqdm import tqdm
import sys
import os

# Add project root to path
sys.path.insert(0, '/home/ksnk/microservices/critical/selfology-bot')

from selfology_bot.services.vector_storage_service import get_vector_storage


async def backfill_episodic():
    """Backfill all user answers to episodic_memory"""

    # Connect to PostgreSQL
    conn = await asyncpg.connect(
        host='localhost',
        port=5434,
        user='selfology_user',
        password='selfology_secure_2024',
        database='selfology'
    )

    # Get all answers with user_id from sessions
    answers = await conn.fetch("""
        SELECT
            a.id,
            s.user_id,
            a.question_json_id as question_id,
            a.raw_answer,
            a.answered_at as created_at,
            aa.psychological_insights
        FROM selfology.user_answers_new a
        JOIN selfology.onboarding_sessions s ON a.session_id = s.id
        LEFT JOIN selfology.answer_analysis aa ON a.id = aa.user_answer_id
        ORDER BY a.answered_at
    """)

    print(f"📊 Found {len(answers)} answers to backfill")

    if not answers:
        print("❌ No answers found")
        await conn.close()
        return

    # Initialize storage
    storage = get_vector_storage()

    # Process each answer
    success = 0
    errors = 0

    for answer in tqdm(answers, desc="Backfilling"):
        try:
            # Skip empty answers
            if not answer['raw_answer'] or len(answer['raw_answer'].strip()) < 5:
                continue

            # Store in episodic_memory
            point_id = await storage.store_episodic(
                user_id=answer['user_id'],
                text=answer['raw_answer'],
                metadata={
                    'question_id': answer['question_id'],
                    'answer_id': answer['id'],
                    'original_created_at': answer['created_at'].isoformat() if answer['created_at'] else None,
                    'has_insights': bool(answer['psychological_insights'])
                }
            )
            success += 1

        except Exception as e:
            errors += 1
            print(f"\n❌ Error processing answer {answer['id']}: {e}")

    await conn.close()

    # Print summary
    print(f"\n✅ Backfill complete!")
    print(f"   Success: {success}")
    print(f"   Errors: {errors}")
    print(f"   Skipped: {len(answers) - success - errors}")

    # Check collection stats
    import requests
    resp = requests.get("http://localhost:6333/collections/episodic_memory")
    points = resp.json()['result']['points_count']
    print(f"\n📊 episodic_memory now has {points} points")


if __name__ == "__main__":
    print("🚀 Starting episodic_memory backfill...")
    asyncio.run(backfill_episodic())
