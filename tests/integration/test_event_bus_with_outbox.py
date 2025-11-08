"""
Integration Tests: Event Bus + Outbox Pattern

Тестирует полный цикл событий:
1. Сохранение в БД через Outbox Pattern
2. OutboxRelay публикует в Event Bus
3. EventConsumer получает и обрабатывает событие
4. ACK события

Requirements:
- PostgreSQL (n8n-postgres)
- Redis (n8n-redis)
"""

import pytest
import asyncio
import asyncpg
import redis.asyncio as redis
from datetime import datetime

from core.outbox_pattern import OutboxPublisher, OutboxRelay, OutboxStatus
from core.event_bus import EventBus, EventConsumer, EventBusConfig
from core.domain_events import UserAnswerSubmittedEventV1, EventPriority


@pytest.fixture
async def db_pool():
    """PostgreSQL connection pool"""
    pool = await asyncpg.create_pool(
        host='n8n-postgres',
        port=5432,
        user='postgres',
        password='sS67wM+1zMBRFHAW4kj9HwFl5J6+veo7Nirx0/I+oiU=',
        database='n8n',
        min_size=1,
        max_size=5
    )

    yield pool

    await pool.close()


@pytest.fixture
async def redis_client():
    """Redis client"""
    client = await redis.from_url(
        "redis://n8n-redis:6379",
        decode_responses=False
    )

    yield client

    await client.close()


@pytest.fixture
async def event_bus(redis_client):
    """Event Bus instance"""
    bus = EventBus(redis_client=redis_client)
    await bus.connect()

    yield bus

    await bus.disconnect()


@pytest.fixture
async def outbox_publisher():
    """Outbox Publisher"""
    return OutboxPublisher(schema="selfology")


@pytest.mark.asyncio
async def test_outbox_pattern_saves_event_in_transaction(db_pool, outbox_publisher):
    """
    Тест: Outbox Pattern сохраняет событие в одной транзакции с данными
    """
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            # Simulate saving business data
            test_data_id = await conn.fetchval(
                "INSERT INTO selfology.test_data (value) VALUES ($1) RETURNING id",
                "test_value"
            )

            # Publish event через Outbox
            event_id = await outbox_publisher.publish(
                conn,
                "user.answer.submitted",
                {
                    "user_id": 123,
                    "question_id": "q_001",
                    "answer_text": "Test answer",
                    "answer_length": 11
                },
                trace_id="test_trace_123"
            )

            assert event_id is not None

        # Verify event saved in outbox
        event = await conn.fetchrow(
            "SELECT * FROM selfology.event_outbox WHERE id = $1",
            event_id
        )

        assert event is not None
        assert event['event_type'] == "user.answer.submitted"
        assert event['status'] == OutboxStatus.PENDING.value
        assert event['trace_id'] == "test_trace_123"
        assert event['retry_count'] == 0


@pytest.mark.asyncio
async def test_outbox_relay_publishes_to_event_bus(
    db_pool,
    event_bus,
    outbox_publisher
):
    """
    Тест: OutboxRelay читает pending события и публикует в Event Bus
    """
    # 1. Create pending event in outbox
    async with db_pool.acquire() as conn:
        event_id = await outbox_publisher.publish(
            conn,
            "user.answer.submitted",
            {
                "user_id": 456,
                "question_id": "q_002",
                "answer_text": "Another test answer",
                "answer_length": 19
            }
        )

    # 2. Start OutboxRelay
    relay = OutboxRelay(
        db_pool=db_pool,
        event_bus=event_bus,
        polling_interval=0.5  # Fast polling for tests
    )

    await relay.start()

    # 3. Wait for relay to process
    await asyncio.sleep(2)

    # 4. Verify event published
    async with db_pool.acquire() as conn:
        event = await conn.fetchrow(
            "SELECT * FROM selfology.event_outbox WHERE id = $1",
            event_id
        )

        assert event['status'] == OutboxStatus.PUBLISHED.value
        assert event['published_at'] is not None

    # Cleanup
    await relay.stop()


@pytest.mark.asyncio
async def test_full_event_cycle_with_consumer(
    db_pool,
    event_bus,
    outbox_publisher
):
    """
    Тест: Полный цикл события от Outbox до Consumer

    Flow:
    1. Бизнес-логика → Outbox
    2. OutboxRelay → Event Bus
    3. EventConsumer → обработка
    """
    received_events = []

    # Handler для consumer
    async def handle_event(event_type: str, payload: dict):
        received_events.append({
            "event_type": event_type,
            "payload": payload,
            "received_at": datetime.now()
        })

    # 1. Create consumer
    consumer = EventConsumer(
        event_bus=event_bus,
        consumer_group="test_consumer_group",
        consumer_name="test_worker",
        event_types=["user.answer.submitted"],
        handler=handle_event
    )

    await consumer.start()

    # 2. Publish event через Outbox
    async with db_pool.acquire() as conn:
        await outbox_publisher.publish(
            conn,
            "user.answer.submitted",
            {
                "user_id": 789,
                "question_id": "q_003",
                "answer_text": "Full cycle test",
                "answer_length": 15
            },
            trace_id="full_cycle_test"
        )

    # 3. Start OutboxRelay
    relay = OutboxRelay(
        db_pool=db_pool,
        event_bus=event_bus,
        polling_interval=0.5
    )

    await relay.start()

    # 4. Wait for processing
    await asyncio.sleep(3)

    # 5. Verify event received by consumer
    assert len(received_events) == 1
    assert received_events[0]['event_type'] == "user.answer.submitted"
    assert received_events[0]['payload']['user_id'] == 789

    # Cleanup
    await relay.stop()
    await consumer.stop()


@pytest.mark.asyncio
async def test_outbox_retry_on_failure(
    db_pool,
    event_bus,
    outbox_publisher
):
    """
    Тест: Outbox retry при ошибке публикации
    """
    # Create failing event bus (simulated)
    class FailingEventBus:
        call_count = 0

        async def publish(self, event_type, payload, **kwargs):
            self.call_count += 1
            if self.call_count < 3:
                raise Exception("Simulated publish failure")
            # 3rd attempt succeeds
            return "success"

    failing_bus = FailingEventBus()

    # Create event in outbox
    async with db_pool.acquire() as conn:
        event_id = await outbox_publisher.publish(
            conn,
            "test.retry.event",
            {"data": "retry_test"}
        )

    # Start relay with failing bus
    relay = OutboxRelay(
        db_pool=db_pool,
        event_bus=failing_bus,
        polling_interval=0.3,
        retry_delay_base=0.5  # Fast retry for tests
    )

    await relay.start()

    # Wait for retries
    await asyncio.sleep(3)

    # Verify retries happened
    assert failing_bus.call_count >= 3

    # Verify event eventually published
    async with db_pool.acquire() as conn:
        event = await conn.fetchrow(
            "SELECT * FROM selfology.event_outbox WHERE id = $1",
            event_id
        )

        assert event['retry_count'] >= 2
        # Eventually succeeds
        if failing_bus.call_count >= 3:
            assert event['status'] == OutboxStatus.PUBLISHED.value

    await relay.stop()


@pytest.mark.asyncio
async def test_outbox_moves_to_dlq_after_max_retries(
    db_pool,
    outbox_publisher
):
    """
    Тест: Событие перемещается в DLQ после max retries
    """
    # Always failing event bus
    class AlwaysFailingEventBus:
        async def publish(self, event_type, payload, **kwargs):
            raise Exception("Permanent failure")

    failing_bus = AlwaysFailingEventBus()

    # Create event
    async with db_pool.acquire() as conn:
        event_id = await outbox_publisher.publish(
            conn,
            "test.dlq.event",
            {"data": "dlq_test"}
        )

    # Relay with max 3 retries
    relay = OutboxRelay(
        db_pool=db_pool,
        event_bus=failing_bus,
        polling_interval=0.3,
        max_retries=3,
        retry_delay_base=0.3
    )

    await relay.start()

    # Wait for max retries
    await asyncio.sleep(5)

    # Verify moved to DLQ (failed status)
    async with db_pool.acquire() as conn:
        event = await conn.fetchrow(
            "SELECT * FROM selfology.event_outbox WHERE id = $1",
            event_id
        )

        assert event['status'] == OutboxStatus.FAILED.value
        assert event['retry_count'] == 3
        assert event['last_error'] is not None

    await relay.stop()


@pytest.mark.asyncio
async def test_event_bus_priority_queues(event_bus):
    """
    Тест: Event Bus обрабатывает priority queues
    """
    # Publish events with different priorities
    await event_bus.publish(
        "test.low.priority",
        {"priority": "low"},
        priority=EventPriority.LOW
    )

    await event_bus.publish(
        "test.critical.priority",
        {"priority": "critical"},
        priority=EventPriority.CRITICAL
    )

    await event_bus.publish(
        "test.normal.priority",
        {"priority": "normal"},
        priority=EventPriority.NORMAL
    )

    # Verify events in different streams
    critical_stream = "selfology:events:critical"
    normal_stream = "selfology:events:normal"
    low_stream = "selfology:events:low"

    # Check stream lengths
    critical_len = await event_bus.redis.xlen(critical_stream)
    normal_len = await event_bus.redis.xlen(normal_stream)
    low_len = await event_bus.redis.xlen(low_stream)

    assert critical_len >= 1
    assert normal_len >= 1
    assert low_len >= 1


@pytest.mark.asyncio
async def test_event_compression_for_large_payload(event_bus):
    """
    Тест: Event Bus сжимает большие payload
    """
    # Create large payload (> 1KB)
    large_text = "x" * 2000

    await event_bus.publish(
        "test.large.payload",
        {"large_field": large_text},
        priority=EventPriority.NORMAL
    )

    # Verify compression happened
    assert event_bus.stats["events_compressed"] >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
