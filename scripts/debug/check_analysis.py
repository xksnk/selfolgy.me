#!/usr/bin/env python3
"""Check answer_analysis table state"""

import asyncio
import os
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

async def check_analysis():
    DATABASE_URL = "postgresql+asyncpg://n8n:sS67wM+1zMBRFHAW4kj9HwFl5J6+veo7Nirx0/I+oiU=@localhost:5432/n8n"

    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Count answers
        result = await session.execute(text("SELECT COUNT(*) as cnt FROM selfology.user_answers_new"))
        answer_count = result.scalar()

        # Count analysis
        result = await session.execute(text("SELECT COUNT(*) as cnt FROM selfology.answer_analysis"))
        analysis_count = result.scalar()

        print(f"📊 user_answers_new: {answer_count}")
        print(f"🔬 answer_analysis: {analysis_count}")

        # Show recent answers
        result = await session.execute(text("""
            SELECT id, session_id, question_json_id, answer_length, analysis_status
            FROM selfology.user_answers_new
            ORDER BY id DESC LIMIT 3
        """))

        print("\n📝 Recent answers:")
        for row in result:
            print(f"  ID {row[0]}: session={row[1]}, q={row[2]}, len={row[3]}, status={row[4]}")

if __name__ == "__main__":
    asyncio.run(check_analysis())
