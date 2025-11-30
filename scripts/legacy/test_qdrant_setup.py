#!/usr/bin/env python3
"""
Тестовый скрипт для проверки setup_qdrant_collections()
"""

import asyncio
import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(__file__))

from selfology_bot.analysis.embedding_creator import EmbeddingCreator

async def test_setup():
    """Тест создания коллекций Qdrant"""

    print("🧪 Testing Qdrant collections setup...")

    # Инициализация EmbeddingCreator (без параметров)
    creator = EmbeddingCreator()

    # Вызываем setup
    success = await creator.setup_qdrant_collections()

    if success:
        print("✅ Test PASSED - collections created successfully")
        return 0
    else:
        print("❌ Test FAILED - collections not created")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(test_setup())
    sys.exit(exit_code)
