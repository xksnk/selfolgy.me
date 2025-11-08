#!/usr/bin/env python3
"""
Check Qdrant collections status

Quick diagnostic tool to see what's in Qdrant.

Usage:
    python scripts/check_qdrant_status.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qdrant_client import QdrantClient


def check_qdrant_status():
    """Check all Qdrant collections"""

    # Connect to Qdrant
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    print(f"🔗 Connecting to Qdrant at {qdrant_url}...\n")

    try:
        qdrant = QdrantClient(url=qdrant_url)
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return

    # Get all collections
    collections_response = qdrant.get_collections()
    collections = [c.name for c in collections_response.collections]

    if not collections:
        print("⚠️  No collections found")
        return

    print(f"📦 Found {len(collections)} collection(s):\n")
    print("="*80)

    # Expected collections for Selfology
    expected_collections = {
        "personality_profiles": "Current personality profiles (1536D)",
        "personality_evolution": "Personality evolution history (1536D)",
        "quick_match": "Quick personality matching (512D)",
        "chat_messages": "Chat message embeddings (1536D) - NEW!",
        "user_facets": "Multi-vector facets (6 × 512D) - Phase 2"
    }

    # Check each expected collection
    for collection_name, description in expected_collections.items():
        print(f"\n🔍 {collection_name}")
        print(f"   Description: {description}")

        if collection_name not in collections:
            print(f"   ❌ NOT FOUND")
            continue

        try:
            info = qdrant.get_collection(collection_name)

            print(f"   ✅ EXISTS")
            print(f"   - Points: {info.points_count:,}")
            print(f"   - Status: {info.status}")
            print(f"   - Vectors config: {info.config.params.vectors}")

            # Sample data
            if info.points_count > 0:
                sample = qdrant.scroll(
                    collection_name=collection_name,
                    limit=1,
                    with_payload=True,
                    with_vectors=False
                )

                if sample and len(sample[0]) > 0:
                    point = sample[0][0]
                    print(f"   - Sample point ID: {point.id}")
                    print(f"   - Payload keys: {list(point.payload.keys())}")

        except Exception as e:
            print(f"   ❌ Error: {e}")

    # Check for unexpected collections
    print("\n" + "="*80)
    unexpected = set(collections) - set(expected_collections.keys())
    if unexpected:
        print(f"\n⚠️  Unexpected collections found: {', '.join(unexpected)}")
    else:
        print("\n✅ All collections are expected")

    # Summary
    print("\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)

    status = []
    for name in expected_collections.keys():
        if name in collections:
            try:
                info = qdrant.get_collection(name)
                status.append(f"✅ {name}: {info.points_count:,} points")
            except:
                status.append(f"⚠️  {name}: ERROR")
        else:
            status.append(f"❌ {name}: NOT FOUND")

    for s in status:
        print(s)

    # Phase status
    print("\n" + "="*80)
    print("🚀 MIGRATION PHASE STATUS")
    print("="*80)

    has_chat_messages = "chat_messages" in collections
    has_user_facets = "user_facets" in collections

    if has_chat_messages:
        info = qdrant.get_collection("chat_messages")
        print(f"✅ Phase 1: COMPLETE (chat_messages has {info.points_count:,} points)")
    else:
        print("❌ Phase 1: NOT STARTED (run: python scripts/create_chat_messages_collection.py)")

    if has_user_facets:
        info = qdrant.get_collection("user_facets")
        print(f"✅ Phase 2: COMPLETE (user_facets has {info.points_count:,} points)")
    else:
        print("⚠️  Phase 2: NOT STARTED (multi-vector facets)")

    print()


if __name__ == "__main__":
    print("="*80)
    print("QDRANT STATUS CHECK")
    print("="*80)
    print()

    try:
        check_qdrant_status()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print()
    print("="*80)
