#!/usr/bin/env python3
"""
Backfill существующих анализов в semantic_knowledge и emotional_thematic

Читает из selfology.answer_analysis и создает embeddings через OpenAI
"""

import asyncio
import asyncpg
from tqdm import tqdm
import sys
import os
import json

# Add project root to path
sys.path.insert(0, '/home/ksnk/microservices/critical/selfology-bot')

from dotenv import load_dotenv
load_dotenv()

from selfology_bot.services.vector_storage_service import get_vector_storage


async def backfill_semantic_emotional():
    """Backfill all analyses to semantic_knowledge and emotional_thematic"""

    # Connect to PostgreSQL
    conn = await asyncpg.connect(
        host='localhost',
        port=5434,
        user='selfology_user',
        password='selfology_secure_2024',
        database='selfology'
    )

    # Get all analyses with user_id
    analyses = await conn.fetch("""
        SELECT
            aa.id,
            aa.user_answer_id,
            s.user_id,
            a.question_json_id as question_id,
            a.raw_answer,
            aa.psychological_insights,
            aa.trait_scores,
            aa.emotional_state,
            aa.processed_at
        FROM selfology.answer_analysis aa
        JOIN selfology.user_answers_new a ON aa.user_answer_id = a.id
        JOIN selfology.onboarding_sessions s ON a.session_id = s.id
        ORDER BY aa.processed_at
    """)

    print(f"📊 Found {len(analyses)} analyses to backfill")

    if not analyses:
        print("❌ No analyses found")
        await conn.close()
        return

    # Initialize storage
    storage = get_vector_storage()

    # Counters
    semantic_success = 0
    emotional_success = 0
    errors = 0

    for analysis in tqdm(analyses, desc="Backfilling"):
        try:
            user_id = analysis['user_id']
            answer_id = analysis['user_answer_id']
            question_id = analysis['question_id']

            # 1. Store in semantic_knowledge
            analysis_text = ""
            if analysis['psychological_insights']:
                analysis_text += f"Инсайты: {analysis['psychological_insights']}. "

            # trait_scores - это JSONB
            traits = analysis['trait_scores']
            if traits and isinstance(traits, dict) and traits:
                analysis_text += f"Черты: {json.dumps(traits, ensure_ascii=False)}. "

            if analysis['emotional_state']:
                analysis_text += f"Эмоции: {analysis['emotional_state']}. "

            if analysis_text and len(analysis_text) > 10:
                await storage.store_semantic(
                    user_id=user_id,
                    analysis_text=analysis_text,
                    turn_id=str(answer_id),
                    metadata={
                        'question_id': question_id,
                        'answer_id': answer_id,
                        'original_processed_at': analysis['processed_at'].isoformat() if analysis['processed_at'] else None,
                        'backfilled': True
                    }
                )
                semantic_success += 1

            # 2. Store in emotional_thematic
            if analysis['emotional_state'] and analysis['raw_answer']:
                await storage.store_emotional(
                    user_id=user_id,
                    text=analysis['raw_answer'][:500],  # Truncate long answers
                    emotion=analysis['emotional_state'],
                    intensity=0.5,  # Default intensity for historical
                    metadata={
                        'question_id': question_id,
                        'answer_id': answer_id,
                        'backfilled': True
                    }
                )
                emotional_success += 1

        except Exception as e:
            errors += 1
            print(f"\n❌ Error processing analysis {analysis['id']}: {e}")

    await conn.close()

    # Print summary
    print(f"\n✅ Backfill complete!")
    print(f"   semantic_knowledge: {semantic_success}")
    print(f"   emotional_thematic: {emotional_success}")
    print(f"   Errors: {errors}")

    # Check collection stats
    import requests
    for collection in ['semantic_knowledge', 'emotional_thematic']:
        resp = requests.get(f"http://localhost:6333/collections/{collection}")
        points = resp.json()['result']['points_count']
        print(f"\n📊 {collection} now has {points} points")


if __name__ == "__main__":
    print("🚀 Starting semantic_knowledge + emotional_thematic backfill...")
    asyncio.run(backfill_semantic_emotional())
