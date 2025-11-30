"""
Message Embedding Service - OpenAI embeddings для semantic search

Быстрый (~200ms) embedding сообщений пользователя для поиска похожих состояний
"""
import os
import asyncio
import logging
from typing import List, Optional
from openai import AsyncOpenAI
from datetime import datetime

logger = logging.getLogger(__name__)


class MessageEmbeddingService:
    """
    Сервис для создания embeddings сообщений через OpenAI

    Использует:
    - Model: text-embedding-3-small
    - Dimensions: 1536D (совпадает с personality_evolution векторами)
    - Скорость: ~200ms per message
    """

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            self.client = None
            print("⚠️ OPENAI_API_KEY not found - embeddings disabled")
        else:
            self.client = AsyncOpenAI(
                api_key=api_key,
                timeout=30.0,
                max_retries=2
            )

        # Конфигурация
        self.model = "text-embedding-3-small"
        self.dimensions = 1536  # Совпадает с personality_evolution
        self.max_text_length = 8000  # OpenAI limit

        # Статистика
        self.stats = {
            "embeddings_created": 0,
            "total_time_ms": 0,
            "errors": 0
        }

        logger.info(f"✅ MessageEmbeddingService initialized (model: {self.model}, dims: {self.dimensions})")

    async def embed_message(self, message: str) -> Optional[List[float]]:
        """
        Создать embedding для одного сообщения

        Args:
            message: Текст сообщения пользователя

        Returns:
            List[float] вектор 1536D или None при ошибке

        Скорость: ~200ms
        """
        if not self.client:
            return None  # Embeddings disabled

        start_time = datetime.now()

        try:
            # Валидация
            if not message or not message.strip():
                logger.warning("⚠️ Пустое сообщение для embedding")
                return None

            # Обрезаем если слишком длинное
            text = message.strip()
            if len(text) > self.max_text_length:
                text = text[:self.max_text_length]
                logger.warning(f"⚠️ Сообщение обрезано до {self.max_text_length} символов")

            # Вызов OpenAI API
            response = await self.client.embeddings.create(
                model=self.model,
                input=text,
                dimensions=self.dimensions
            )

            # Извлекаем вектор
            embedding = response.data[0].embedding

            # Статистика
            elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
            self.stats["embeddings_created"] += 1
            self.stats["total_time_ms"] += elapsed_ms

            logger.info(f"✅ Embedding created in {elapsed_ms:.0f}ms (length: {len(message)} chars)")

            return embedding

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"❌ Error creating embedding: {e}")
            return None

    async def embed_messages_batch(self, messages: List[str]) -> List[Optional[List[float]]]:
        """
        Создать embeddings для нескольких сообщений параллельно

        Args:
            messages: List сообщений

        Returns:
            List embeddings (может содержать None для failed)
        """
        start_time = datetime.now()

        # Создаем tasks для параллельного выполнения
        tasks = [self.embed_message(msg) for msg in messages]
        embeddings = await asyncio.gather(*tasks, return_exceptions=True)

        # Обрабатываем исключения
        results = []
        for i, emb in enumerate(embeddings):
            if isinstance(emb, Exception):
                logger.error(f"❌ Failed to embed message #{i}: {emb}")
                results.append(None)
            else:
                results.append(emb)

        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
        success_count = sum(1 for r in results if r is not None)

        logger.info(f"✅ Batch embedding: {success_count}/{len(messages)} in {elapsed_ms:.0f}ms")

        return results

    def get_stats(self) -> dict:
        """Получить статистику работы сервиса"""
        avg_time = (
            self.stats["total_time_ms"] / self.stats["embeddings_created"]
            if self.stats["embeddings_created"] > 0
            else 0
        )

        return {
            **self.stats,
            "avg_time_ms": round(avg_time, 2),
            "success_rate": (
                (self.stats["embeddings_created"] /
                 (self.stats["embeddings_created"] + self.stats["errors"]) * 100)
                if (self.stats["embeddings_created"] + self.stats["errors"]) > 0
                else 0
            )
        }
