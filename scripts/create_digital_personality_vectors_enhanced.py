"""
Создание векторов для Digital Personality в Qdrant (ENHANCED VERSION)

НОВОЕ: Добавляет психологические черты (Big Five, dynamic, adaptive, domain-specific)
в payload векторов для работы AI коуча

Векторизует:
- Конкретную информацию (интересы, цели, барьеры)
- Big Five personality traits
- Dynamic traits (resilience, authenticity, growth_mindset)
- Adaptive traits (stress_level, creative_flow, current_energy, social_battery)
- Domain-specific traits (по психологическим доменам)
- Psychological analysis
- Quality & processing metadata
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


async def get_latest_analysis(db_service: DatabaseService, user_id: int):
    """
    Получить последний (самый полный) анализ пользователя

    Returns:
        Dict с полным AI анализом включая personality_traits, psychological_analysis и т.д.
    """
    conn = await db_service.pool.acquire()

    try:
        # Получаем последний анализ с personality_summary (самый полный)
        result = await conn.fetchrow("""
            SELECT aa.raw_ai_response
            FROM selfology.answer_analysis aa
            JOIN selfology.user_answers_new ua ON aa.user_answer_id = ua.id
            JOIN selfology.onboarding_sessions os ON ua.session_id = os.id
            WHERE os.user_id = $1
              AND aa.raw_ai_response ? 'personality_summary'
            ORDER BY aa.id DESC
            LIMIT 1
        """, user_id)

        if not result:
            logger.warning(f"⚠️ No AI analysis with personality_summary found for user {user_id}")
            return None

        # raw_ai_response это JSONB, может прийти как строка или dict
        analysis = result['raw_ai_response']

        # Если пришла строка - парсим JSON
        if isinstance(analysis, str):
            try:
                analysis = json.loads(analysis)
                logger.info(f"✅ Parsed raw_ai_response from JSON string")
            except json.JSONDecodeError as e:
                logger.error(f"❌ Failed to parse raw_ai_response: {e}")
                return None

        # Проверяем что это dict
        if not isinstance(analysis, dict):
            logger.error(f"❌ raw_ai_response is not a dict after parsing: {type(analysis)}")
            return None

        logger.info(f"✅ Found latest AI analysis with {len(analysis.keys())} top-level keys")
        logger.info(f"   Keys: {', '.join(analysis.keys())}")

        return analysis

    finally:
        await db_service.pool.release(conn)


def safe_extract(obj, *keys, default=None):
    """
    Безопасная извлечение вложенных ключей из словаря

    Example:
        safe_extract(data, 'personality_traits', 'big_five', 'openness', default=0.5)
    """
    current = obj
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


async def create_digital_personality_vectors(user_id: int):
    """
    Создаёт векторы для Digital Personality с ПОЛНОЙ психологической информацией

    Создаёт 2 типа векторов:
    1. Structured vector (1536D) - все категории + психологические черты для точного поиска
    2. Narrative vector (3072D) - человекочитаемое описание + полная психология для AI коуча
    """

    logger.info("="*80)
    logger.info(f"🔮 CREATING ENHANCED DIGITAL PERSONALITY VECTORS FOR USER {user_id}")
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

    # 1. Получаем Digital Personality (interests, goals, barriers)
    personality = await personality_dao.get_personality(user_id)

    if not personality:
        logger.error(f"❌ No digital personality found for user {user_id}")
        return

    logger.info(f"✅ Loaded digital personality")
    logger.info(f"   Completeness: {personality.get('completeness_score', 0):.2%}")

    # 2. Получаем последний AI анализ с психологическими чертами
    analysis = await get_latest_analysis(db_service, user_id)

    if not analysis:
        logger.warning("⚠️ No AI analysis found - will create vectors WITHOUT psychological traits")
        psychological_traits = None
    else:
        psychological_traits = analysis.get('personality_traits', {})
        logger.info(f"✅ Loaded psychological traits")
        logger.info(f"   Big Five: {psychological_traits.get('big_five', {}).keys() if 'big_five' in psychological_traits else 'NOT FOUND'}")
        logger.info(f"   Dynamic traits: {len(psychological_traits.get('dynamic_traits', {}))} traits")
        logger.info(f"   Adaptive traits: {len(psychological_traits.get('adaptive_traits', {}))} traits")
        logger.info(f"   Domain-specific: {len(psychological_traits.get('domain_specific', {}))} domains")

    # === Создаём коллекции если их нет ===

    collections_config = [
        {
            "name": "digital_personality_structured",
            "size": 1536,
            "description": "Structured personality data with full psychological traits for precise matching"
        },
        {
            "name": "digital_personality_narrative",
            "size": 3072,
            "description": "Human-readable personality narrative with psychology for AI coach"
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
    logger.info("📊 CREATING ENHANCED STRUCTURED VECTOR (1536D)")
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

    # НОВОЕ: Добавляем психологические черты в текст для векторизации
    if psychological_traits:
        # Big Five
        big_five = psychological_traits.get('big_five', {})
        if big_five:
            traits_text = ", ".join([f"{trait}: {score:.2f}" for trait, score in big_five.items()])
            structured_parts.append(f"Big Five traits: {traits_text}")

        # Dynamic traits
        dynamic = psychological_traits.get('dynamic_traits', {})
        if dynamic:
            dynamic_text = ", ".join([f"{trait}: {score:.2f}" for trait, score in dynamic.items()])
            structured_parts.append(f"Dynamic traits: {dynamic_text}")

        # Adaptive traits
        adaptive = psychological_traits.get('adaptive_traits', {})
        if adaptive:
            adaptive_text = ", ".join([f"{trait}: {score:.2f}" for trait, score in adaptive.items()])
            structured_parts.append(f"Adaptive traits: {adaptive_text}")

    structured_text = " | ".join(structured_parts)

    logger.info(f"\n📝 Enhanced structured text to vectorize:")
    logger.info(f"   {structured_text[:300]}...")

    # Создаём embedding
    response = await openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=structured_text
    )

    structured_vector = response.data[0].embedding

    logger.info(f"✅ Created 1536D embedding")

    # НОВОЕ: Расширенный payload с психологическими чертами
    payload = {
        "user_id": user_id,

        # Конкретная информация (как раньше)
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

    # НОВОЕ: Добавляем психологические черты
    if psychological_traits:
        payload["personality_traits"] = {
            "big_five": psychological_traits.get('big_five', {}),
            "dynamic_traits": psychological_traits.get('dynamic_traits', {}),
            "adaptive_traits": psychological_traits.get('adaptive_traits', {}),
            "domain_specific": psychological_traits.get('domain_specific', {})
        }

        logger.info(f"✅ Added psychological traits to payload:")
        logger.info(f"   - Big Five: {len(payload['personality_traits']['big_five'])} traits")
        logger.info(f"   - Dynamic: {len(payload['personality_traits']['dynamic_traits'])} traits")
        logger.info(f"   - Adaptive: {len(payload['personality_traits']['adaptive_traits'])} traits")
        logger.info(f"   - Domain-specific: {len(payload['personality_traits']['domain_specific'])} domains")

    # НОВОЕ: Добавляем psychological_analysis если есть
    if analysis and 'psychological_analysis' in analysis:
        payload["psychological_analysis"] = analysis['psychological_analysis']
        logger.info(f"✅ Added psychological_analysis to payload")

    # НОВОЕ: Добавляем quality_metadata если есть
    if analysis and 'quality_metadata' in analysis:
        payload["quality_metadata"] = analysis['quality_metadata']
        logger.info(f"✅ Added quality_metadata to payload")

    # НОВОЕ: Добавляем processing_metadata если есть
    if analysis and 'processing_metadata' in analysis:
        payload["processing_metadata"] = analysis['processing_metadata']
        logger.info(f"✅ Added processing_metadata to payload")

    # Сохраняем в Qdrant
    qdrant_client.upsert(
        collection_name="digital_personality_structured",
        points=[
            PointStruct(
                id=user_id,
                vector=structured_vector,
                payload=payload
            )
        ]
    )

    logger.info(f"✅ Saved enhanced structured vector to Qdrant")

    # === ВЕКТОР 2: NARRATIVE (3072D) ===
    logger.info("\n" + "="*80)
    logger.info("📖 CREATING ENHANCED NARRATIVE VECTOR (3072D) FOR AI COACH")
    logger.info("="*80)

    # Создаём человекочитаемое описание личности для AI коуча
    narrative_parts = []

    # Вступление
    narrative_parts.append("This is a comprehensive personality profile of the user with detailed psychological analysis.")

    # НОВОЕ: Психологические черты в narrative
    if psychological_traits:
        # Big Five
        big_five = psychological_traits.get('big_five', {})
        if big_five:
            bf_text = ", ".join([
                f"{trait}: {score:.2f} ({'high' if score > 0.7 else 'medium' if score > 0.4 else 'low'})"
                for trait, score in big_five.items()
            ])
            narrative_parts.append(f"Big Five personality traits: {bf_text}.")

        # Dynamic traits
        dynamic = psychological_traits.get('dynamic_traits', {})
        if dynamic:
            dynamic_text = ", ".join([f"{trait}: {score:.2f}" for trait, score in dynamic.items()])
            narrative_parts.append(f"Dynamic psychological traits including: {dynamic_text}.")

        # Adaptive traits
        adaptive = psychological_traits.get('adaptive_traits', {})
        if adaptive:
            adaptive_text = ", ".join([f"{trait}: {score:.2f}" for trait, score in adaptive.items()])
            narrative_parts.append(f"Current adaptive state: {adaptive_text}.")

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

    # НОВОЕ: Psychological analysis insights
    if analysis and 'psychological_analysis' in analysis:
        psych = analysis['psychological_analysis']
        insights = psych.get('insights', [])
        if insights:
            narrative_parts.append(f"Key psychological insights: {'; '.join(insights)}.")

    # Заключение
    narrative_parts.append(f"This profile is based on {personality.get('total_answers_analyzed', 0)} analyzed answers with {personality.get('completeness_score', 0):.0%} completeness.")

    narrative_text = " ".join(narrative_parts)

    logger.info(f"\n📝 Enhanced narrative text for AI coach:")
    logger.info(f"   {narrative_text[:400]}...")

    # Создаём embedding (3072D)
    response = await openai_client.embeddings.create(
        model="text-embedding-3-large",
        input=narrative_text
    )

    narrative_vector = response.data[0].embedding

    logger.info(f"✅ Created 3072D embedding")

    # НОВОЕ: Расширенный payload для narrative
    narrative_payload = {
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

    # НОВОЕ: Добавляем все психологические данные
    if psychological_traits:
        narrative_payload["personality_traits"] = {
            "big_five": psychological_traits.get('big_five', {}),
            "dynamic_traits": psychological_traits.get('dynamic_traits', {}),
            "adaptive_traits": psychological_traits.get('adaptive_traits', {}),
            "domain_specific": psychological_traits.get('domain_specific', {})
        }

    if analysis and 'psychological_analysis' in analysis:
        narrative_payload["psychological_analysis"] = analysis['psychological_analysis']

    if analysis and 'quality_metadata' in analysis:
        narrative_payload["quality_metadata"] = analysis['quality_metadata']

    if analysis and 'processing_metadata' in analysis:
        narrative_payload["processing_metadata"] = analysis['processing_metadata']

    # Сохраняем в Qdrant
    qdrant_client.upsert(
        collection_name="digital_personality_narrative",
        points=[
            PointStruct(
                id=user_id,
                vector=narrative_vector,
                payload=narrative_payload
            )
        ]
    )

    logger.info(f"✅ Saved enhanced narrative vector to Qdrant")

    # === ПРОВЕРКА ===
    logger.info("\n" + "="*80)
    logger.info("🔍 VERIFICATION")
    logger.info("="*80)

    # Проверяем что векторы сохранились через curl (get_collection имеет баг с pydantic)
    try:
        import requests
        for collection in ["digital_personality_structured", "digital_personality_narrative"]:
            response = requests.post(
                f"http://localhost:6333/collections/{collection}/points/scroll",
                json={"limit": 1, "with_payload": True, "with_vector": False, "filter": {"must": [{"key": "user_id", "match": {"value": user_id}}]}}
            )
            if response.status_code == 200:
                data = response.json()
                if data['result']['points']:
                    point = data['result']['points'][0]
                    logger.info(f"✅ {collection}: Vector exists")
                    logger.info(f"   Payload keys: {list(point['payload'].keys())}")
                else:
                    logger.error(f"❌ {collection}: Vector NOT found")
            else:
                logger.error(f"❌ {collection}: Failed to verify (HTTP {response.status_code})")
    except Exception as e:
        logger.warning(f"⚠️ Verification failed (non-critical): {e}")
        logger.info(f"   Vectors were saved successfully, verification just didn't work")

    logger.info("\n" + "="*80)
    logger.info("🎉 ENHANCED DIGITAL PERSONALITY VECTORS CREATED SUCCESSFULLY!")
    logger.info("="*80)
    logger.info("\n💡 Now AI coach has access to:")
    logger.info("   ✅ Interests, goals, barriers, values (as before)")
    logger.info("   ✅ Big Five personality traits")
    logger.info("   ✅ Dynamic traits (resilience, authenticity, growth_mindset...)")
    logger.info("   ✅ Adaptive traits (stress_level, creative_flow, social_battery...)")
    logger.info("   ✅ Domain-specific traits (per psychological domain)")
    logger.info("   ✅ Psychological analysis insights")
    logger.info("   ✅ Quality & processing metadata")
    logger.info("="*80)

    await db_service.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Create ENHANCED digital personality vectors with full psychology')
    parser.add_argument('--user-id', type=int, required=True, help='User ID')
    args = parser.parse_args()

    asyncio.run(create_digital_personality_vectors(args.user_id))
