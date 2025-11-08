#!/usr/bin/env python3
"""Простой тест OpenAI Embeddings API"""

import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from selfology_bot.analysis.embedding_creator import EmbeddingCreator


async def test_embeddings():
    """Простой тест создания embeddings"""

    print("🧪 Тест создания embeddings")

    creator = EmbeddingCreator()

    print(f"OpenAI client: {creator.openai_client is not None}")
    print(f"Qdrant client: {creator.qdrant_client is not None}")

    text = "Я люблю программирование и психологию"

    print(f"\n📝 Текст: {text}")
    print(f"\n🔬 Создаем embedding 1536D...")

    try:
        result = await creator._create_openai_embedding(text, "text-embedding-3-small", 1536)

        if result:
            print(f"✅ Embedding создан: {len(result)} dimensions")
            print(f"📊 Первые 5 значений: {result[:5]}")
            return True
        else:
            print(f"❌ Embedding = None")
            return False

    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_embeddings())
    sys.exit(0 if success else 1)
