"""
Bot Instance Lock - предотвращение множественных экземпляров бота

Использует Redis SET NX для создания distributed lock:
- Только один экземпляр бота может работать одновременно
- Автоматическое обновление TTL каждые 15 секунд
- Graceful release при shutdown

КРИТИЧНО для предотвращения конфликтов Telegram getUpdates!
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Optional

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class BotInstanceLock:
    """
    Управление блокировкой экземпляра бота через Redis

    Предотвращает запуск нескольких экземпляров бота, которые будут
    конфликтовать при получении обновлений от Telegram API.
    """

    def __init__(
        self,
        redis_host: str,
        redis_port: int,
        redis_db: int,
        lock_key: str,
        lock_ttl: int = 30
    ):
        """
        Args:
            redis_host: Redis server host
            redis_port: Redis server port
            redis_db: Redis database number
            lock_key: Key name for the lock in Redis
            lock_ttl: Lock TTL in seconds (default: 30)
        """
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_db = redis_db
        self.lock_key = lock_key
        self.lock_ttl = lock_ttl

        self.redis_client: Optional[redis.Redis] = None
        self.refresh_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

    async def acquire(self) -> bool:
        """
        Получить блокировку для предотвращения множественных экземпляров

        Returns:
            True если блокировка получена, False если другой экземпляр уже запущен
        """
        try:
            # Создаем Redis клиент если еще не создан
            if not self.redis_client:
                self.redis_client = await redis.Redis(
                    host=self.redis_host,
                    port=self.redis_port,
                    db=self.redis_db,
                    decode_responses=True
                )

            # Пытаемся установить блокировку с TTL
            # SET NX (only if Not eXists) с expiration
            lock_acquired = await self.redis_client.set(
                self.lock_key,
                f"pid:{os.getpid()}:started:{datetime.now().isoformat()}",
                nx=True,
                ex=self.lock_ttl
            )

            if lock_acquired:
                logger.info(f"✅ Bot instance lock acquired (PID: {os.getpid()})")
                return True
            else:
                # Проверяем кто держит блокировку
                existing_lock = await self.redis_client.get(self.lock_key)
                logger.error(
                    f"❌ Another bot instance is already running!\n"
                    f"   Lock holder: {existing_lock}\n"
                    f"   Please stop other instances before starting a new one."
                )
                return False

        except Exception as e:
            logger.error(f"❌ Failed to acquire instance lock: {e}")
            return False

    async def start_refresh(self):
        """
        Запустить периодическое обновление блокировки

        Создает background task который обновляет TTL каждые lock_ttl/2 секунд
        """
        self.refresh_task = asyncio.create_task(self._refresh_loop())
        logger.info(f"🔄 Instance lock refresh task started (interval: {self.lock_ttl // 2}s)")

    async def _refresh_loop(self):
        """
        Периодически обновлять блокировку экземпляра чтобы показать что бот активен
        """
        try:
            while not self._shutdown_event.is_set():
                # Обновляем TTL блокировки
                await self.redis_client.expire(self.lock_key, self.lock_ttl)
                logger.debug(f"🔄 Instance lock refreshed (TTL: {self.lock_ttl}s)")

                # Ждем перед следующим обновлением (обновляем каждые lock_ttl/2 секунд)
                await asyncio.sleep(self.lock_ttl // 2)

        except asyncio.CancelledError:
            logger.info("🛑 Instance lock refresh task cancelled")
        except Exception as e:
            logger.error(f"❌ Error refreshing instance lock: {e}")

    async def release(self):
        """
        Освободить блокировку экземпляра при shutdown
        """
        try:
            # Останавливаем refresh task
            if self.refresh_task and not self.refresh_task.done():
                self._shutdown_event.set()
                self.refresh_task.cancel()
                try:
                    await self.refresh_task
                except asyncio.CancelledError:
                    pass
                logger.info("✅ Instance lock refresh task stopped")

            # Удаляем блокировку из Redis
            if self.redis_client:
                await self.redis_client.delete(self.lock_key)
                logger.info("✅ Bot instance lock released")

                # Закрываем Redis client
                await self.redis_client.close()
                logger.info("✅ Redis client closed")

        except Exception as e:
            logger.error(f"❌ Error releasing instance lock: {e}")
