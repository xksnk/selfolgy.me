#!/usr/bin/env python3
"""Check onboarding sessions"""

import asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

async def check_sessions():
    DATABASE_URL = "postgresql+asyncpg://n8n:sS67wM+1zMBRFHAW4kj9HwFl5J6+veo7Nirx0/I+oiU=@localhost:5432/n8n"

    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Check recent sessions
        result = await session.execute(text("""
            SELECT
                id,
                user_id,
                status,
                questions_asked,
                questions_answered,
                started_at
            FROM selfology.onboarding_sessions
            ORDER BY started_at DESC
            LIMIT 5
        """))

        print("📊 Recent onboarding sessions:\n")
        for row in result:
            print(f"  Session {row[0]}: user={row[1]}, status={row[2]}")
            print(f"    Asked={row[3]}, Answered={row[4]}")
            print(f"    Started: {row[5]}\n")

if __name__ == "__main__":
    asyncio.run(check_sessions())
