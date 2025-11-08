"""
Генерация полного отчёта о личности пользователя

Объединяет данные из:
1. Digital Personality (конкретные факты)
2. Answer Analysis (Big Five + психологические черты)
3. Qdrant векторы (семантический профиль)
4. Оригинальные ответы пользователя
"""

import asyncio
import logging
import sys
import json
from pathlib import Path
from datetime import datetime

# Добавляем пути
sys.path.append(str(Path(__file__).parent.parent))

from selfology_bot.database import DatabaseService, OnboardingDAO, DigitalPersonalityDAO
from selfology_bot.analysis import EmbeddingCreator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def generate_personality_report(user_id: int):
    """
    Генерирует полный отчёт о личности пользователя

    Args:
        user_id: ID пользователя
    """

    logger.info("="*80)
    logger.info(f"🎯 GENERATING FULL PERSONALITY REPORT FOR USER {user_id}")
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
    embedding_creator = EmbeddingCreator()

    # === СЕКЦИЯ 1: ЦИФРОВАЯ ЛИЧНОСТЬ ===
    logger.info("\n" + "="*80)
    logger.info("📋 SECTION 1: DIGITAL PERSONALITY (Concrete Facts)")
    logger.info("="*80)

    digital_personality = await personality_dao.get_personality(user_id)

    if digital_personality:
        logger.info(f"\n✅ Digital Personality Found")
        logger.info(f"   Total answers analyzed: {digital_personality.get('total_answers_analyzed', 0)}")
        logger.info(f"   Completeness score: {digital_personality.get('completeness_score', 0):.2%}")
        logger.info(f"   Last updated: {digital_personality.get('last_updated')}")

        # Интересы
        interests = json.loads(digital_personality.get('interests', '[]')) if isinstance(digital_personality.get('interests'), str) else digital_personality.get('interests', [])
        if interests:
            logger.info(f"\n   🎨 INTERESTS & HOBBIES:")
            for item in interests:
                status = item.get('status', 'unknown')
                activity = item.get('activity', 'N/A')
                context = item.get('context', '')
                status_emoji = "✅" if status == "active" else "❌"
                logger.info(f"      {status_emoji} {activity} {f'({context})' if context else ''}")

        # Навыки
        skills = json.loads(digital_personality.get('skills', '[]')) if isinstance(digital_personality.get('skills'), str) else digital_personality.get('skills', [])
        if skills:
            logger.info(f"\n   💪 SKILLS & ABILITIES:")
            for item in skills:
                skill = item.get('skill', 'N/A')
                level = item.get('level', 'unknown')
                logger.info(f"      • {skill} (level: {level})")

        # Цели
        goals = json.loads(digital_personality.get('goals', '[]')) if isinstance(digital_personality.get('goals'), str) else digital_personality.get('goals', [])
        if goals:
            logger.info(f"\n   🎯 GOALS & ASPIRATIONS:")
            for item in goals:
                goal = item.get('goal', 'N/A')
                goal_type = item.get('type', 'unknown')
                priority = item.get('priority', 'unknown')
                logger.info(f"      • {goal} ({goal_type}, priority: {priority})")

        # Барьеры
        barriers = json.loads(digital_personality.get('barriers', '[]')) if isinstance(digital_personality.get('barriers'), str) else digital_personality.get('barriers', [])
        if barriers:
            logger.info(f"\n   🚧 BARRIERS & FEARS:")
            for item in barriers:
                barrier = item.get('barrier', 'N/A')
                barrier_type = item.get('type', 'unknown')
                impact = item.get('impact', 'N/A')
                logger.info(f"      • {barrier} (type: {barrier_type})")
                logger.info(f"        Impact: {impact}")

        # Отношения
        relationships = json.loads(digital_personality.get('relationships', '[]')) if isinstance(digital_personality.get('relationships'), str) else digital_personality.get('relationships', [])
        if relationships:
            logger.info(f"\n   👥 IMPORTANT RELATIONSHIPS:")
            for item in relationships:
                person = item.get('person', 'N/A')
                relationship = item.get('relationship', 'unknown')
                logger.info(f"      • {person} ({relationship})")

        # Ценности
        values = json.loads(digital_personality.get('values', '[]')) if isinstance(digital_personality.get('values'), str) else digital_personality.get('values', [])
        if values:
            logger.info(f"\n   💎 VALUES & PRINCIPLES:")
            for item in values:
                value = item.get('value', 'N/A')
                context = item.get('context', '')
                logger.info(f"      • {value} {f'({context})' if context else ''}")

        # Здоровье
        health = json.loads(digital_personality.get('health', '[]')) if isinstance(digital_personality.get('health'), str) else digital_personality.get('health', [])
        if health:
            logger.info(f"\n   🏥 HEALTH & WELLBEING:")
            for item in health:
                aspect = item.get('aspect', 'N/A')
                condition = item.get('condition', 'N/A')
                impact = item.get('impact', 'N/A')
                logger.info(f"      • {aspect}: {condition}")
                logger.info(f"        Impact: {impact}")

        # Текущее состояние
        current_state = json.loads(digital_personality.get('current_state', '[]')) if isinstance(digital_personality.get('current_state'), str) else digital_personality.get('current_state', [])
        if current_state:
            logger.info(f"\n   📍 CURRENT STATE:")
            for item in current_state:
                activity = item.get('activity', 'N/A')
                status = item.get('status', 'unknown')
                logger.info(f"      • {activity} ({status})")
    else:
        logger.info("\n❌ No digital personality found")

    # === СЕКЦИЯ 2: ПСИХОЛОГИЧЕСКИЕ ЧЕРТЫ ===
    logger.info("\n" + "="*80)
    logger.info("🧠 SECTION 2: PSYCHOLOGICAL TRAITS (Big Five + Dynamics)")
    logger.info("="*80)

    async with db_service.get_connection() as conn:
        # Получаем все анализы
        analyses_query = """
            SELECT
                aa.id,
                aa.trait_scores,
                aa.psychological_insights,
                aa.quality_score,
                aa.confidence_score,
                ua.raw_answer,
                ua.question_json_id
            FROM selfology.answer_analysis aa
            JOIN selfology.user_answers_new ua ON aa.user_answer_id = ua.id
            JOIN selfology.onboarding_sessions os ON ua.session_id = os.id
            WHERE os.user_id = $1
            ORDER BY aa.id
        """
        analyses = await conn.fetch(analyses_query, user_id)

    if analyses:
        logger.info(f"\n✅ Found {len(analyses)} psychological analyses")
        logger.info(f"   Average quality: {sum(a['quality_score'] for a in analyses) / len(analyses):.2%}")
        logger.info(f"   Average confidence: {sum(a['confidence_score'] for a in analyses) / len(analyses):.2%}")

        # Усредняем Big Five
        big_five_accumulated = {
            'openness': [],
            'conscientiousness': [],
            'extraversion': [],
            'agreeableness': [],
            'neuroticism': []
        }

        dynamic_traits_accumulated = {}

        for analysis in analyses:
            trait_scores = analysis['trait_scores']

            # Парсим если это строка
            if isinstance(trait_scores, str):
                trait_scores = json.loads(trait_scores)

            # Big Five
            bf = trait_scores.get('big_five', {})
            for trait, value in bf.items():
                if trait in big_five_accumulated:
                    big_five_accumulated[trait].append(value)

            # Dynamic traits
            dt = trait_scores.get('dynamic_traits', {})
            for trait, value in dt.items():
                if trait not in dynamic_traits_accumulated:
                    dynamic_traits_accumulated[trait] = []
                dynamic_traits_accumulated[trait].append(value)

        # Усредняем
        big_five_avg = {k: (sum(v) / len(v) if v else 0) for k, v in big_five_accumulated.items()}
        dynamic_avg = {k: (sum(v) / len(v) if v else 0) for k, v in dynamic_traits_accumulated.items()}

        logger.info(f"\n   📊 BIG FIVE PERSONALITY TRAITS (averaged):")
        logger.info(f"      {'Trait':<25} Score   Interpretation")
        logger.info(f"      {'-'*60}")

        interpretations = {
            'openness': ('Low: Practical', 'Moderate', 'High: Creative'),
            'conscientiousness': ('Low: Spontaneous', 'Moderate', 'High: Organized'),
            'extraversion': ('Low: Introverted', 'Moderate', 'High: Extraverted'),
            'agreeableness': ('Low: Competitive', 'Moderate', 'High: Cooperative'),
            'neuroticism': ('Low: Calm', 'Moderate', 'High: Anxious')
        }

        for trait, score in big_five_avg.items():
            low, mid, high = interpretations[trait]
            if score < 0.33:
                interpretation = low
            elif score < 0.66:
                interpretation = mid
            else:
                interpretation = high

            bar = "█" * int(score * 20)
            logger.info(f"      {trait.capitalize():<25} {score:.2f}   {bar:<20} {interpretation}")

        logger.info(f"\n   ⚡ DYNAMIC PSYCHOLOGICAL TRAITS:")
        logger.info(f"      {'Trait':<30} Score")
        logger.info(f"      {'-'*60}")

        # Сортируем по убыванию
        sorted_dynamic = sorted(dynamic_avg.items(), key=lambda x: x[1], reverse=True)
        for trait, score in sorted_dynamic:
            bar = "█" * int(score * 20)
            logger.info(f"      {trait.replace('_', ' ').title():<30} {score:.2f}   {bar}")

        # Ключевые инсайты
        logger.info(f"\n   💡 KEY PSYCHOLOGICAL INSIGHTS:")
        insights_shown = 0
        for analysis in analyses:
            insights = analysis.get('psychological_insights', {})
            if isinstance(insights, dict):
                main_insight = insights.get('main', '')
                if main_insight and insights_shown < 5:  # Показываем топ-5
                    logger.info(f"      • {main_insight}")
                    insights_shown += 1
    else:
        logger.info("\n❌ No psychological analyses found")

    # === СЕКЦИЯ 3: ОРИГИНАЛЬНЫЕ ОТВЕТЫ ===
    logger.info("\n" + "="*80)
    logger.info("💬 SECTION 3: ORIGINAL USER ANSWERS")
    logger.info("="*80)

    async with db_service.get_connection() as conn:
        answers_query = """
            SELECT
                ua.raw_answer,
                ua.question_json_id
            FROM selfology.user_answers_new ua
            JOIN selfology.onboarding_sessions os ON ua.session_id = os.id
            WHERE os.user_id = $1
            ORDER BY ua.id
        """
        answers = await conn.fetch(answers_query, user_id)

    if answers:
        logger.info(f"\n✅ Found {len(answers)} user answers:")
        for idx, answer in enumerate(answers, 1):
            logger.info(f"\n   Answer #{idx} (Question ID: {answer['question_json_id']}):")
            logger.info(f"   \"{answer['raw_answer']}\"")
    else:
        logger.info("\n❌ No answers found")

    # === СЕКЦИЯ 4: ВЕКТОРНОЕ ПРЕДСТАВЛЕНИЕ ===
    logger.info("\n" + "="*80)
    logger.info("🔮 SECTION 4: VECTOR EMBEDDINGS (Semantic Profile)")
    logger.info("="*80)

    try:
        # Проверяем наличие векторов в Qdrant
        from qdrant_client import QdrantClient

        qdrant_client = QdrantClient(host="localhost", port=6333)

        # Проверяем коллекции
        collections = ["personality_profiles", "quick_match", "personality_evolution"]

        for collection in collections:
            try:
                collection_info = qdrant_client.get_collection(collection)
                points_count = collection_info.points_count

                if points_count > 0:
                    logger.info(f"\n   ✅ Collection: {collection}")
                    logger.info(f"      Vectors: {points_count}")
                    logger.info(f"      Dimension: {collection_info.config.params.vectors.size}")

                    # Пытаемся получить вектор пользователя
                    try:
                        point = qdrant_client.retrieve(
                            collection_name=collection,
                            ids=[user_id]
                        )

                        if point:
                            logger.info(f"      Status: Vector exists for user {user_id} ✅")

                            # Показываем payload
                            if point[0].payload:
                                logger.info(f"      Metadata:")
                                for key, value in point[0].payload.items():
                                    if key != 'full_profile' and key != 'narrative':
                                        logger.info(f"         {key}: {value}")
                        else:
                            logger.info(f"      Status: No vector for user {user_id}")
                    except Exception as e:
                        logger.info(f"      Status: Error retrieving vector - {e}")
                else:
                    logger.info(f"\n   ⚠️ Collection: {collection} - empty")

            except Exception as e:
                logger.info(f"\n   ❌ Collection: {collection} - {e}")

    except Exception as e:
        logger.error(f"\n❌ Error accessing Qdrant: {e}")

    # === ФИНАЛЬНОЕ РЕЗЮМЕ ===
    logger.info("\n" + "="*80)
    logger.info("📝 COMPREHENSIVE PERSONALITY SUMMARY")
    logger.info("="*80)

    summary = await personality_dao.get_personality_summary(user_id)
    if summary:
        logger.info(f"\n{summary}")

    logger.info("\n" + "="*80)
    logger.info(f"✅ REPORT GENERATION COMPLETED")
    logger.info(f"   Generated at: {datetime.now().isoformat()}")
    logger.info("="*80)

    await db_service.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Generate full personality report')
    parser.add_argument('--user-id', type=int, required=True, help='User ID')
    args = parser.parse_args()

    asyncio.run(generate_personality_report(args.user_id))
