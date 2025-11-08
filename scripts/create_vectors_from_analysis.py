"""
Создание векторов личности в Qdrant из существующих анализов

Берёт все проанализированные ответы и создаёт векторы для каждого пользователя
"""

import asyncio
import logging
import sys
from pathlib import Path

# Добавляем пути
sys.path.append(str(Path(__file__).parent.parent))

from selfology_bot.database import DatabaseService, OnboardingDAO
from selfology_bot.analysis import EmbeddingCreator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def create_vectors_for_analyzed_answers(user_id: int = None):
    """
    Создаёт векторы для всех анализов

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
    embedding_creator = EmbeddingCreator()

    # Setup Qdrant collections
    logger.info("🔧 Setting up Qdrant collections...")
    setup_success = await embedding_creator.setup_qdrant_collections()
    if not setup_success:
        logger.error("❌ Failed to setup Qdrant collections")
        return

    logger.info("✅ Components initialized")

    # Получаем все анализы
    async with db_service.get_connection() as conn:
        if user_id:
            query = """
                SELECT
                    aa.id as analysis_id,
                    aa.user_answer_id,
                    aa.trait_scores,
                    aa.psychological_insights,
                    aa.emotional_state,
                    aa.ai_model_used,
                    aa.quality_score,
                    aa.confidence_score,
                    ua.session_id,
                    ua.question_json_id,
                    ua.raw_answer,
                    os.user_id
                FROM selfology.answer_analysis aa
                JOIN selfology.user_answers_new ua ON aa.user_answer_id = ua.id
                JOIN selfology.onboarding_sessions os ON ua.session_id = os.id
                WHERE os.user_id = $1 AND aa.trait_scores IS NOT NULL
                ORDER BY aa.id
            """
            rows = await conn.fetch(query, user_id)
        else:
            query = """
                SELECT
                    aa.id as analysis_id,
                    aa.user_answer_id,
                    aa.trait_scores,
                    aa.psychological_insights,
                    aa.emotional_state,
                    aa.ai_model_used,
                    aa.quality_score,
                    aa.confidence_score,
                    ua.session_id,
                    ua.question_json_id,
                    ua.raw_answer,
                    os.user_id
                FROM selfology.answer_analysis aa
                JOIN selfology.user_answers_new ua ON aa.user_answer_id = ua.id
                JOIN selfology.onboarding_sessions os ON ua.session_id = os.id
                WHERE aa.trait_scores IS NOT NULL
                ORDER BY aa.id
            """
            rows = await conn.fetch(query)

    total = len(rows)
    logger.info(f"📊 Found {total} analyses to vectorize")

    if total == 0:
        logger.info("✅ No analyses found")
        return

    # Группируем по пользователям
    user_analyses = {}
    for row in rows:
        uid = row['user_id']
        if uid not in user_analyses:
            user_analyses[uid] = []
        user_analyses[uid].append(dict(row))

    logger.info(f"👥 Found {len(user_analyses)} unique users")

    # Создаём векторы для каждого пользователя
    for uid, analyses in user_analyses.items():
        logger.info(f"\n{'='*60}")
        logger.info(f"👤 Processing user {uid} ({len(analyses)} analyses)")

        # Аккумулируем все trait_scores для создания полного профиля
        accumulated_traits = {
            "big_five": {},
            "dynamic_traits": {},
            "adaptive_traits": {},
            "domain_specific": {}
        }

        # Собираем все инсайты
        all_insights = []

        for idx, analysis in enumerate(analyses, 1):
            trait_scores = analysis['trait_scores']

            # Если это строка (не должно быть), парсим
            if isinstance(trait_scores, str):
                import json
                trait_scores = json.loads(trait_scores)

            # Аккумулируем черты (усредняем)
            for category in accumulated_traits.keys():
                if category in trait_scores and isinstance(trait_scores[category], dict):
                    for trait, value in trait_scores[category].items():
                        if isinstance(value, dict):
                            # domain_specific
                            if trait not in accumulated_traits[category]:
                                accumulated_traits[category][trait] = {}
                            for subtrait, subvalue in value.items():
                                if isinstance(subvalue, (int, float)):
                                    if subtrait not in accumulated_traits[category][trait]:
                                        accumulated_traits[category][trait][subtrait] = []
                                    accumulated_traits[category][trait][subtrait].append(subvalue)
                        elif isinstance(value, (int, float)):
                            if trait not in accumulated_traits[category]:
                                accumulated_traits[category][trait] = []
                            accumulated_traits[category][trait].append(value)

            # Собираем инсайты
            if analysis['psychological_insights']:
                insights = analysis['psychological_insights']
                # insights это уже dict (JSONB), не строка
                if isinstance(insights, dict):
                    if 'main' in insights:
                        all_insights.append(insights['main'])
                    elif insights:  # Если есть хоть что-то
                        all_insights.append(str(insights))
                elif isinstance(insights, str):
                    all_insights.append(insights)

        # Усредняем черты
        final_traits = {
            "big_five": {},
            "dynamic_traits": {},
            "adaptive_traits": {},
            "domain_specific": {}
        }

        for category in accumulated_traits.keys():
            for trait, values in accumulated_traits[category].items():
                if isinstance(values, dict):
                    final_traits[category][trait] = {}
                    for subtrait, subvalues in values.items():
                        if subvalues:
                            final_traits[category][trait][subtrait] = sum(subvalues) / len(subvalues)
                elif isinstance(values, list) and values:
                    final_traits[category][trait] = sum(values) / len(values)

        # Создаём personality narrative для векторизации
        narrative_parts = []

        # Добавляем Big Five описание
        bf = final_traits['big_five']
        narrative_parts.append(f"Личность с высокой открытостью ({bf.get('openness', 0.5):.2f}), "
                               f"добросовестностью ({bf.get('conscientiousness', 0.5):.2f}), "
                               f"экстраверсией ({bf.get('extraversion', 0.5):.2f}), "
                               f"доброжелательностью ({bf.get('agreeableness', 0.5):.2f}), "
                               f"и нейротизмом ({bf.get('neuroticism', 0.5):.2f}).")

        # Добавляем ключевые инсайты
        if all_insights:
            narrative_parts.append("Ключевые паттерны: " + "; ".join(all_insights[:3]))

        # Добавляем динамические черты
        dt = final_traits['dynamic_traits']
        if dt:
            top_dynamic = sorted(dt.items(), key=lambda x: x[1], reverse=True)[:3]
            traits_str = ", ".join([f"{k} ({v:.2f})" for k, v in top_dynamic])
            narrative_parts.append(f"Выраженные динамические черты: {traits_str}.")

        personality_narrative = " ".join(narrative_parts)

        # Вычисляем средние метрики
        avg_confidence = sum(a['confidence_score'] for a in analyses) / len(analyses)
        avg_quality = sum(a['quality_score'] for a in analyses) / len(analyses)

        # Создаём финальный analysis_result
        analysis_result = {
            "personality_summary": {
                "narrative": personality_narrative,
                "short_description": f"Профиль на основе {len(analyses)} ответов",
                "key_traits": list(bf.keys())
            },
            "personality_traits": final_traits,  # Нужно для EmbeddingCreator
            "trait_extraction": {
                "version": "2.0",
                "traits": final_traits,
                "assessment_metadata": {
                    "total_analyses": len(analyses),
                    "confidence_avg": avg_confidence,
                    "quality_avg": avg_quality
                }
            },
            "core_analysis": {
                "insights": {
                    "main": f"Аккумулированные инсайты из {len(analyses)} ответов",
                    "patterns": all_insights[:5]  # Первые 5
                }
            },
            "processing_metadata": {
                "model_used": analyses[-1]['ai_model_used'],
                "analyses_count": len(analyses)
            },
            "quality_metadata": {  # Нужно для EmbeddingCreator
                "overall_reliability": avg_quality,
                "confidence": avg_confidence
            }
        }

        logger.info(f"   📊 Accumulated {len(analyses)} analyses into personality profile")
        logger.info(f"   🧬 Big Five traits: {len(final_traits['big_five'])}")
        logger.info(f"   🔬 Dynamic traits: {len(final_traits['dynamic_traits'])}")

        # Создаём векторы
        try:
            vector_success = await embedding_creator.create_personality_vector(
                user_id=uid,
                analysis_result=analysis_result,
                is_update=False  # Первое создание
            )

            if vector_success:
                logger.info(f"   ✅ Vectors created successfully for user {uid}")
            else:
                logger.error(f"   ❌ Failed to create vectors for user {uid}")

        except Exception as e:
            logger.error(f"   ❌ Error creating vectors for user {uid}: {e}", exc_info=True)

    logger.info(f"\n{'='*60}")
    logger.info(f"🎉 Vector creation completed!")
    logger.info(f"   Processed {len(user_analyses)} users")

    await db_service.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Create Qdrant vectors from analyses')
    parser.add_argument('--user-id', type=int, help='Specific user ID')
    args = parser.parse_args()

    asyncio.run(create_vectors_for_analyzed_answers(args.user_id))
