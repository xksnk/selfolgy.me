#!/usr/bin/env python3
"""
Psychological Components Health Check - Month 6
Проверяет состояние всех психологических компонентов системы
"""

import sys
import asyncio
import redis
from datetime import datetime

sys.path.insert(0, '/home/ksnk/microservices/critical/selfology-bot')

# Suppress verbose logging
import logging
logging.basicConfig(level=logging.WARNING)


def check_psychological_components():
    """Проверка всех психологических компонентов"""
    results = {}

    components = [
        ("CognitiveDistortionDetector", "selfology_bot.coach.components.cognitive_distortion_detector", "get_distortion_detector"),
        ("DefenseMechanismDetector", "selfology_bot.coach.components.defense_mechanism_detector", "get_defense_detector"),
        ("CoreBeliefsExtractor", "selfology_bot.coach.components.core_beliefs_extractor", "get_beliefs_extractor"),
        ("BlindSpotDetector", "selfology_bot.coach.components.blind_spot_detector", "get_blind_spot_detector"),
        ("TherapeuticAllianceTracker", "selfology_bot.coach.components.therapeutic_alliance_tracker", "get_alliance_tracker"),
        ("GatingMechanism", "selfology_bot.coach.components.gating_mechanism", "get_gating_mechanism"),
        ("AttachmentStyleClassifier", "selfology_bot.coach.components.attachment_style_classifier", "get_attachment_classifier"),
        ("BreakthroughDetector", "selfology_bot.coach.components.breakthrough_detector", "get_breakthrough_detector"),
        ("GrowthAreaTracker", "selfology_bot.coach.components.growth_area_tracker", "get_growth_tracker"),
        ("MetaPatternAnalyzer", "selfology_bot.coach.components.meta_pattern_analyzer", "get_meta_analyzer"),
    ]

    for name, module_path, func_name in components:
        try:
            module = __import__(module_path, fromlist=[func_name])
            getter = getattr(module, func_name)
            instance = getter()
            results[name] = {"status": "✅", "error": None}
        except Exception as e:
            results[name] = {"status": "❌", "error": str(e)}

    return results


def check_redis():
    """Проверка Redis"""
    try:
        r = redis.Redis(host='localhost', port=6379, db=0, socket_timeout=5)
        r.ping()
        return {"status": "✅", "error": None}
    except Exception as e:
        return {"status": "❌", "error": str(e)}


def check_qdrant():
    """Проверка Qdrant"""
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(host="localhost", port=6333)
        collections = client.get_collections()

        expected = ["episodic_memory", "semantic_knowledge", "emotional_thematic",
                   "psychological_constructs", "meta_patterns"]
        found = [c.name for c in collections.collections]
        missing = [c for c in expected if c not in found]

        if missing:
            return {"status": "⚠️", "error": f"Missing: {missing}", "found": len(found)}
        return {"status": "✅", "error": None, "collections": len(found)}
    except Exception as e:
        return {"status": "❌", "error": str(e)}


async def check_postgresql():
    """Проверка PostgreSQL"""
    try:
        import asyncpg
        conn = await asyncpg.connect(
            host='localhost',
            port=5434,
            user='selfology_user',
            password='selfology_secure_2024',
            database='selfology',
            timeout=5
        )
        tables = await conn.fetch("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'selfology' ORDER BY table_name
        """)
        await conn.close()
        return {"status": "✅", "error": None, "tables": len(tables)}
    except Exception as e:
        return {"status": "❌", "error": str(e)}


def main():
    """Main health check"""
    print("\n" + "=" * 60)
    print("🏥 SELFOLOGY PSYCHOLOGICAL SYSTEM HEALTH CHECK")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}\n")

    all_ok = True

    # Infrastructure
    print("📦 INFRASTRUCTURE:")

    redis_result = check_redis()
    print(f"   Redis: {redis_result['status']}")
    if redis_result['error']:
        all_ok = False

    qdrant_result = check_qdrant()
    status = qdrant_result['status']
    print(f"   Qdrant: {status}", end="")
    if qdrant_result.get('collections'):
        print(f" ({qdrant_result['collections']} collections)")
    else:
        print()
    if qdrant_result['status'] == '❌':
        all_ok = False

    pg_result = asyncio.run(check_postgresql())
    print(f"   PostgreSQL: {pg_result['status']}", end="")
    if pg_result.get('tables'):
        print(f" ({pg_result['tables']} tables)")
    else:
        print()
    if pg_result['error']:
        all_ok = False

    # Psychological Components
    print("\n🧠 PSYCHOLOGICAL COMPONENTS (10):")

    component_results = check_psychological_components()
    passed = sum(1 for r in component_results.values() if r['status'] == '✅')
    total = len(component_results)

    for name, result in component_results.items():
        if result['status'] != '✅':
            print(f"   {result['status']} {name}")
            all_ok = False

    if passed == total:
        print(f"   ✅ All {total} components OK")

    # Summary
    print("\n" + "=" * 60)
    if all_ok:
        print("✅ ALL SYSTEMS OPERATIONAL")
    else:
        print("⚠️ ISSUES DETECTED")

    print(f"Components: {passed}/{total}")
    print("=" * 60 + "\n")

    return 0 if all_ok else 1


if __name__ == "__main__":
    exit(main())
