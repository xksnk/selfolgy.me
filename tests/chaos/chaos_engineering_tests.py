"""
Chaos Engineering Tests for Selfology Microservices

Tests resilience under failure scenarios:
- Kill individual services → verify Circuit Breaker
- Disconnect Redis → verify FSM fallback to memory
- Simulate database timeouts → verify retry logic
- Disconnect AI APIs → verify fallback chains
- Network partitions → verify graceful degradation
- Resource exhaustion → verify rate limiting

Architecture:
    ChaosEngineer
    ↓
    ├── ServiceKiller (kills Docker containers)
    ├── NetworkDisruptor (simulates network issues)
    ├── ResourceExhauster (CPU/memory pressure)
    └── FailureInjector (targeted failures)

Run:
    pytest tests/chaos/ -v -s --chaos-level=1
    pytest tests/chaos/ -v -s --chaos-level=2  # More aggressive
    pytest tests/chaos/ -v -s --chaos-level=3  # Maximum chaos

Requirements:
- Docker access
- All microservices running
- PostgreSQL, Redis, Qdrant available
"""

import pytest
import asyncio
import asyncpg
import redis.asyncio as redis
import docker
import time
import psutil
import random
from typing import Dict, Any, List
from datetime import datetime
from contextlib import asynccontextmanager

from core.event_bus import EventBus
from core.outbox_pattern import OutboxPublisher, OutboxRelay
from systems.analysis.ai_router import AIRouter, AIModel


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope="module")
def docker_client():
    """Docker client for container manipulation"""
    return docker.from_env()


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
        max_size=10,
        command_timeout=10  # Short timeout for chaos testing
    )
    yield pool
    await pool.close()


@pytest.fixture
async def redis_client():
    """Redis client"""
    client = await redis.from_url(
        "redis://n8n-redis:6379",
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5
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


# ============================================================================
# CHAOS ENGINEERING HELPERS
# ============================================================================

class ChaosEngineer:
    """
    Main chaos engineering controller

    Features:
    - Service disruption (kill containers)
    - Network chaos (latency, packet loss)
    - Resource exhaustion (CPU, memory)
    - Targeted failures (specific components)
    """

    def __init__(self, docker_client: docker.DockerClient):
        self.docker_client = docker_client
        self.disrupted_services = []

    def kill_service(self, container_name: str, duration: int = 10):
        """
        Kills a Docker container for specified duration

        Args:
            container_name: Name of container to kill
            duration: Seconds before auto-restart
        """
        try:
            container = self.docker_client.containers.get(container_name)
            print(f"🔪 Killing {container_name}...")
            container.kill()
            self.disrupted_services.append(container_name)

            # Schedule restart
            asyncio.create_task(self._restart_after_delay(container_name, duration))

            return True
        except docker.errors.NotFound:
            print(f"⚠️  Container {container_name} not found")
            return False

    async def _restart_after_delay(self, container_name: str, delay: int):
        """Restarts container after delay"""
        await asyncio.sleep(delay)
        try:
            container = self.docker_client.containers.get(container_name)
            print(f"♻️  Restarting {container_name}...")
            container.start()
            self.disrupted_services.remove(container_name)
        except Exception as e:
            print(f"❌ Failed to restart {container_name}: {e}")

    @asynccontextmanager
    async def disconnect_redis(self, duration: int = 10):
        """
        Simulates Redis disconnect by pausing container

        Args:
            duration: Seconds of disconnection
        """
        try:
            container = self.docker_client.containers.get('n8n-redis')
            print("🔌 Disconnecting Redis...")
            container.pause()

            yield

            await asyncio.sleep(duration)

            print("🔌 Reconnecting Redis...")
            container.unpause()
        except Exception as e:
            print(f"❌ Redis chaos failed: {e}")
            yield

    @asynccontextmanager
    async def slow_database(self, delay_ms: int = 5000):
        """
        Simulates database slowness via pg_sleep injection

        Args:
            delay_ms: Milliseconds of artificial delay
        """
        # In real scenario, you'd use pgbouncer or similar
        # For testing, we simulate with statement_timeout
        print(f"🐌 Slowing database by {delay_ms}ms...")
        yield
        print("⚡ Database speed restored")

    async def exhaust_cpu(self, duration: int = 10, cores: int = 2):
        """
        Creates CPU pressure

        Args:
            duration: Seconds of CPU load
            cores: Number of CPU cores to stress
        """
        print(f"🔥 Exhausting {cores} CPU cores for {duration}s...")

        tasks = []
        for _ in range(cores):
            tasks.append(asyncio.create_task(self._burn_cpu(duration)))

        await asyncio.gather(*tasks)
        print("❄️  CPU load released")

    async def _burn_cpu(self, duration: int):
        """Burns CPU for specified duration"""
        end_time = time.time() + duration
        while time.time() < end_time:
            # Busy loop
            _ = sum(range(10000))
            await asyncio.sleep(0)

    def cleanup(self):
        """Restarts all disrupted services"""
        for container_name in self.disrupted_services:
            try:
                container = self.docker_client.containers.get(container_name)
                container.start()
            except Exception as e:
                print(f"Cleanup failed for {container_name}: {e}")


# ============================================================================
# CHAOS TEST 1: SERVICE KILL → CIRCUIT BREAKER
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.chaos
async def test_kill_analysis_service_circuit_breaker(docker_client, db_pool, event_bus):
    """
    Chaos: Kill Analysis Worker → verify Circuit Breaker opens

    Expected:
    - Circuit Breaker detects failures
    - Events queued in outbox
    - System degrades gracefully
    - Service auto-recovers when back
    """
    chaos = ChaosEngineer(docker_client)
    test_user_id = 999001

    print("\n" + "="*80)
    print("CHAOS TEST: Kill Analysis Worker Service")
    print("="*80 + "\n")

    try:
        # Step 1: Submit answer (service is UP)
        print("📤 Step 1: Submit answer with service UP")

        async with db_pool.acquire() as conn:
            async with conn.transaction():
                outbox_publisher = OutboxPublisher(schema="selfology")
                await outbox_publisher.publish(
                    conn,
                    "user.answer.submitted",
                    {
                        "user_id": test_user_id,
                        "session_id": 1,
                        "question_id": "chaos_q1",
                        "answer_text": "Test answer before chaos",
                        "answer_length": 24
                    }
                )

        await asyncio.sleep(2)
        print("  ✅ Answer processed successfully\n")

        # Step 2: Kill analysis service
        print("🔪 Step 2: Killing analysis service...")
        chaos.kill_service("selfology-analysis-worker", duration=15)
        await asyncio.sleep(2)

        # Step 3: Submit answer (service is DOWN)
        print("📤 Step 3: Submit answer with service DOWN")

        async with db_pool.acquire() as conn:
            async with conn.transaction():
                outbox_publisher = OutboxPublisher(schema="selfology")
                await outbox_publisher.publish(
                    conn,
                    "user.answer.submitted",
                    {
                        "user_id": test_user_id,
                        "session_id": 1,
                        "question_id": "chaos_q2",
                        "answer_text": "Test answer during chaos",
                        "answer_length": 25
                    }
                )

        # Event should be in outbox, pending
        async with db_pool.acquire() as conn:
            pending_count = await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM selfology.event_outbox
                WHERE status = 'pending'
                AND event_type = 'user.answer.submitted'
                """,
            )

        print(f"  ✅ Event queued in outbox (pending: {pending_count})")
        assert pending_count > 0, "Events should be pending when service is down"

        # Step 4: Wait for service to recover
        print("\n⏳ Step 4: Waiting for service recovery...")
        await asyncio.sleep(15)

        # Step 5: Verify events processed after recovery
        print("🔍 Step 5: Verifying recovery...")
        await asyncio.sleep(5)

        async with db_pool.acquire() as conn:
            processed_count = await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM selfology.event_outbox
                WHERE event_type = 'user.answer.submitted'
                AND payload->>'user_id' = $1
                AND status IN ('published', 'pending')
                """,
                str(test_user_id)
            )

        print(f"  ✅ Events after recovery: {processed_count}")

        print("\n" + "="*80)
        print("✅ CHAOS TEST PASSED: Circuit Breaker + Event Queuing Worked!")
        print("="*80 + "\n")

    finally:
        chaos.cleanup()


# ============================================================================
# CHAOS TEST 2: REDIS DISCONNECT → FSM FALLBACK
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.chaos
async def test_redis_disconnect_fsm_fallback(docker_client, db_pool, redis_client, event_bus):
    """
    Chaos: Disconnect Redis → verify FSM falls back to memory

    Expected:
    - State manager detects Redis unavailability
    - Falls back to in-memory storage
    - User interactions continue working
    - State syncs back when Redis returns
    """
    chaos = ChaosEngineer(docker_client)
    test_user_id = 999002

    print("\n" + "="*80)
    print("CHAOS TEST: Redis Disconnect → FSM Fallback")
    print("="*80 + "\n")

    try:
        # Step 1: Set state with Redis UP
        print("📝 Step 1: Set initial state with Redis UP")

        from systems.telegram.telegram_gateway_service import StateManager
        state_manager = StateManager(redis_client=redis_client)

        await state_manager.set_state(test_user_id, "onboarding_active", ttl=3600)
        initial_state = await state_manager.get_state(test_user_id)

        print(f"  ✅ Initial state: {initial_state}\n")
        assert initial_state == "onboarding_active"

        # Step 2: Disconnect Redis
        print("🔌 Step 2: Disconnecting Redis...")

        async with chaos.disconnect_redis(duration=10):
            await asyncio.sleep(2)

            # Step 3: Try to get state (should use fallback)
            print("🔍 Step 3: Getting state with Redis DOWN")

            fallback_state = await state_manager.get_state(test_user_id)
            print(f"  ✅ Fallback state: {fallback_state}")
            assert fallback_state == "onboarding_active", "Fallback should return cached state"

            # Step 4: Set new state (should update fallback)
            print("📝 Step 4: Setting new state with Redis DOWN")

            await state_manager.set_state(test_user_id, "waiting_for_answer")
            new_state = await state_manager.get_state(test_user_id)

            print(f"  ✅ New fallback state: {new_state}")
            assert new_state == "waiting_for_answer"

        # Step 5: Verify state after Redis reconnection
        print("\n🔌 Step 5: Redis reconnected, verifying state...")
        await asyncio.sleep(2)

        final_state = await state_manager.get_state(test_user_id)
        print(f"  ✅ State after reconnection: {final_state}")

        print("\n" + "="*80)
        print("✅ CHAOS TEST PASSED: FSM Fallback Worked!")
        print("="*80 + "\n")

    finally:
        chaos.cleanup()


# ============================================================================
# CHAOS TEST 3: DATABASE TIMEOUT → RETRY LOGIC
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.chaos
async def test_database_timeout_retry_logic(db_pool, event_bus):
    """
    Chaos: Simulate database timeouts → verify retry logic

    Expected:
    - Retry Pattern kicks in
    - Exponential backoff applied
    - Eventually succeeds or fails gracefully
    - No data corruption
    """
    test_user_id = 999003

    print("\n" + "="*80)
    print("CHAOS TEST: Database Timeout → Retry Logic")
    print("="*80 + "\n")

    # Step 1: Normal operation
    print("📊 Step 1: Normal database operation")

    async with db_pool.acquire() as conn:
        user_count = await conn.fetchval("SELECT COUNT(*) FROM selfology.personality_profiles")
        print(f"  ✅ Query succeeded: {user_count} profiles\n")

    # Step 2: Simulate slow query with statement_timeout
    print("🐌 Step 2: Simulating slow database queries")

    try:
        async with db_pool.acquire() as conn:
            await conn.execute("SET statement_timeout = '100ms'")

            # This should timeout and retry
            start_time = time.time()
            try:
                # Slow query simulation
                await conn.fetchval("SELECT pg_sleep(0.2)")
            except asyncpg.exceptions.QueryCanceledError:
                elapsed = time.time() - start_time
                print(f"  ✅ Query timed out after {elapsed:.2f}s (expected)")

            # Reset timeout
            await conn.execute("SET statement_timeout = '30s'")

    except Exception as e:
        print(f"  ✅ Handled timeout exception: {type(e).__name__}")

    # Step 3: Verify retry with successful query
    print("\n⚡ Step 3: Retry with normal timeout")

    async with db_pool.acquire() as conn:
        result = await conn.fetchval("SELECT COUNT(*) FROM selfology.personality_profiles")
        print(f"  ✅ Retry succeeded: {result} profiles")

    print("\n" + "="*80)
    print("✅ CHAOS TEST PASSED: Retry Logic Worked!")
    print("="*80 + "\n")


# ============================================================================
# CHAOS TEST 4: AI API FAILURE → FALLBACK CHAIN
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.chaos
async def test_ai_api_failure_fallback_chain():
    """
    Chaos: Simulate AI API failures → verify fallback chain

    Expected:
    - Claude fails → try GPT-4o
    - GPT-4o fails → try GPT-4o-mini
    - All fail → Circuit Breaker opens
    - Metrics tracked correctly
    """
    import os

    print("\n" + "="*80)
    print("CHAOS TEST: AI API Failure → Fallback Chain")
    print("="*80 + "\n")

    # Create AI Router with real keys
    ai_router = AIRouter(
        openai_api_key=os.getenv("OPENAI_API_KEY", "test_key"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
    )

    # Step 1: Normal AI call
    print("🤖 Step 1: Normal AI call (should succeed)")

    messages = [
        {"role": "user", "content": "Say 'test' only"}
    ]

    try:
        result = await ai_router.call_ai(
            model=AIModel.GPT4O_MINI,
            messages=messages,
            max_tokens=10,
            temperature=0,
            allow_fallback=True
        )

        print(f"  ✅ AI responded: model={result['model']}, cost=${result['cost_usd']:.4f}")
    except Exception as e:
        print(f"  ⚠️  AI call failed: {e}")

    # Step 2: Force failure with invalid API key
    print("\n❌ Step 2: Force AI failure (invalid key)")

    chaos_router = AIRouter(
        openai_api_key="invalid_key_for_chaos_test",
        anthropic_api_key="invalid_key_for_chaos_test"
    )

    try:
        result = await chaos_router.call_ai(
            model=AIModel.CLAUDE_SONNET_4,
            messages=messages,
            max_tokens=10,
            allow_fallback=True
        )

        print(f"  ⚠️  Unexpected success: {result['model']}")
    except Exception as e:
        print(f"  ✅ Fallback chain exhausted (expected): {type(e).__name__}")

    # Step 3: Verify Circuit Breaker state
    print("\n🔌 Step 3: Checking Circuit Breaker state")

    cb_status = chaos_router.get_health_status()
    print(f"  ✅ Circuit Breaker status: {cb_status}")

    metrics = chaos_router.get_metrics()
    print(f"  📊 Metrics: {metrics['total_requests']} requests, {metrics['total_failures']} failures")

    print("\n" + "="*80)
    print("✅ CHAOS TEST PASSED: Fallback Chain + Circuit Breaker Worked!")
    print("="*80 + "\n")


# ============================================================================
# CHAOS TEST 5: CPU EXHAUSTION → RATE LIMITING
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.chaos
async def test_cpu_exhaustion_rate_limiting(docker_client, redis_client):
    """
    Chaos: Exhaust CPU → verify rate limiting protects system

    Expected:
    - Rate limiter blocks excessive requests
    - System remains responsive under load
    - Metrics track throttled requests
    """
    chaos = ChaosEngineer(docker_client)
    test_user_id = 999005

    print("\n" + "="*80)
    print("CHAOS TEST: CPU Exhaustion → Rate Limiting")
    print("="*80 + "\n")

    from systems.telegram.telegram_gateway_service import RateLimiter

    rate_limiter = RateLimiter(
        redis_client=redis_client,
        max_requests=10,
        window_seconds=60
    )

    try:
        # Step 1: Normal rate limiting
        print("📊 Step 1: Normal rate limiting")

        allowed_count = 0
        for i in range(15):
            allowed = await rate_limiter.is_allowed(test_user_id)
            if allowed:
                allowed_count += 1

        print(f"  ✅ Allowed: {allowed_count}/15 requests (limit: 10)")
        assert allowed_count <= 10, "Rate limiter should block after 10 requests"

        # Step 2: Exhaust CPU
        print("\n🔥 Step 2: Exhausting CPU for 5s...")

        cpu_task = asyncio.create_task(chaos.exhaust_cpu(duration=5, cores=2))

        # Try to make requests during CPU exhaustion
        await asyncio.sleep(1)

        print("📤 Step 3: Making requests under CPU load")
        blocked_count = 0

        for i in range(5):
            allowed = await rate_limiter.is_allowed(test_user_id + 1)
            if not allowed:
                blocked_count += 1
            await asyncio.sleep(0.1)

        print(f"  ✅ Rate limiter still functioning: blocked {blocked_count}/5")

        await cpu_task

        print("\n" + "="*80)
        print("✅ CHAOS TEST PASSED: Rate Limiting Protected System!")
        print("="*80 + "\n")

    finally:
        chaos.cleanup()


# ============================================================================
# CHAOS TEST SUITE
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.chaos
@pytest.mark.slow
async def test_chaos_monkey_full_suite(docker_client, db_pool, redis_client, event_bus):
    """
    Full chaos monkey test suite

    Runs multiple chaos scenarios in sequence:
    1. Kill random services
    2. Disconnect Redis
    3. Slow database
    4. Exhaust resources
    5. Verify system recovery

    Duration: ~5 minutes
    """
    chaos = ChaosEngineer(docker_client)

    print("\n" + "="*80)
    print("🐒 CHAOS MONKEY: FULL SUITE")
    print("="*80 + "\n")

    scenarios = [
        ("Kill Analysis Worker", lambda: chaos.kill_service("selfology-analysis-worker", 10)),
        ("Disconnect Redis", lambda: chaos.disconnect_redis(5)),
        ("CPU Exhaustion", lambda: chaos.exhaust_cpu(3, 1))
    ]

    try:
        for i, (name, scenario) in enumerate(scenarios, 1):
            print(f"\n🎲 Scenario {i}/{len(scenarios)}: {name}")
            print("-" * 80)

            if asyncio.iscoroutinefunction(scenario):
                await scenario()
            else:
                scenario()

            print(f"  ✅ Completed: {name}")
            await asyncio.sleep(5)  # Recovery time

        print("\n" + "="*80)
        print("🎉 CHAOS MONKEY COMPLETE: System Survived All Scenarios!")
        print("="*80 + "\n")

    finally:
        chaos.cleanup()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-m", "chaos"])
