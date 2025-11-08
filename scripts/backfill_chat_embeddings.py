#!/usr/bin/env python3
"""
Backfill embeddings for existing chat messages

One-time migration script to create embeddings for historical messages.

Usage:
    python scripts/backfill_chat_embeddings.py [--days 30] [--batch-size 100]
"""

import sys
import os
import asyncio
import argparse
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncpg
from openai import AsyncOpenAI
from qdrant_client import QdrantClient
from qdrant_client.http import models


async def backfill_embeddings(days: int = 30, batch_size: int = 100, dry_run: bool = False):
    """
    Backfill embeddings for existing messages

    Args:
        days: Process messages from last N days
        batch_size: Number of messages to process at once
        dry_run: If True, don't actually create embeddings (test mode)
    """

    print(f"📋 Configuration:")
    print(f"   - Days to process: {days}")
    print(f"   - Batch size: {batch_size}")
    print(f"   - Dry run: {dry_run}")
    print()

    # Connect to PostgreSQL
    print("🔗 Connecting to PostgreSQL...")
    db_pool = await asyncpg.create_pool(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        database=os.getenv("POSTGRES_DB", "n8n"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD")
    )

    # Connect to OpenAI
    print("🔗 Connecting to OpenAI...")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("❌ OPENAI_API_KEY not found in environment")
        return

    openai_client = AsyncOpenAI(api_key=openai_api_key)

    # Connect to Qdrant
    print("🔗 Connecting to Qdrant...")
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant = QdrantClient(url=qdrant_url)

    # Check collection exists
    try:
        qdrant.get_collection("chat_messages")
        print("✅ Collection 'chat_messages' exists")
    except Exception as e:
        print(f"❌ Collection 'chat_messages' not found: {e}")
        print("   Run: python scripts/create_chat_messages_collection.py")
        return

    print()

    # Get existing messages
    print(f"📊 Fetching messages from last {days} days...")
    async with db_pool.acquire() as conn:
        messages = await conn.fetch("""
            SELECT id, user_id, message, role, created_at
            FROM chat_messages
            WHERE created_at > NOW() - INTERVAL $1
              AND role = 'user'  -- Only user messages to save cost
            ORDER BY id
        """, f"{days} days")

    total_messages = len(messages)
    print(f"📋 Found {total_messages} user messages to process")

    if total_messages == 0:
        print("✅ No messages to process")
        return

    if dry_run:
        print("\n🔍 DRY RUN MODE - no embeddings will be created")
        print(f"   Would process {total_messages} messages in {(total_messages-1)//batch_size + 1} batches")
        return

    # Confirm
    response = input(f"\n❓ Process {total_messages} messages? (yes/no): ")
    if response.lower() != "yes":
        print("❌ Cancelled")
        return

    print("\n🚀 Starting backfill...\n")

    # Process in batches
    total_batches = (total_messages - 1) // batch_size + 1
    total_cost = 0.0
    processed_count = 0

    for batch_num in range(0, total_messages, batch_size):
        batch = messages[batch_num:batch_num+batch_size]
        batch_index = batch_num // batch_size + 1

        print(f"📦 Batch {batch_index}/{total_batches} ({len(batch)} messages)...")

        try:
            # Create embeddings
            texts = [msg["message"] for msg in batch]
            embeddings_response = await openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=texts,
                dimensions=1536
            )

            # Calculate cost
            # text-embedding-3-small: $0.00002 per 1K tokens
            # Rough estimate: 1 token ≈ 4 characters
            total_chars = sum(len(text) for text in texts)
            estimated_tokens = total_chars // 4
            batch_cost = (estimated_tokens / 1000) * 0.00002
            total_cost += batch_cost

            # Upsert to Qdrant
            points = [
                models.PointStruct(
                    id=f"msg_{msg['id']}",
                    vector=emb.embedding,
                    payload={
                        "user_id": msg["user_id"],
                        "message_id": msg["id"],
                        "message": msg["message"],
                        "role": msg["role"],
                        "timestamp": msg["created_at"].isoformat(),
                        "message_length": len(msg["message"]),
                        "backfilled_at": datetime.now().isoformat()
                    }
                )
                for msg, emb in zip(batch, embeddings_response.data)
            ]

            qdrant.upsert(collection_name="chat_messages", points=points)

            processed_count += len(batch)
            print(f"   ✅ Processed {processed_count}/{total_messages} messages (cost: ${batch_cost:.6f})")

            # Small delay to avoid rate limits
            await asyncio.sleep(0.5)

        except Exception as e:
            print(f"   ❌ Error processing batch {batch_index}: {e}")
            import traceback
            traceback.print_exc()

    # Cleanup
    await db_pool.close()

    # Summary
    print("\n" + "="*80)
    print("📊 BACKFILL SUMMARY")
    print("="*80)
    print(f"✅ Total messages processed: {processed_count}/{total_messages}")
    print(f"💰 Total cost: ${total_cost:.4f}")
    print(f"📈 Average cost per message: ${total_cost/processed_count:.6f}")
    print()

    # Verify Qdrant
    info = qdrant.get_collection("chat_messages")
    print(f"📦 Qdrant collection 'chat_messages':")
    print(f"   - Points count: {info.points_count}")
    print(f"   - Status: {info.status}")
    print()

    print("🎉 Backfill completed!")


def main():
    parser = argparse.ArgumentParser(description="Backfill chat message embeddings")
    parser.add_argument("--days", type=int, default=30,
                       help="Process messages from last N days (default: 30)")
    parser.add_argument("--batch-size", type=int, default=100,
                       help="Batch size for processing (default: 100)")
    parser.add_argument("--dry-run", action="store_true",
                       help="Test mode - don't create embeddings")

    args = parser.parse_args()

    print("="*80)
    print("BACKFILL CHAT MESSAGE EMBEDDINGS - PHASE 1")
    print("="*80)
    print()

    try:
        asyncio.run(backfill_embeddings(
            days=args.days,
            batch_size=args.batch_size,
            dry_run=args.dry_run
        ))

    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user")
        sys.exit(1)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
