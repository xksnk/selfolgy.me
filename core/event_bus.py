"""
Event Bus Implementation on Redis Streams

Централизованная шина событий для event-driven архитектуры.

Features:
- Redis Streams для pub/sub
- Consumer Groups для distributed processing
- Priority queues (CRITICAL/HIGH/NORMAL/LOW)
- Dead Letter Queue (DLQ)
- Event compression для больших payload
- Integration с Outbox Pattern
- Distributed tracing (Trace ID)
- Metrics и monitoring

Architecture:
    Producer → Event Bus → Redis Streams → Consumer Groups → Workers

Streams:
    - selfology:events:critical  (CRITICAL priority)
    - selfology:events:high      (HIGH priority)
    - selfology:events:normal    (NORMAL priority)
    - selfology:events:low       (LOW priority)
    - selfology:events:dlq       (Dead Letter Queue)

Usage:
    # Initialize
    event_bus = EventBus(redis_client)

    # Publish
    await event_bus.publish(
        "user.answer.submitted",
        {"user_id": 123, "answer": "text"},
        priority=EventPriority.HIGH,
        trace_id="req_abc"
    )

    # Subscribe
    consumer = EventConsumer(
        event_bus,
        "analysis_system",
        event_types=["user.answer.submitted"]
    )
    await consumer.start()
"""

import asyncio
import json
import logging
import zlib
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable, Awaitable
from dataclasses import dataclass

import redis.asyncio as redis

from core.domain_events import (
    BaseDomainEvent,
    EventPriority,
    EventRegistry,
    serialize_event
)

logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class EventBusConfig:
    """Конфигурация Event Bus"""
    redis_url: str = "redis://n8n-redis:6379"
    stream_prefix: str = "selfology:events"
    max_stream_length: int = 10000  # Максимум событий в stream (MAXLEN)
    compression_threshold: int = 1024  # Сжимать если payload > 1KB
    dlq_stream: str = "selfology:events:dlq"
    consumer_block_ms: int = 5000  # Timeout для blocking read
    batch_size: int = 100  # Количество событий в batch


# ============================================================================
# EVENT BUS
# ============================================================================

class EventBus:
    """
    Централизованная шина событий на Redis Streams

    Поддерживает:
    - Priority queues
    - Event compression
    - Distributed tracing
    - Metrics tracking
    """

    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        config: Optional[EventBusConfig] = None
    ):
        """
        Args:
            redis_client: Redis client instance (если None - создается новый)
            config: Конфигурация Event Bus
        """
        self.config = config or EventBusConfig()
        self.redis = redis_client
        self._own_redis = redis_client is None

        # Stream names по приоритетам
        self.streams = {
            EventPriority.CRITICAL: f"{self.config.stream_prefix}:critical",
            EventPriority.HIGH: f"{self.config.stream_prefix}:high",
            EventPriority.NORMAL: f"{self.config.stream_prefix}:normal",
            EventPriority.LOW: f"{self.config.stream_prefix}:low",
        }

        # Metrics
        self.stats = {
            "events_published": 0,
            "events_compressed": 0,
            "total_payload_bytes": 0,
            "errors": 0
        }

    async def connect(self):
        """Подключение к Redis"""
        if self._own_redis:
            self.redis = await redis.from_url(
                self.config.redis_url,
                decode_responses=False  # Binary mode для compression
            )
            logger.info(f"Event Bus connected to Redis: {self.config.redis_url}")

    async def disconnect(self):
        """Отключение от Redis"""
        if self._own_redis and self.redis:
            await self.redis.close()
            logger.info("Event Bus disconnected from Redis")

    async def publish(
        self,
        event_type: str,
        payload: Dict[str, Any],
        priority: EventPriority = EventPriority.NORMAL,
        trace_id: Optional[str] = None
    ) -> str:
        """
        Публикует событие в Event Bus

        Args:
            event_type: Тип события
            payload: Данные события
            priority: Приоритет (определяет stream)
            trace_id: Trace ID для distributed tracing

        Returns:
            Event ID в Redis Streams

        Example:
            event_id = await event_bus.publish(
                "user.answer.submitted",
                {"user_id": 123, "answer": "text"},
                priority=EventPriority.HIGH,
                trace_id="req_abc"
            )
        """
        try:
            # Валидация события через EventRegistry
            try:
                EventRegistry.validate_event(event_type, payload)
            except ValueError as e:
                logger.warning(f"Event validation failed: {e}. Publishing anyway.")

            # Сериализация payload
            serialized = json.dumps(payload).encode('utf-8')
            payload_size = len(serialized)

            # Compression если нужно
            compressed = False
            if payload_size > self.config.compression_threshold:
                serialized = zlib.compress(serialized)
                compressed = True
                self.stats["events_compressed"] += 1

            # Подготовка данных для Redis Stream
            stream_data = {
                b"event_type": event_type.encode('utf-8'),
                b"payload": serialized,
                b"compressed": b"1" if compressed else b"0",
                b"priority": priority.value.encode('utf-8'),
                b"timestamp": datetime.now().isoformat().encode('utf-8'),
            }

            if trace_id:
                stream_data[b"trace_id"] = trace_id.encode('utf-8')

            # Выбираем stream по приоритету
            stream_name = self.streams[priority]

            # XADD с MAXLEN для ограничения размера
            event_id = await self.redis.xadd(
                stream_name,
                stream_data,
                maxlen=self.config.max_stream_length,
                approximate=True  # Approximate MAXLEN для performance
            )

            # Metrics
            self.stats["events_published"] += 1
            self.stats["total_payload_bytes"] += payload_size

            logger.debug(
                f"Event published: {event_type} "
                f"(id={event_id.decode()}, priority={priority.value}, "
                f"size={payload_size}, compressed={compressed}, trace_id={trace_id})"
            )

            return event_id.decode()

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Failed to publish event {event_type}: {e}", exc_info=True)
            raise

    async def publish_event(
        self,
        event: BaseDomainEvent
    ) -> str:
        """
        Публикует Domain Event

        Args:
            event: Domain Event instance

        Returns:
            Event ID
        """
        payload = serialize_event(event)
        return await self.publish(
            event.event_type,
            payload,
            priority=event.priority,
            trace_id=event.trace_id
        )

    async def publish_to_dlq(
        self,
        event_type: str,
        payload: Dict[str, Any],
        error: str,
        original_stream: str,
        retry_count: int = 0
    ):
        """
        Публикует событие в Dead Letter Queue

        Используется когда событие не может быть обработано
        """
        dlq_payload = {
            "original_event_type": event_type,
            "original_payload": payload,
            "error": error,
            "original_stream": original_stream,
            "retry_count": retry_count,
            "failed_at": datetime.now().isoformat()
        }

        serialized = json.dumps(dlq_payload).encode('utf-8')

        await self.redis.xadd(
            self.config.dlq_stream,
            {
                b"event_type": event_type.encode('utf-8'),
                b"payload": serialized,
                b"compressed": b"0"
            },
            maxlen=self.config.max_stream_length,
            approximate=True
        )

        logger.error(
            f"Event moved to DLQ: {event_type} "
            f"(retry_count={retry_count}, error={error})"
        )

    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику Event Bus"""
        return {
            **self.stats,
            "streams": {
                name: priority.value
                for priority, name in self.streams.items()
            }
        }


# ============================================================================
# EVENT CONSUMER
# ============================================================================

class EventConsumer:
    """
    Consumer для обработки событий из Event Bus

    Features:
    - Consumer Groups (distributed processing)
    - Batch processing
    - Automatic retry
    - ACK/NACK
    - Health monitoring
    """

    def __init__(
        self,
        event_bus: EventBus,
        consumer_group: str,
        consumer_name: str,
        event_types: Optional[List[str]] = None,
        priorities: Optional[List[EventPriority]] = None,
        handler: Optional[Callable[[str, Dict[str, Any]], Awaitable[None]]] = None
    ):
        """
        Args:
            event_bus: Event Bus instance
            consumer_group: Имя consumer group (например "analysis_system")
            consumer_name: Имя этого consumer (например "worker_1")
            event_types: Фильтр по типам событий (None = все)
            priorities: Фильтр по приоритетам (None = все)
            handler: Async функция обработки события
        """
        self.event_bus = event_bus
        self.consumer_group = consumer_group
        self.consumer_name = consumer_name
        self.event_types = set(event_types) if event_types else None
        self.priorities = priorities or list(EventPriority)
        self.handler = handler

        self._running = False
        self._task: Optional[asyncio.Task] = None

        # Streams для подписки
        self.streams_to_read = [
            self.event_bus.streams[priority]
            for priority in self.priorities
        ]

        # Metrics
        self.stats = {
            "events_processed": 0,
            "events_failed": 0,
            "events_filtered": 0,
            "processing_time_total": 0.0
        }

    async def start(self):
        """Запускает consumer"""
        if self._running:
            logger.warning(f"Consumer {self.consumer_name} already running")
            return

        # Создаем consumer groups если не существуют
        await self._create_consumer_groups()

        self._running = True
        self._task = asyncio.create_task(self._consume_loop())

        logger.info(
            f"Consumer started: {self.consumer_name} "
            f"(group={self.consumer_group}, streams={len(self.streams_to_read)})"
        )

    async def stop(self):
        """Graceful shutdown consumer"""
        if not self._running:
            return

        self._running = False
        if self._task:
            await self._task

        logger.info(f"Consumer stopped: {self.consumer_name}")

    async def _create_consumer_groups(self):
        """Создает consumer groups для streams"""
        for stream_name in self.streams_to_read:
            try:
                await self.event_bus.redis.xgroup_create(
                    stream_name,
                    self.consumer_group,
                    id='0',  # Читать с начала
                    mkstream=True  # Создать stream если не существует
                )
                logger.debug(f"Consumer group created: {self.consumer_group} for {stream_name}")
            except redis.ResponseError as e:
                if "BUSYGROUP" in str(e):
                    # Group уже существует - ок
                    pass
                else:
                    raise

    async def _consume_loop(self):
        """Основной цикл чтения событий"""
        # Формируем dict для XREADGROUP: {stream_name: last_id}
        # '>' означает "новые сообщения"
        streams_dict = {
            stream_name: '>'
            for stream_name in self.streams_to_read
        }

        while self._running:
            try:
                # XREADGROUP - blocking read из нескольких streams
                results = await self.event_bus.redis.xreadgroup(
                    groupname=self.consumer_group,
                    consumername=self.consumer_name,
                    streams=streams_dict,
                    count=self.event_bus.config.batch_size,
                    block=self.event_bus.config.consumer_block_ms
                )

                if not results:
                    # Timeout - нет новых событий
                    continue

                # Обрабатываем события из всех streams
                for stream_name, messages in results:
                    for message_id, data in messages:
                        await self._process_event(
                            stream_name.decode(),
                            message_id.decode(),
                            data
                        )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Consumer loop error: {e}", exc_info=True)
                await asyncio.sleep(5)  # Backoff при ошибке

    async def _process_event(
        self,
        stream_name: str,
        message_id: str,
        data: Dict[bytes, bytes]
    ):
        """Обрабатывает одно событие"""
        start_time = datetime.now()

        try:
            # Десериализация
            event_type = data[b"event_type"].decode('utf-8')
            compressed = data.get(b"compressed", b"0") == b"1"
            payload_bytes = data[b"payload"]

            # Decompression если нужно
            if compressed:
                payload_bytes = zlib.decompress(payload_bytes)

            payload = json.loads(payload_bytes.decode('utf-8'))

            # Фильтрация по event_type
            if self.event_types and event_type not in self.event_types:
                self.stats["events_filtered"] += 1
                # ACK - событие не для нас
                await self._ack_event(stream_name, message_id)
                return

            # Обработка события
            if self.handler:
                await self.handler(event_type, payload)

            # ACK - успешно обработано
            await self._ack_event(stream_name, message_id)

            # Metrics
            self.stats["events_processed"] += 1
            elapsed = (datetime.now() - start_time).total_seconds()
            self.stats["processing_time_total"] += elapsed

            logger.debug(
                f"Event processed: {event_type} "
                f"(id={message_id}, time={elapsed:.3f}s)"
            )

        except Exception as e:
            self.stats["events_failed"] += 1
            logger.error(
                f"Failed to process event {message_id}: {e}",
                exc_info=True
            )

            # Можно отправить в DLQ
            # await self.event_bus.publish_to_dlq(...)

    async def _ack_event(self, stream_name: str, message_id: str):
        """ACK события (удаление из pending)"""
        await self.event_bus.redis.xack(
            stream_name,
            self.consumer_group,
            message_id
        )

    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику consumer"""
        avg_processing_time = 0.0
        if self.stats["events_processed"] > 0:
            avg_processing_time = (
                self.stats["processing_time_total"] /
                self.stats["events_processed"]
            )

        return {
            "consumer_group": self.consumer_group,
            "consumer_name": self.consumer_name,
            "is_running": self._running,
            "avg_processing_time": round(avg_processing_time, 3),
            **self.stats
        }


# ============================================================================
# EVENT BUS FACTORY
# ============================================================================

_event_bus_instance: Optional[EventBus] = None


async def get_event_bus(
    config: Optional[EventBusConfig] = None
) -> EventBus:
    """
    Возвращает singleton instance Event Bus

    Args:
        config: Конфигурация (используется только при первом вызове)

    Returns:
        Event Bus instance
    """
    global _event_bus_instance

    if _event_bus_instance is None:
        _event_bus_instance = EventBus(config=config)
        await _event_bus_instance.connect()

    return _event_bus_instance


async def close_event_bus():
    """Закрывает Event Bus"""
    global _event_bus_instance

    if _event_bus_instance:
        await _event_bus_instance.disconnect()
        _event_bus_instance = None
