"""
Outbox Pattern Implementation for Event-Driven Architecture

Решает проблему атомарности операций "сохранить в БД + опубликовать событие"
без использования двухфазных коммитов (2PC).

Архитектура:
1. OutboxPublisher - сохраняет события в outbox таблицу в той же транзакции
2. OutboxRelay - фоновый worker читает outbox и публикует в Event Bus
3. Event гарантированно публикуется даже при сбое между DB commit и Event Bus

Usage:
    # В бизнес-логике
    async with db.transaction():
        user_id = await save_user(conn, user_data)
        await outbox.publish(conn, "user.created", {"user_id": user_id})

    # Фоновый worker
    relay = OutboxRelay(db, event_bus)
    await relay.start()  # Работает постоянно
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from enum import Enum

import asyncpg
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class OutboxStatus(str, Enum):
    """Статусы события в outbox таблице"""
    PENDING = "pending"      # Ожидает публикации
    PUBLISHED = "published"  # Успешно опубликовано
    FAILED = "failed"        # Ошибка публикации (после max retries)


class OutboxEvent(BaseModel):
    """Модель события в outbox таблице"""
    id: Optional[int] = None
    event_type: str = Field(..., description="Тип события (user.created, profile.updated)")
    payload: Dict[str, Any] = Field(..., description="Данные события")
    status: OutboxStatus = Field(OutboxStatus.PENDING, description="Статус обработки")
    retry_count: int = Field(0, description="Количество попыток")
    created_at: datetime = Field(default_factory=datetime.now)
    published_at: Optional[datetime] = None
    last_error: Optional[str] = None
    trace_id: Optional[str] = Field(None, description="Trace ID для distributed tracing")


class OutboxPublisher:
    """
    Публикует события в outbox таблицу

    Гарантирует атомарность: если транзакция откатится, событие не будет сохранено
    """

    def __init__(self, schema: str = "selfology"):
        self.schema = schema
        self.table_name = f"{schema}.event_outbox"

    async def publish(
        self,
        conn: asyncpg.Connection,
        event_type: str,
        payload: Dict[str, Any],
        trace_id: Optional[str] = None
    ) -> int:
        """
        Сохраняет событие в outbox таблицу в рамках существующей транзакции

        Args:
            conn: Активное соединение с БД (в транзакции)
            event_type: Тип события (например "user.answer.submitted")
            payload: Данные события
            trace_id: ID для distributed tracing

        Returns:
            ID созданной записи в outbox

        Example:
            async with pool.acquire() as conn:
                async with conn.transaction():
                    answer_id = await save_answer(conn, answer_data)

                    await outbox.publish(
                        conn,
                        "user.answer.submitted",
                        {"answer_id": answer_id, "user_id": user_id},
                        trace_id=request_id
                    )
        """
        event = OutboxEvent(
            event_type=event_type,
            payload=payload,
            trace_id=trace_id
        )

        query = f"""
            INSERT INTO {self.table_name}
            (event_type, payload, status, retry_count, created_at, trace_id)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
        """

        event_id = await conn.fetchval(
            query,
            event.event_type,
            json.dumps(event.payload),
            event.status.value,
            event.retry_count,
            event.created_at,
            event.trace_id
        )

        logger.debug(
            f"Outbox event saved: {event_type} (id={event_id}, trace_id={trace_id})"
        )

        return event_id

    async def publish_batch(
        self,
        conn: asyncpg.Connection,
        events: List[tuple[str, Dict[str, Any]]]
    ) -> List[int]:
        """
        Сохраняет несколько событий одной операцией (оптимизация)

        Args:
            conn: Активное соединение с БД
            events: Список кортежей (event_type, payload)

        Returns:
            Список ID созданных событий
        """
        if not events:
            return []

        query = f"""
            INSERT INTO {self.table_name}
            (event_type, payload, status, retry_count, created_at)
            VALUES ($1, $2, $3, 0, NOW())
            RETURNING id
        """

        event_ids = []
        for event_type, payload in events:
            event_id = await conn.fetchval(
                query,
                event_type,
                json.dumps(payload),
                OutboxStatus.PENDING.value
            )
            event_ids.append(event_id)

        logger.debug(f"Outbox batch saved: {len(events)} events")

        return event_ids


class OutboxRelay:
    """
    Фоновый worker, который читает pending события из outbox и публикует в Event Bus

    Features:
    - Автоматический retry с exponential backoff
    - Dead Letter Queue (события после max_retries помечаются как FAILED)
    - Graceful shutdown
    - Мониторинг производительности
    """

    def __init__(
        self,
        db_pool: asyncpg.Pool,
        event_bus: Any,  # EventBus instance
        schema: str = "selfology",
        batch_size: int = 100,
        polling_interval: float = 1.0,
        max_retries: int = 5,
        retry_delay_base: float = 2.0
    ):
        """
        Args:
            db_pool: Connection pool к PostgreSQL
            event_bus: Instance Event Bus для публикации событий
            schema: Схема БД с outbox таблицей
            batch_size: Количество событий обрабатываемых за раз
            polling_interval: Интервал опроса таблицы (секунды)
            max_retries: Максимум попыток перед отправкой в DLQ
            retry_delay_base: База для exponential backoff (секунды)
        """
        self.db_pool = db_pool
        self.event_bus = event_bus
        self.schema = schema
        self.table_name = f"{schema}.event_outbox"
        self.batch_size = batch_size
        self.polling_interval = polling_interval
        self.max_retries = max_retries
        self.retry_delay_base = retry_delay_base

        self._running = False
        self._task: Optional[asyncio.Task] = None

        # Метрики
        self.stats = {
            "events_processed": 0,
            "events_failed": 0,
            "total_retries": 0,
            "last_batch_time": None
        }

    async def start(self):
        """Запускает фоновый worker"""
        if self._running:
            logger.warning("OutboxRelay already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._relay_loop())
        logger.info("OutboxRelay started")

    async def stop(self):
        """Graceful shutdown worker"""
        if not self._running:
            return

        self._running = False
        if self._task:
            await self._task

        logger.info("OutboxRelay stopped")

    async def _relay_loop(self):
        """Основной цикл обработки событий"""
        while self._running:
            try:
                batch_start = datetime.now()

                # Получаем pending события
                events = await self._fetch_pending_events()

                if events:
                    await self._process_batch(events)

                    batch_time = (datetime.now() - batch_start).total_seconds()
                    self.stats["last_batch_time"] = batch_time

                    logger.info(
                        f"Outbox batch processed: {len(events)} events in {batch_time:.2f}s"
                    )
                else:
                    # Нет событий - ждём
                    await asyncio.sleep(self.polling_interval)

            except Exception as e:
                logger.error(f"OutboxRelay error: {e}", exc_info=True)
                await asyncio.sleep(5)  # Backoff при ошибке

    async def _fetch_pending_events(self) -> List[Dict[str, Any]]:
        """Получает pending события из outbox"""
        async with self.db_pool.acquire() as conn:
            # Выбираем события ready для обработки:
            # 1. Status = PENDING
            # 2. Retry_count < max_retries
            # 3. Для событий с retry_count > 0 проверяем exponential backoff
            query = f"""
                SELECT id, event_type, payload, retry_count, created_at, trace_id
                FROM {self.table_name}
                WHERE status = $1
                  AND retry_count < $2
                  AND (
                    retry_count = 0
                    OR created_at + (INTERVAL '1 second' * POW($3, retry_count)) < NOW()
                  )
                ORDER BY created_at
                LIMIT $4
            """

            rows = await conn.fetch(
                query,
                OutboxStatus.PENDING.value,
                self.max_retries,
                self.retry_delay_base,
                self.batch_size
            )

            return [dict(row) for row in rows]

    async def _process_batch(self, events: List[Dict[str, Any]]):
        """Обрабатывает batch событий"""
        for event in events:
            await self._process_event(event)

    async def _process_event(self, event: Dict[str, Any]):
        """Публикует одно событие в Event Bus"""
        event_id = event["id"]
        event_type = event["event_type"]
        payload = event["payload"]
        retry_count = event["retry_count"]
        trace_id = event.get("trace_id")

        try:
            # Публикуем в Event Bus
            await self.event_bus.publish(
                event_type=event_type,
                payload=payload if isinstance(payload, dict) else json.loads(payload),
                trace_id=trace_id
            )

            # Помечаем как published
            await self._mark_published(event_id)

            self.stats["events_processed"] += 1

            logger.debug(
                f"Outbox event published: {event_type} "
                f"(id={event_id}, retries={retry_count}, trace_id={trace_id})"
            )

        except Exception as e:
            # Публикация не удалась
            new_retry_count = retry_count + 1

            if new_retry_count >= self.max_retries:
                # Достигнут лимит - отправляем в DLQ
                await self._mark_failed(event_id, str(e))
                self.stats["events_failed"] += 1

                logger.error(
                    f"Outbox event moved to DLQ: {event_type} "
                    f"(id={event_id}, retries={new_retry_count}). Error: {e}"
                )
            else:
                # Увеличиваем retry_count
                await self._increment_retry(event_id, str(e))
                self.stats["total_retries"] += 1

                logger.warning(
                    f"Outbox event retry scheduled: {event_type} "
                    f"(id={event_id}, retry={new_retry_count}/{self.max_retries}). Error: {e}"
                )

    async def _mark_published(self, event_id: int):
        """Помечает событие как опубликованное"""
        async with self.db_pool.acquire() as conn:
            query = f"""
                UPDATE {self.table_name}
                SET status = $1, published_at = NOW()
                WHERE id = $2
            """
            await conn.execute(query, OutboxStatus.PUBLISHED.value, event_id)

    async def _mark_failed(self, event_id: int, error: str):
        """Помечает событие как failed (DLQ)"""
        async with self.db_pool.acquire() as conn:
            query = f"""
                UPDATE {self.table_name}
                SET status = $1, last_error = $2
                WHERE id = $3
            """
            await conn.execute(query, OutboxStatus.FAILED.value, error[:500], event_id)

    async def _increment_retry(self, event_id: int, error: str):
        """Увеличивает счетчик retry"""
        async with self.db_pool.acquire() as conn:
            query = f"""
                UPDATE {self.table_name}
                SET retry_count = retry_count + 1, last_error = $1
                WHERE id = $2
            """
            await conn.execute(query, error[:500], event_id)

    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику работы"""
        return {
            **self.stats,
            "is_running": self._running
        }


class OutboxCleaner:
    """
    Утилита для очистки старых событий из outbox

    Рекомендуется запускать периодически (например раз в день)
    """

    def __init__(self, db_pool: asyncpg.Pool, schema: str = "selfology"):
        self.db_pool = db_pool
        self.schema = schema
        self.table_name = f"{schema}.event_outbox"

    async def cleanup_published(self, older_than_days: int = 7) -> int:
        """
        Удаляет опубликованные события старше N дней

        Args:
            older_than_days: Удалить события старше N дней

        Returns:
            Количество удаленных записей
        """
        async with self.db_pool.acquire() as conn:
            query = f"""
                DELETE FROM {self.table_name}
                WHERE status = $1
                  AND published_at < NOW() - INTERVAL '{older_than_days} days'
                RETURNING id
            """
            rows = await conn.fetch(query, OutboxStatus.PUBLISHED.value)

            count = len(rows)
            logger.info(f"Outbox cleanup: removed {count} published events older than {older_than_days} days")

            return count

    async def cleanup_failed(self, older_than_days: int = 30) -> int:
        """
        Удаляет failed события старше N дней

        Args:
            older_than_days: Удалить события старше N дней

        Returns:
            Количество удаленных записей
        """
        async with self.db_pool.acquire() as conn:
            query = f"""
                DELETE FROM {self.table_name}
                WHERE status = $1
                  AND created_at < NOW() - INTERVAL '{older_than_days} days'
                RETURNING id
            """
            rows = await conn.fetch(query, OutboxStatus.FAILED.value)

            count = len(rows)
            logger.info(f"Outbox cleanup: removed {count} failed events older than {older_than_days} days")

            return count

    async def get_failed_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Возвращает failed события для анализа

        Используется для debugging и ручного recovery
        """
        async with self.db_pool.acquire() as conn:
            query = f"""
                SELECT id, event_type, payload, retry_count, created_at, last_error, trace_id
                FROM {self.table_name}
                WHERE status = $1
                ORDER BY created_at DESC
                LIMIT $2
            """
            rows = await conn.fetch(query, OutboxStatus.FAILED.value, limit)

            return [dict(row) for row in rows]

    async def retry_failed_event(self, event_id: int):
        """
        Повторно пытается опубликовать failed событие

        Переводит событие обратно в PENDING с retry_count = 0
        """
        async with self.db_pool.acquire() as conn:
            query = f"""
                UPDATE {self.table_name}
                SET status = $1, retry_count = 0, last_error = NULL
                WHERE id = $2 AND status = $3
                RETURNING id
            """
            result = await conn.fetchval(
                query,
                OutboxStatus.PENDING.value,
                event_id,
                OutboxStatus.FAILED.value
            )

            if result:
                logger.info(f"Outbox event retry scheduled: id={event_id}")
                return True
            else:
                logger.warning(f"Outbox event not found or not failed: id={event_id}")
                return False


# Singleton instance для удобства использования в коде
_outbox_publisher: Optional[OutboxPublisher] = None


def get_outbox_publisher(schema: str = "selfology") -> OutboxPublisher:
    """Возвращает singleton instance OutboxPublisher"""
    global _outbox_publisher
    if _outbox_publisher is None:
        _outbox_publisher = OutboxPublisher(schema=schema)
    return _outbox_publisher
