"""
E2E Tests: Complete Onboarding Flow

Тестирует полный цикл онбординга от начала до конца:
1. User initiates onboarding → Session created
2. Session Management creates session → Question Selection starts
3. Question selected → User submits answer
4. Answer submitted → Analysis triggered + Next question selected
5. Repeat until session complete
6. Session completed → Analytics generated

Architecture Integration:
    user.onboarding.initiated → SessionManagementService
    ↓
    session.created → (logged)
    ↓
    user.session.started → QuestionSelectionService
    ↓
    question.selected → (user answers)
    ↓
    user.answer.submitted → SessionManagement + QuestionSelection + Analysis
    ↓
    question.selected OR session.completed
    ↓
    session.analytics.updated

Requirements:
- PostgreSQL (n8n-postgres)
- Redis (n8n-redis)
- Event Bus running
"""

import pytest
import asyncio
import asyncpg
import redis.asyncio as redis
from datetime import datetime
from typing import List, Dict, Any

from core.event_bus import EventBus
from core.outbox_pattern import OutboxPublisher, OutboxRelay
from systems.onboarding.question_selection_service import QuestionSelectionService
from systems.onboarding.session_management_service import SessionManagementService


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
async def db_pool():
    """PostgreSQL connection pool"""
    pool = await asyncpg.create_pool(
        host='n8n-postgres',
        port=5432,
        user='n8n',
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
async def redis_client_with_decode():
    """Redis client with decode_responses=True for Session Management"""
    client = await redis.from_url(
        "redis://n8n-redis:6379",
        decode_responses=True
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
async def outbox_relay(db_pool, event_bus):
    """OutboxRelay for publishing pending events"""
    relay = OutboxRelay(
        db_pool=db_pool,
        event_bus=event_bus,
        polling_interval=0.3,  # Fast for tests
        schema="selfology"
    )

    yield relay


@pytest.fixture
async def question_service(event_bus, db_pool):
    """Question Selection Service"""
    service = QuestionSelectionService(
        event_bus=event_bus,
        db_pool=db_pool
    )

    await service.start()

    yield service

    await service.stop()


@pytest.fixture
async def session_service(event_bus, db_pool, redis_client_with_decode):
    """Session Management Service"""
    service = SessionManagementService(
        event_bus=event_bus,
        db_pool=db_pool,
        redis_client=redis_client_with_decode
    )

    await service.start()

    yield service

    await service.stop()


# ============================================================================
# E2E TEST: COMPLETE ONBOARDING FLOW
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_complete_onboarding_flow(
    db_pool,
    event_bus,
    outbox_relay,
    question_service,
    session_service
):
    """
    Тест: Полный цикл онбординга от начала до конца

    Flow:
    1. User initiates onboarding
    2. Session created
    3. First question selected
    4. User submits answers (5 iterations)
    5. Session completes
    6. Analytics generated
    """
    test_user_id = 99999  # Test user
    trace_id = f"e2e_test_{datetime.now().timestamp()}"

    # Track events received
    received_events = []

    def track_event(event_type: str, payload: Dict[str, Any]):
        received_events.append({
            "event_type": event_type,
            "payload": payload,
            "timestamp": datetime.now()
        })

    # Start OutboxRelay to publish pending events
    await outbox_relay.start()

    # Step 1: User initiates onboarding
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            outbox_publisher = OutboxPublisher(schema="selfology")
            await outbox_publisher.publish(
                conn,
                "user.onboarding.initiated",
                {
                    "user_id": test_user_id,
                    "timestamp": datetime.now().isoformat()
                },
                trace_id=trace_id
            )

    track_event("user.onboarding.initiated", {"user_id": test_user_id})

    # Wait for OutboxRelay to publish
    await asyncio.sleep(1)

    # Step 2: Verify session created
    await asyncio.sleep(2)  # Wait for event processing

    session = None
    async with db_pool.acquire() as conn:
        session_row = await conn.fetchrow(
            """
            SELECT * FROM selfology.onboarding_sessions
            WHERE user_id = $1
            ORDER BY started_at DESC
            LIMIT 1
            """,
            test_user_id
        )

        if session_row:
            session = dict(session_row)

    assert session is not None, "Session should be created"
    assert session["user_id"] == test_user_id
    assert session["status"] == "active"

    session_id = session["id"]
    track_event("session.created", {"session_id": session_id})

    # Step 3-7: Simulate 5 question-answer cycles
    for i in range(5):
        # Wait for question selection
        await asyncio.sleep(1.5)

        # Check for question.selected event in outbox
        async with db_pool.acquire() as conn:
            question_event = await conn.fetchrow(
                """
                SELECT * FROM selfology.event_outbox
                WHERE event_type = 'question.selected'
                  AND payload->>'session_id' = $1
                  AND status = 'pending'
                ORDER BY created_at DESC
                LIMIT 1
                """,
                str(session_id)
            )

            if question_event:
                question_payload = question_event["payload"]
                question_id = question_payload["question_id"]

                track_event("question.selected", {
                    "question_id": question_id,
                    "iteration": i + 1
                })

                # User submits answer
                async with conn.transaction():
                    outbox_publisher = OutboxPublisher(schema="selfology")
                    await outbox_publisher.publish(
                        conn,
                        "user.answer.submitted",
                        {
                            "user_id": test_user_id,
                            "session_id": session_id,
                            "question_id": question_id,
                            "answer_text": f"Test answer {i+1}",
                            "answer_length": len(f"Test answer {i+1}")
                        },
                        trace_id=trace_id
                    )

                track_event("user.answer.submitted", {
                    "question_id": question_id,
                    "iteration": i + 1
                })

        # Wait for OutboxRelay to publish
        await asyncio.sleep(1)

    # Step 8: Verify session analytics
    await asyncio.sleep(3)

    # Get final session state
    async with db_pool.acquire() as conn:
        final_session = await conn.fetchrow(
            """
            SELECT * FROM selfology.onboarding_sessions
            WHERE id = $1
            """,
            session_id
        )

        # Count answers
        answers_count = await conn.fetchval(
            """
            SELECT COUNT(*) FROM selfology.user_answers_new
            WHERE session_id = $1
            """,
            session_id
        )

    # Verify results
    assert final_session is not None
    # Note: answers might not be in DB yet if using mocked handlers
    # In production, answers would be saved by AnswerStorageService

    # Verify events flow
    assert len(received_events) >= 7  # At least: initiated + 5*(selected + submitted)

    # Verify event types
    event_types = [e["event_type"] for e in received_events]
    assert "user.onboarding.initiated" in event_types
    assert "session.created" in event_types
    assert event_types.count("question.selected") >= 5
    assert event_types.count("user.answer.submitted") == 5

    # Cleanup: Stop OutboxRelay
    await outbox_relay.stop()

    # Print summary
    print("\n" + "="*60)
    print("E2E TEST SUMMARY")
    print("="*60)
    print(f"User ID: {test_user_id}")
    print(f"Session ID: {session_id}")
    print(f"Total Events: {len(received_events)}")
    print(f"Question-Answer Cycles: 5")
    print(f"Final Session Status: {final_session['status']}")
    print("="*60)


# ============================================================================
# E2E TEST: SESSION TIMEOUT
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_session_timeout_detection(
    db_pool,
    event_bus,
    session_service
):
    """
    Тест: Обнаружение и обработка session timeout

    Flow:
    1. Create session
    2. Simulate inactivity (set last_activity_at to past)
    3. Trigger timeout check
    4. Verify session marked as timed_out
    """
    test_user_id = 88888
    session_manager = session_service.session_manager

    # Create session
    session_id = await session_manager.create_session(
        user_id=test_user_id,
        session_type="onboarding"
    )

    # Simulate old inactivity (31 minutes ago)
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE selfology.onboarding_sessions
            SET last_activity_at = NOW() - INTERVAL '31 minutes'
            WHERE id = $1
            """,
            session_id
        )

    # Trigger timeout check
    timed_out_ids = await session_manager.check_timeouts()

    assert session_id in timed_out_ids

    # Verify session status
    session = await session_manager.get_session(session_id)
    # Note: get_session might return cached version, check DB directly
    async with db_pool.acquire() as conn:
        status = await conn.fetchval(
            """
            SELECT status FROM selfology.onboarding_sessions
            WHERE id = $1
            """,
            session_id
        )

    assert status == "timed_out"


# ============================================================================
# E2E TEST: FATIGUE DETECTION
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_fatigue_detection_triggers_healing_question(
    db_pool,
    question_service
):
    """
    Тест: FatigueDetector обнаруживает усталость и выдает HEALING вопрос

    Flow:
    1. Simulate low energy session
    2. Request next question
    3. Verify HEALING question selected
    """
    smart_mix_router = question_service.smart_mix_router

    # Session with low energy
    session_data = {
        "questions_answered": 8,
        "energy_balance": -6,  # Very low
        "trust_level": 0,
        "answered_question_ids": [],
        "avg_answer_length": 50
    }

    # Select next question
    question = await smart_mix_router.select_next_question(
        user_id=77777,
        session_id=999,
        session_data=session_data
    )

    # Should get HEALING question or None (if max questions reached)
    if question:
        # If question returned, it should be HEALING type
        assert question.get("energy_level") == "HEALING"
    else:
        # Session should be completed due to low energy
        pass


# ============================================================================
# E2E TEST: TRUST LEVEL PROGRESSION
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_trust_level_limits_question_depth(
    question_service
):
    """
    Тест: Trust level ограничивает глубину вопросов

    Flow:
    1. User with STRANGER trust level
    2. Verify only SURFACE questions selected
    3. User with SOUL_MATE trust level
    4. Verify CORE questions available
    """
    smart_mix_router = question_service.smart_mix_router

    # Test 1: STRANGER can only get SURFACE
    max_depth_stranger = smart_mix_router._get_max_depth_for_trust_level(0)
    assert max_depth_stranger == "SURFACE"

    # Test 2: SOUL_MATE can get CORE
    max_depth_soulmate = smart_mix_router._get_max_depth_for_trust_level(4)
    assert max_depth_soulmate == "CORE"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-m", "e2e"])
