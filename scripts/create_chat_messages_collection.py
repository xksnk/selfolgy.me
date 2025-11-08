#!/usr/bin/env python3
"""
Create chat_messages collection in Qdrant

Решение Embedding Space Mismatch для semantic search.

Usage:
    python scripts/create_chat_messages_collection.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qdrant_client import QdrantClient
from qdrant_client.http import models


def create_chat_messages_collection():
    """Create chat_messages collection for Message → Message semantic search"""

    # Connect to Qdrant
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    print(f"🔗 Connecting to Qdrant at {qdrant_url}...")

    qdrant = QdrantClient(url=qdrant_url)

    # Check if collection exists
    try:
        existing = qdrant.get_collection("chat_messages")
        print(f"⚠️  Collection 'chat_messages' already exists")
        print(f"   Points count: {existing.points_count}")
        print(f"   Status: {existing.status}")

        response = input("\n❓ Delete and recreate? (yes/no): ")
        if response.lower() == "yes":
            qdrant.delete_collection("chat_messages")
            print("🗑️  Deleted existing collection")
        else:
            print("✅ Keeping existing collection")
            return

    except Exception:
        pass  # Collection doesn't exist - that's ok

    # Create collection
    print("\n📦 Creating chat_messages collection...")

    qdrant.create_collection(
        collection_name="chat_messages",
        vectors_config=models.VectorParams(
            size=1536,  # text-embedding-3-small dimension
            distance=models.Distance.COSINE
        ),
        optimizers_config=models.OptimizersConfigDiff(
            indexing_threshold=10000,  # Start indexing after 10K points
            memmap_threshold=50000     # Use memory-mapped storage after 50K points
        ),
        hnsw_config=models.HnswConfigDiff(
            m=16,                    # Number of edges per node
            ef_construct=100,        # Quality of index construction
            full_scan_threshold=10000  # When to use full scan vs HNSW
        )
    )

    print("✅ Collection 'chat_messages' created successfully!")

    # Verify collection
    info = qdrant.get_collection("chat_messages")
    print(f"\n📊 Collection info:")
    print(f"   - Name: {info.config.params}")
    print(f"   - Vector size: 1536D")
    print(f"   - Distance: COSINE")
    print(f"   - Status: {info.status}")

    print("\n🎉 Setup complete! You can now:")
    print("   1. Start saving messages with embeddings")
    print("   2. Run backfill script for existing messages")
    print("   3. Enable semantic search in ChatCoachService")


if __name__ == "__main__":
    print("="*80)
    print("CREATE CHAT_MESSAGES COLLECTION - PHASE 1")
    print("="*80)
    print()

    try:
        create_chat_messages_collection()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print()
    print("="*80)
