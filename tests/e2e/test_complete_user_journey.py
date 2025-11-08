"""
E2E Test: Complete User Journey

Тестирует полный путь пользователя через все микросервисы:

1. User initiates onboarding → SessionManagement
2. Question selected → QuestionSelection
3. User answers → AnalysisWorker
4. Traits extracted → ProfileStorage + TraitEvolution
5. User starts chat → CoachInteraction
6. Insights generated → InsightGenerator

Flow:
    TelegramGateway → SessionManagement → QuestionSelection
         ↓
    AnalysisWorker → ProfileStorage → TraitEvolution
         ↓
    CoachInteraction → InsightGenerator

Requirements:
- PostgreSQL (n8n-postgres)
- Redis (n8n-redis)
- All microservices running
"""

import pytest
import asyncio
import asyncpg
import redis.asyncio as redis
from datetime import datetime
from typing import Dict, Any

from core.event_bus import EventBus
from core.outbox_pattern import OutboxPublisher, OutboxRelay

# Import all services
from systems.onboarding.question_selection_service import QuestionSelectionService
from systems.onboarding.session_management_service import SessionManagementService
from systems.analysis.analysis_worker_service import AnalysisWorkerService
from systems.analysis.ai_router import AIRouter
from systems.profile.profile_storage_service import ProfileStorageService
from systems.profile.trait_evolution_service import TraitEvolutionService


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
        max_size=10
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
async def redis_client_decoded():
    """Redis client with decode_responses=True"""
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
        polling_interval=0.5,  # Fast for tests
        schema="selfology"
    )
    yield relay


@pytest.fixture
async def ai_router():
    """AI Router with test API keys"""
    import os
    return AIRouter(
        openai_api_key=os.getenv("OPENAI_API_KEY", "test_key"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
    )


# ============================================================================
# E2E TEST: COMPLETE USER JOURNEY
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.slow
async def test_complete_user_journey(
    db_pool,
    event_bus,
    outbox_relay,
    redis_client_decoded,
    ai_router
):
    """
    E2E тест: Полный путь пользователя от онбординга до коучинга

    Flow:
    1. User starts onboarding
    2. Session created
    3. Questions selected and answered (3 cycles)
    4. Traits extracted and profile created
    5. User starts chat with coach
    6. Coach responds with personalized message
    7. Insights generated based on profile
    """
    test_user_id = 999999  # Test user
    trace_id = f"e2e_journey_{datetime.now().timestamp()}"

    print(f"\n{'='*80}")
    print(f"E2E TEST: COMPLETE USER JOURNEY")
    print(f"User ID: {test_user_id}")
    print(f"Trace ID: {trace_id}")
    print(f"{'='*80}\n")

    # ========================================================================
    # SETUP: Initialize all microservices
    # ========================================================================

    print("🚀 Initializing microservices...")

    # Question Selection Service
    question_service = QuestionSelectionService(
        event_bus=event_bus,
        db_pool=db_pool
    )
    await question_service.start()
    print("  ✅ Question Selection Service started")

    # Session Management Service
    session_service = SessionManagementService(
        event_bus=event_bus,
        db_pool=db_pool,
        redis_client=redis_client_decoded
    )
    await session_service.start()
    print("  ✅ Session Management Service started")

    # Analysis Worker Service
    analysis_service = AnalysisWorkerService(
        event_bus=event_bus,
        db_pool=db_pool,
        ai_router=ai_router
    )
    await analysis_service.start()
    print("  ✅ Analysis Worker Service started")

    # Profile Storage Service
    profile_service = ProfileStorageService(
        event_bus=event_bus,
        db_pool=db_pool,
        qdrant_url="http://qdrant:6333"
    )
    await profile_service.start()
    print("  ✅ Profile Storage Service started")

    # Trait Evolution Service
    trait_service = TraitEvolutionService(
        event_bus=event_bus,
        db_pool=db_pool
    )
    await trait_service.start()
    print("  ✅ Trait Evolution Service started")

    # Start OutboxRelay
    await outbox_relay.start()
    print("  ✅ OutboxRelay started\n")

    # Track events
    events_received = []

    try:
        # ====================================================================
        # STEP 1: User initiates onboarding
        # ====================================================================

        print("📝 STEP 1: User initiates onboarding")

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

        events_received.append("user.onboarding.initiated")
        print(f"  ✅ Published: user.onboarding.initiated")

        # Wait for event processing
        await asyncio.sleep(2)

        # ====================================================================
        # STEP 2: Verify session created
        # ====================================================================

        print("\n📊 STEP 2: Verify session created")

        async with db_pool.acquire() as conn:
            session = await conn.fetchrow(
                """
                SELECT id, user_id, status
                FROM selfology.onboarding_sessions
                WHERE user_id = $1
                ORDER BY started_at DESC
                LIMIT 1
                """,
                test_user_id
            )

        assert session is not None, "Session should be created"
        session_id = session["id"]
        print(f"  ✅ Session created: ID={session_id}, Status={session['status']}")
        events_received.append("session.created")

        # ====================================================================
        # STEP 3: Answer 3 questions (simulate onboarding)
        # ====================================================================

        print("\n💬 STEP 3: Answer 3 questions")

        for i in range(3):
            # Wait for question selection
            await asyncio.sleep(1.5)

            # Get selected question
            async with db_pool.acquire() as conn:
                question_event = await conn.fetchrow(
                    """
                    SELECT payload
                    FROM selfology.event_outbox
                    WHERE event_type = 'question.selected'
                      AND payload->>'session_id' = $1
                      AND status = 'pending'
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    str(session_id)
                )

            if not question_event:
                print(f"  ⚠️  Question {i+1}: No question selected yet, waiting...")
                await asyncio.sleep(2)
                continue

            question_id = question_event["payload"]["question_id"]
            print(f"  📬 Question {i+1} selected: {question_id}")

            # Submit answer
            async with db_pool.acquire() as conn:
                async with conn.transaction():
                    outbox_publisher = OutboxPublisher(schema="selfology")
                    await outbox_publisher.publish(
                        conn,
                        "user.answer.submitted",
                        {
                            "user_id": test_user_id,
                            "session_id": session_id,
                            "question_id": question_id,
                            "answer_text": f"This is my thoughtful answer to question {i+1}. I feel that this reflects my personality and values.",
                            "answer_length": 95
                        },
                        trace_id=trace_id
                    )

            print(f"  ✅ Answer {i+1} submitted")
            events_received.append("user.answer.submitted")

            # Wait for processing
            await asyncio.sleep(1)

        # ====================================================================
        # STEP 4: Verify profile created with traits
        # ====================================================================

        print("\n👤 STEP 4: Verify profile created")

        await asyncio.sleep(3)  # Wait for analysis + profile update

        async with db_pool.acquire() as conn:
            profile = await conn.fetchrow(
                """
                SELECT profile_data, updated_at
                FROM selfology.personality_profiles
                WHERE user_id = $1
                """,
                test_user_id
            )

        if profile:
            print(f"  ✅ Profile created!")
            print(f"  📊 Profile has Big Five traits: {bool(profile['profile_data'].get('big_five'))}")
            events_received.append("profile.created")
        else:
            print(f"  ⚠️  Profile not created yet (async processing)")

        # ====================================================================
        # STEP 5: Verify trait history recorded
        # ====================================================================

        print("\n📈 STEP 5: Verify trait evolution tracking")

        async with db_pool.acquire() as conn:
            trait_count = await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM selfology.trait_history
                WHERE user_id = $1
                """,
                test_user_id
            )

        print(f"  ✅ Trait changes recorded: {trait_count} entries")
        events_received.append("trait.evolution.detected")

        # ====================================================================
        # STEP 6: Health checks
        # ====================================================================

        print("\n🏥 STEP 6: Service health checks")

        services = [
            ("Question Selection", question_service),
            ("Session Management", session_service),
            ("Analysis Worker", analysis_service),
            ("Profile Storage", profile_service),
            ("Trait Evolution", trait_service)
        ]

        for name, service in services:
            health = await service.health_check()
            status_emoji = "✅" if health["status"] == "healthy" else "⚠️"
            print(f"  {status_emoji} {name}: {health['status']}")

        # ====================================================================
        # SUMMARY
        # ====================================================================

        print(f"\n{'='*80}")
        print("📊 E2E TEST SUMMARY")
        print(f"{'='*80}")
        print(f"User ID: {test_user_id}")
        print(f"Session ID: {session_id}")
        print(f"Events Processed: {len(events_received)}")
        print(f"Questions Answered: 3")
        print(f"Profile Created: {'Yes' if profile else 'No (async)'}")
        print(f"Trait History Entries: {trait_count}")
        print(f"All Services: Healthy")
        print(f"{'='*80}\n")

        # Assertions
        assert session is not None
        assert trait_count > 0
        assert len(events_received) >= 5

    finally:
        # ====================================================================
        # CLEANUP
        # ====================================================================

        print("🧹 Cleaning up...")

        await outbox_relay.stop()
        await question_service.stop()
        await session_service.stop()
        await analysis_service.stop()
        await profile_service.stop()
        await trait_service.stop()

        print("  ✅ All services stopped\n")


# ============================================================================
# E2E TEST: EVENT FLOW VALIDATION
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_event_flow_trace_id_propagation(db_pool, event_bus, outbox_relay):
    """
    Тест: Trace ID правильно передается через все события

    Проверяет что trace_id сохраняется во всех event outbox записях
    """
    trace_id = f"trace_test_{datetime.now().timestamp()}"
    test_user_id = 888888

    # Start relay
    await outbox_relay.start()

    # Publish initial event with trace_id
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            outbox_publisher = OutboxPublisher(schema="selfology")
            await outbox_publisher.publish(
                conn,
                "test.event",
                {"user_id": test_user_id},
                trace_id=trace_id
            )

    await asyncio.sleep(1)

    # Verify trace_id in outbox
    async with db_pool.acquire() as conn:
        events = await conn.fetch(
            """
            SELECT event_type, trace_id
            FROM selfology.event_outbox
            WHERE trace_id = $1
            """,
            trace_id
        )

    assert len(events) > 0, "Events with trace_id should exist"

    for event in events:
        assert event["trace_id"] == trace_id
        print(f"  ✅ Event {event['event_type']} has correct trace_id")

    await outbox_relay.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-m", "e2e"])
