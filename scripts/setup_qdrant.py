#!/usr/bin/env python3
"""
Инициализация коллекций Qdrant

Создает необходимые коллекции для хранения векторов личности:
- quick_match (512D) - быстрый поиск
- personality_profiles (1536D) - основные профили
- personality_evolution (1536D) - эволюция личности
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from selfology_bot.analysis.embedding_creator import EmbeddingCreator


async def main():
    """Создать коллекции Qdrant"""

    print("\n" + "="*70)
    print("ИНИЦИАЛИЗАЦИЯ QDRANT КОЛЛЕКЦИЙ")
    print("="*70)
    print()

    # Инициализация embedding creator
    embedding_creator = EmbeddingCreator()

    # Создать коллекции
    success = await embedding_creator.setup_qdrant_collections()

    if success:
        print("\n✅ ВСЕ КОЛЛЕКЦИИ УСПЕШНО СОЗДАНЫ!")
        print("\nДоступные коллекции:")
        print("  - quick_match (512D) - быстрый поиск похожих личностей")
        print("  - personality_profiles (1536D) - основные профили пользователей")
        print("  - personality_evolution (1536D) - история эволюции личности")
    else:
        print("\n❌ Ошибка создания коллекций")
        print("Проверьте что Qdrant запущен: http://localhost:6333")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
