"""
Создание векторов для Digital Personality в Qdrant

Векторизует конкретную информацию (интересы, цели, барьеры и т.д.)
для семантического поиска и работы с AI коучем
"""

import asyncio
import logging
import sys
import json
from pathlib import Path
from datetime import datetime

# Добавляем пути
sys.path.append(str(Path(__file__).parent.parent))

from selfology_bot.database import DatabaseService, DigitalPersonalityDAO
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance

# OpenAI для создания embeddings
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def create_digital_personality_vectors(user_id: int):
    """
    Создаёт векторы для Digital Personality

    Создаёт 2 типа векторов:
    1. Structured vector (1536D) - все категории отдельно для точного поиска
    2. Narrative vector (3072D) - человекочитаемое описание для AI коуча
    """

    logger.info("="*80)
    logger.info(f"🔮 CREATING DIGITAL PERSONALITY VECTORS FOR USER {user_id}")
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

    personality_dao = DigitalPersonalityDAO(db_service)

    # OpenAI client
    import os
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("❌ OPENAI_API_KEY not found")
        return

    openai_client = AsyncOpenAI(api_key=api_key)

    # Qdrant client
    qdrant_client = QdrantClient(host="localhost", port=6333)

    # Получаем Digital Personality
    personality = await personality_dao.get_personality(user_id)

    if not personality:
        logger.error(f"❌ No digital personality found for user {user_id}")
        return

    logger.info(f"✅ Loaded digital personality")
    logger.info(f"   Completeness: {personality.get('completeness_score', 0):.2%}")

    # === Создаём коллекции если их нет ===

    collections_config = [
        {
            "name": "digital_personality_structured",
            "size": 1536,
            "description": "Structured personality data for precise matching"
        },
        {
            "name": "digital_personality_narrative",
            "size": 3072,
            "description": "Human-readable personality narrative for AI coach"
        }
    ]

    for config in collections_config:
        try:
            # Пытаемся получить коллекцию через REST API напрямую
            import requests
            response = requests.get(f"http://localhost:6333/collections/{config['name']}")
            if response.status_code == 200:
                logger.info(f"✅ Collection '{config['name']}' already exists")
                continue
        except Exception as e:
            logger.warning(f"Could not check collection existence: {e}")

        try:
            qdrant_client.create_collection(
                collection_name=config["name"],
                vectors_config=VectorParams(
                    size=config["size"],
                    distance=Distance.COSINE
                )
            )
            logger.info(f"✅ Created collection '{config['name']}' ({config['size']}D)")
        except Exception as create_error:
            if "already exists" in str(create_error).lower():
                logger.info(f"✅ Collection '{config['name']}' already exists")
            else:
                raise

    # === ВЕКТОР 1: STRUCTURED (1536D) ===
    logger.info("\n" + "="*80)
    logger.info("📊 CREATING STRUCTURED VECTOR (1536D)")
    logger.info("="*80)

    # Создаём структурированный текст со всеми категориями
    structured_parts = []

    # Парсим JSONB поля
    interests = json.loads(personality.get('interests', '[]')) if isinstance(personality.get('interests'), str) else personality.get('interests', [])
    goals = json.loads(personality.get('goals', '[]')) if isinstance(personality.get('goals'), str) else personality.get('goals', [])
    barriers = json.loads(personality.get('barriers', '[]')) if isinstance(personality.get('barriers'), str) else personality.get('barriers', [])
    skills = json.loads(personality.get('skills', '[]')) if isinstance(personality.get('skills'), str) else personality.get('skills', [])
    relationships = json.loads(personality.get('relationships', '[]')) if isinstance(personality.get('relationships'), str) else personality.get('relationships', [])
    values = json.loads(personality.get('values', '[]')) if isinstance(personality.get('values'), str) else personality.get('values', [])
    health = json.loads(personality.get('health', '[]')) if isinstance(personality.get('health'), str) else personality.get('health', [])
    current_state = json.loads(personality.get('current_state', '[]')) if isinstance(personality.get('current_state'), str) else personality.get('current_state', [])

    # Интересы
    if interests:
        active_interests = [i['activity'] for i in interests if i.get('status') == 'active']
        if active_interests:
            structured_parts.append(f"Interests: {', '.join(active_interests)}")

    # Навыки
    if skills:
        skill_names = [s['skill'] for s in skills]
        if skill_names:
            structured_parts.append(f"Skills: {', '.join(skill_names)}")

    # Цели
    if goals:
        high_priority_goals = [g['goal'] for g in goals if g.get('priority') == 'high']
        if high_priority_goals:
            structured_parts.append(f"High priority goals: {', '.join(high_priority_goals)}")

        medium_priority_goals = [g['goal'] for g in goals if g.get('priority') == 'medium']
        if medium_priority_goals:
            structured_parts.append(f"Medium priority goals: {', '.join(medium_priority_goals)}")

    # Барьеры
    if barriers:
        barrier_texts = [b['barrier'] for b in barriers]
        if barrier_texts:
            structured_parts.append(f"Barriers and fears: {', '.join(barrier_texts)}")

    # Отношения
    if relationships:
        important_people = [f"{r['person']} ({r['relationship']})" for r in relationships]
        if important_people:
            structured_parts.append(f"Important people: {', '.join(important_people)}")

    # Ценности
    if values:
        value_texts = [v['value'] for v in values]
        if value_texts:
            structured_parts.append(f"Core values: {', '.join(value_texts)}")

    # Здоровье
    if health:
        health_texts = [f"{h['aspect']}: {h['condition']}" for h in health]
        if health_texts:
            structured_parts.append(f"Health considerations: {'; '.join(health_texts)}")

    structured_text = " | ".join(structured_parts)

    logger.info(f"\n📝 Structured text to vectorize:")
    logger.info(f"   {structured_text[:200]}...")

    # Создаём embedding
    response = await openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=structured_text
    )

    structured_vector = response.data[0].embedding

    logger.info(f"✅ Created 1536D embedding")

    # Сохраняем в Qdrant
    qdrant_client.upsert(
        collection_name="digital_personality_structured",
        points=[
            PointStruct(
                id=user_id,
                vector=structured_vector,
                payload={
                    "user_id": user_id,
                    "interests": interests,
                    "goals": goals,
                    "barriers": barriers,
                    "skills": skills,
                    "relationships": relationships,
                    "values": values,
                    "health": health,
                    "completeness_score": personality.get('completeness_score', 0),
                    "last_updated": personality.get('last_updated').isoformat() if personality.get('last_updated') else None,
                    "structured_text": structured_text
                }
            )
        ]
    )

    logger.info(f"✅ Saved structured vector to Qdrant")

    # === ВЕКТОР 2: NARRATIVE (3072D) ===
    logger.info("\n" + "="*80)
    logger.info("📖 CREATING NARRATIVE VECTOR (3072D) FOR AI COACH")
    logger.info("="*80)

    # Создаём человекочитаемое описание личности для AI коуча
    narrative_parts = []

    # Вступление
    narrative_parts.append("This is a comprehensive personality profile of the user.")

    # Интересы и увлечения
    if interests:
        active = [i['activity'] for i in interests if i.get('status') == 'active']
        inactive = [i['activity'] for i in interests if i.get('status') == 'inactive']

        if active:
            narrative_parts.append(f"The user is actively interested in: {', '.join(active)}.")
        if inactive:
            narrative_parts.append(f"Previously interested but no longer active: {', '.join(inactive)}.")

    # Навыки
    if skills:
        skill_descriptions = []
        for skill in skills:
            level = skill.get('level', 'unknown')
            name = skill['skill']
            skill_descriptions.append(f"{name} (level: {level})")

        if skill_descriptions:
            narrative_parts.append(f"Skills and abilities: {', '.join(skill_descriptions)}.")

    # Цели и амбиции
    if goals:
        long_term = [g['goal'] for g in goals if g.get('type') == 'long_term']
        short_term = [g['goal'] for g in goals if g.get('type') == 'short_term']

        if long_term:
            narrative_parts.append(f"Long-term aspirations: {', '.join(long_term)}.")
        if short_term:
            narrative_parts.append(f"Short-term goals: {', '.join(short_term)}.")

    # Барьеры и страхи
    if barriers:
        barrier_descriptions = []
        for barrier in barriers:
            b_type = barrier.get('type', 'unknown')
            impact = barrier.get('impact', '')
            text = barrier['barrier']
            barrier_descriptions.append(f"{text} ({b_type}, impact: {impact})")

        if barrier_descriptions:
            narrative_parts.append(f"Current barriers and challenges: {'; '.join(barrier_descriptions)}.")

    # Важные отношения
    if relationships:
        rel_descriptions = [f"{r['person']} ({r['relationship']})" for r in relationships]
        if rel_descriptions:
            narrative_parts.append(f"Important relationships: {', '.join(rel_descriptions)}. These people matter to the user.")

    # Ценности
    if values:
        value_descriptions = []
        for value in values:
            v_text = value['value']
            context = value.get('context', '')
            value_descriptions.append(f"{v_text}" + (f" in {context}" if context else ""))

        if value_descriptions:
            narrative_parts.append(f"Core values and principles: {', '.join(value_descriptions)}.")

    # Здоровье
    if health:
        health_descriptions = []
        for h in health:
            aspect = h['aspect']
            condition = h['condition']
            impact = h.get('impact', '')
            health_descriptions.append(f"{aspect}: {condition} (impact: {impact})")

        if health_descriptions:
            narrative_parts.append(f"Health and wellbeing considerations: {'; '.join(health_descriptions)}.")

    # Текущее состояние
    if current_state:
        state_descriptions = [f"{s['activity']} ({s.get('status', 'unknown')})" for s in current_state]
        if state_descriptions:
            narrative_parts.append(f"Current activities: {', '.join(state_descriptions)}.")

    # Заключение
    narrative_parts.append(f"This profile is based on {personality.get('total_answers_analyzed', 0)} analyzed answers with {personality.get('completeness_score', 0):.0%} completeness.")

    narrative_text = " ".join(narrative_parts)

    logger.info(f"\n📝 Narrative text for AI coach:")
    logger.info(f"   {narrative_text[:300]}...")

    # Создаём embedding (3072D)
    response = await openai_client.embeddings.create(
        model="text-embedding-3-large",
        input=narrative_text
    )

    narrative_vector = response.data[0].embedding

    logger.info(f"✅ Created 3072D embedding")

    # Сохраняем в Qdrant
    qdrant_client.upsert(
        collection_name="digital_personality_narrative",
        points=[
            PointStruct(
                id=user_id,
                vector=narrative_vector,
                payload={
                    "user_id": user_id,
                    "narrative": narrative_text,
                    "structured_data": {
                        "interests": interests,
                        "goals": goals,
                        "barriers": barriers,
                        "skills": skills,
                        "relationships": relationships,
                        "values": values,
                        "health": health,
                        "current_state": current_state
                    },
                    "completeness_score": personality.get('completeness_score', 0),
                    "total_answers_analyzed": personality.get('total_answers_analyzed', 0),
                    "last_updated": personality.get('last_updated').isoformat() if personality.get('last_updated') else None
                }
            )
        ]
    )

    logger.info(f"✅ Saved narrative vector to Qdrant")

    # === ПРОВЕРКА ===
    logger.info("\n" + "="*80)
    logger.info("🔍 VERIFICATION")
    logger.info("="*80)

    # Проверяем что векторы сохранились
    for collection in ["digital_personality_structured", "digital_personality_narrative"]:
        collection_info = qdrant_client.get_collection(collection)
        points = qdrant_client.retrieve(
            collection_name=collection,
            ids=[user_id]
        )

        if points:
            logger.info(f"✅ {collection}: Vector exists")
            logger.info(f"   Dimension: {collection_info.config.params.vectors.size}D")
            logger.info(f"   Points in collection: {collection_info.points_count}")
        else:
            logger.error(f"❌ {collection}: Vector NOT found")

    logger.info("\n" + "="*80)
    logger.info("🎉 DIGITAL PERSONALITY VECTORS CREATED SUCCESSFULLY!")
    logger.info("="*80)
    logger.info("\n💡 Now you can:")
    logger.info("   1. Search for similar users by interests/goals/values")
    logger.info("   2. Use AI coach with full context of your personality")
    logger.info("   3. Query specific aspects (barriers, skills, etc.)")
    logger.info("="*80)

    await db_service.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Create digital personality vectors')
    parser.add_argument('--user-id', type=int, required=True, help='User ID')
    args = parser.parse_args()

    asyncio.run(create_digital_personality_vectors(args.user_id))
