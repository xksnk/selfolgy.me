#!/usr/bin/env python3
"""Debug script to view user onboarding data and chat history"""
import asyncio
import asyncpg
from dotenv import load_dotenv
import os

load_dotenv()

async def main():
    user_id = 98005572

    # Connect with explicit parameters (localhost instead of n8n-postgres)
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        user='n8n',
        password='sS67wM+1zMBRFHAW4kj9HwFl5J6+veo7Nirx0/I+oiU=',
        database='n8n'
    )

    try:
        # Set schema
        await conn.execute("SET search_path TO selfology")

        print(f"\n{'='*80}")
        print(f"USER {user_id} ONBOARDING ANSWERS (psychological_insights)")
        print(f"{'='*80}\n")

        # Get onboarding answers - first check table structure
        answers = await conn.fetch("""
            SELECT *
            FROM user_answers_new
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT 3
        """, user_id)

        # Print table structure first
        if answers:
            print("AVAILABLE COLUMNS:", list(answers[0].keys()))
            print()

        for i, row in enumerate(answers, 1):
            print(f"{i}. Row data:")
            for key, value in row.items():
                if value:
                    val_str = str(value)[:200] if len(str(value)) > 200 else str(value)
                    print(f"   {key}: {val_str}")
            print()

        print(f"\n{'='*80}")
        print(f"USER {user_id} CHAT MESSAGES (last 10)")
        print(f"{'='*80}\n")

        messages = await conn.fetch("""
            SELECT created_at, role, LEFT(content, 200) as content
            FROM chat_messages
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT 10
        """, user_id)

        for msg in messages:
            print(f"[{msg['created_at']}] {msg['role']}: {msg['content']}")
            print()

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
