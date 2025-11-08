"""
Performance Profiling Tests for Selfology Microservices

Profiles critical paths to identify bottlenecks:
- Instant analysis latency (<500ms target)
- Deep analysis throughput
- Database query performance
- Redis operations latency
- AI API call timing
- Event processing speed

Tools:
- cProfile for Python profiling
- memory_profiler for memory usage
- asyncio debugging for async bottlenecks
- Custom timing decorators

Run:
    pytest tests/performance/ -v -s --profile
    python tests/performance/profiling_tests.py --target instant_analysis
    python tests/performance/profiling_tests.py --target deep_analysis
    python tests/performance/profiling_tests.py --target event_processing

Output:
    - Performance reports in tests/performance/reports/
    - Flame graphs for visualization
    - Bottleneck identification
"""

import pytest
import asyncio
import asyncpg
import redis.asyncio as redis
import time
import cProfile
import pstats
import io
import json
import tracemalloc
from typing import Dict, Any, List, Callable
from datetime import datetime
from contextlib import asynccontextmanager
from functools import wraps

from core.event_bus import EventBus
from core.outbox_pattern import OutboxPublisher
from systems.analysis.analysis_worker_service import AnalysisWorkerService
from systems.analysis.ai_router import AIRouter, AIModel


# ============================================================================
# PERFORMANCE PROFILING UTILITIES
# ============================================================================

class PerformanceProfiler:
    """
    Performance profiling utilities

    Features:
    - CPU profiling with cProfile
    - Memory profiling with tracemalloc
    - Custom timing decorators
    - Report generation
    """

    def __init__(self, report_dir: str = "tests/performance/reports"):
        self.report_dir = report_dir
        self.metrics = []

    @asynccontextmanager
    async def profile_cpu(self, name: str):
        """CPU profiling context manager"""
        profiler = cProfile.Profile()
        profiler.enable()

        try:
            yield profiler
        finally:
            profiler.disable()

            # Generate report
            s = io.StringIO()
            ps = pstats.Stats(profiler, stream=s)
            ps.strip_dirs()
            ps.sort_stats('cumulative')
            ps.print_stats(50)  # Top 50 functions

            report = {
                "name": name,
                "timestamp": datetime.now().isoformat(),
                "profile": s.getvalue()
            }

            self._save_report(f"{name}_cpu", report)
            print(f"\n📊 CPU Profile saved: {name}_cpu.json")

    @asynccontextmanager
    async def profile_memory(self, name: str):
        """Memory profiling context manager"""
        tracemalloc.start()

        try:
            yield
        finally:
            snapshot = tracemalloc.take_snapshot()
            tracemalloc.stop()

            # Top 10 memory consumers
            top_stats = snapshot.statistics('lineno')[:10]

            report = {
                "name": name,
                "timestamp": datetime.now().isoformat(),
                "top_memory_consumers": [
                    {
                        "file": str(stat.traceback),
                        "size_mb": stat.size / (1024 * 1024),
                        "count": stat.count
                    }
                    for stat in top_stats
                ]
            }

            self._save_report(f"{name}_memory", report)
            print(f"\n📊 Memory Profile saved: {name}_memory.json")

    async def time_async_function(
        self,
        func: Callable,
        name: str,
        iterations: int = 100
    ) -> Dict[str, Any]:
        """
        Times an async function over multiple iterations

        Args:
            func: Async function to profile
            name: Profile name
            iterations: Number of iterations

        Returns:
            Timing statistics
        """
        latencies = []

        for i in range(iterations):
            start = time.perf_counter()
            await func()
            elapsed = (time.perf_counter() - start) * 1000  # ms

            latencies.append(elapsed)

        # Calculate statistics
        latencies.sort()
        stats = {
            "name": name,
            "iterations": iterations,
            "min_ms": min(latencies),
            "max_ms": max(latencies),
            "mean_ms": sum(latencies) / len(latencies),
            "p50_ms": latencies[len(latencies) // 2],
            "p95_ms": latencies[int(len(latencies) * 0.95)],
            "p99_ms": latencies[int(len(latencies) * 0.99)],
            "timestamp": datetime.now().isoformat()
        }

        self.metrics.append(stats)
        self._save_report(f"{name}_timing", stats)

        return stats

    def _save_report(self, name: str, data: Dict[str, Any]):
        """Saves report to JSON file"""
        import os
        os.makedirs(self.report_dir, exist_ok=True)

        filepath = f"{self.report_dir}/{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    def print_summary(self):
        """Prints summary of all metrics"""
        print("\n" + "="*80)
        print("PERFORMANCE PROFILING SUMMARY")
        print("="*80 + "\n")

        for metric in self.metrics:
            print(f"📊 {metric['name']}")
            print(f"   Iterations: {metric['iterations']}")
            print(f"   Mean: {metric['mean_ms']:.2f}ms")
            print(f"   P95:  {metric['p95_ms']:.2f}ms")
            print(f"   P99:  {metric['p99_ms']:.2f}ms")
            print()

        print("="*80 + "\n")


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
        min_size=5,
        max_size=20
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
async def ai_router():
    """AI Router with test keys"""
    import os
    return AIRouter(
        openai_api_key=os.getenv("OPENAI_API_KEY", "test_key"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
    )


@pytest.fixture
def profiler():
    """Performance profiler instance"""
    return PerformanceProfiler()


# ============================================================================
# PROFILE TEST 1: INSTANT ANALYSIS LATENCY
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.performance
async def test_profile_instant_analysis(db_pool, event_bus, ai_router, profiler):
    """
    Profile instant analysis latency (<500ms target)

    Measures:
    - AI Router call time
    - Sentiment analysis
    - Quality scoring
    - Database save time
    """
    print("\n" + "="*80)
    print("PROFILE: Instant Analysis Latency")
    print("="*80 + "\n")

    analysis_service = AnalysisWorkerService(
        event_bus=event_bus,
        db_pool=db_pool,
        ai_router=ai_router
    )

    test_user_id = 888001
    test_question_id = "profile_q1"
    test_answer = "I feel deeply connected to my creative side and find meaning in helping others grow."

    # Define test function
    async def run_instant_analysis():
        result = await analysis_service.analysis_engine.analyze_instant(
            user_id=test_user_id,
            question_id=test_question_id,
            answer_text=test_answer,
            question_context={"domain": "IDENTITY", "depth_level": "CONSCIOUS"}
        )
        return result

    # Profile CPU
    print("🔬 Profiling CPU usage...")
    async with profiler.profile_cpu("instant_analysis"):
        await run_instant_analysis()

    # Profile memory
    print("🔬 Profiling memory usage...")
    async with profiler.profile_memory("instant_analysis"):
        await run_instant_analysis()

    # Time over iterations
    print("🔬 Timing over 100 iterations...")
    stats = await profiler.time_async_function(
        run_instant_analysis,
        "instant_analysis_timing",
        iterations=100
    )

    # Verify target met
    assert stats['p95_ms'] < 500, f"P95 latency {stats['p95_ms']:.2f}ms exceeds 500ms target"

    print(f"\n✅ Instant Analysis Performance:")
    print(f"   Mean: {stats['mean_ms']:.2f}ms")
    print(f"   P95:  {stats['p95_ms']:.2f}ms")
    print(f"   P99:  {stats['p99_ms']:.2f}ms")


# ============================================================================
# PROFILE TEST 2: DEEP ANALYSIS THROUGHPUT
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.performance
async def test_profile_deep_analysis_throughput(db_pool, event_bus, ai_router, profiler):
    """
    Profile deep analysis throughput

    Measures:
    - AI call latency (Claude/GPT-4)
    - Trait extraction
    - Database updates
    - Event publishing
    """
    print("\n" + "="*80)
    print("PROFILE: Deep Analysis Throughput")
    print("="*80 + "\n")

    analysis_service = AnalysisWorkerService(
        event_bus=event_bus,
        db_pool=db_pool,
        ai_router=ai_router
    )

    test_user_id = 888002
    test_question_id = "profile_q2"
    test_answer = "When facing difficult decisions, I tend to weigh all options carefully and seek input from trusted friends before committing."

    async def run_deep_analysis():
        result = await analysis_service.analysis_engine.analyze_deep(
            user_id=test_user_id,
            question_id=test_question_id,
            answer_text=test_answer,
            question_context={"domain": "DECISION_MAKING", "depth_level": "EDGE"}
        )
        return result

    # Profile CPU for deep analysis
    print("🔬 Profiling CPU usage (deep analysis)...")
    async with profiler.profile_cpu("deep_analysis"):
        await run_deep_analysis()

    # Time over iterations (fewer due to cost)
    print("🔬 Timing over 10 iterations...")
    stats = await profiler.time_async_function(
        run_deep_analysis,
        "deep_analysis_timing",
        iterations=10
    )

    print(f"\n✅ Deep Analysis Performance:")
    print(f"   Mean: {stats['mean_ms']:.2f}ms")
    print(f"   P95:  {stats['p95_ms']:.2f}ms")
    print(f"   P99:  {stats['p99_ms']:.2f}ms")


# ============================================================================
# PROFILE TEST 3: DATABASE QUERY PERFORMANCE
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.performance
async def test_profile_database_queries(db_pool, profiler):
    """
    Profile database query performance

    Measures:
    - Profile lookup time
    - Trait history queries
    - Batch inserts
    - Index effectiveness
    """
    print("\n" + "="*80)
    print("PROFILE: Database Query Performance")
    print("="*80 + "\n")

    # Test 1: Profile lookup
    async def profile_lookup():
        async with db_pool.acquire() as conn:
            await conn.fetchrow(
                "SELECT * FROM selfology.personality_profiles WHERE user_id = $1",
                888003
            )

    stats_lookup = await profiler.time_async_function(
        profile_lookup,
        "db_profile_lookup",
        iterations=1000
    )

    print(f"✅ Profile Lookup: P95 = {stats_lookup['p95_ms']:.2f}ms")

    # Test 2: Trait history query
    async def trait_history_query():
        async with db_pool.acquire() as conn:
            await conn.fetch(
                """
                SELECT * FROM selfology.trait_history
                WHERE user_id = $1
                ORDER BY timestamp DESC
                LIMIT 20
                """,
                888003
            )

    stats_history = await profiler.time_async_function(
        trait_history_query,
        "db_trait_history",
        iterations=1000
    )

    print(f"✅ Trait History: P95 = {stats_history['p95_ms']:.2f}ms")

    # Test 3: Batch insert (outbox)
    async def batch_insert():
        async with db_pool.acquire() as conn:
            async with conn.transaction():
                await conn.executemany(
                    """
                    INSERT INTO selfology.event_outbox (event_type, payload, status)
                    VALUES ($1, $2, $3)
                    """,
                    [
                        ("test.event", {"data": f"test_{i}"}, "pending")
                        for i in range(10)
                    ]
                )

    stats_insert = await profiler.time_async_function(
        batch_insert,
        "db_batch_insert",
        iterations=100
    )

    print(f"✅ Batch Insert (10 rows): P95 = {stats_insert['p95_ms']:.2f}ms")


# ============================================================================
# PROFILE TEST 4: REDIS OPERATIONS LATENCY
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.performance
async def test_profile_redis_operations(redis_client, profiler):
    """
    Profile Redis operations latency

    Measures:
    - GET/SET operations
    - Stream publish
    - Sorted set operations (rate limiter)
    - Cache hit/miss
    """
    print("\n" + "="*80)
    print("PROFILE: Redis Operations Latency")
    print("="*80 + "\n")

    # Test 1: GET/SET
    async def redis_get_set():
        await redis_client.set("test_key", "test_value")
        await redis_client.get("test_key")

    stats_get_set = await profiler.time_async_function(
        redis_get_set,
        "redis_get_set",
        iterations=1000
    )

    print(f"✅ GET/SET: P95 = {stats_get_set['p95_ms']:.2f}ms")

    # Test 2: Stream publish
    async def redis_stream_publish():
        await redis_client.xadd(
            "test_stream",
            {"event": "test", "timestamp": str(time.time())}
        )

    stats_stream = await profiler.time_async_function(
        redis_stream_publish,
        "redis_stream_publish",
        iterations=1000
    )

    print(f"✅ Stream Publish: P95 = {stats_stream['p95_ms']:.2f}ms")

    # Test 3: Sorted set (rate limiter)
    async def redis_sorted_set():
        now = time.time()
        await redis_client.zadd("rate_limit:test", {str(now): now})
        await redis_client.zcard("rate_limit:test")

    stats_sorted = await profiler.time_async_function(
        redis_sorted_set,
        "redis_sorted_set",
        iterations=1000
    )

    print(f"✅ Sorted Set: P95 = {stats_sorted['p95_ms']:.2f}ms")


# ============================================================================
# PROFILE TEST 5: EVENT PROCESSING SPEED
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.performance
async def test_profile_event_processing(db_pool, event_bus, profiler):
    """
    Profile event processing speed

    Measures:
    - Event publish latency
    - Outbox relay processing
    - Event consumption latency
    - End-to-end event flow
    """
    print("\n" + "="*80)
    print("PROFILE: Event Processing Speed")
    print("="*80 + "\n")

    # Test 1: Event publish to outbox
    async def publish_event():
        async with db_pool.acquire() as conn:
            async with conn.transaction():
                outbox_publisher = OutboxPublisher(schema="selfology")
                await outbox_publisher.publish(
                    conn,
                    "test.event",
                    {"data": "performance_test"}
                )

    stats_publish = await profiler.time_async_function(
        publish_event,
        "event_publish",
        iterations=100
    )

    print(f"✅ Event Publish: P95 = {stats_publish['p95_ms']:.2f}ms")

    # Test 2: Event consumption from stream
    consumed_events = []

    async def consume_event():
        # Simulate event consumption
        messages = await event_bus.redis_client.xread(
            {"selfology:events": '$'},
            count=1,
            block=100
        )
        if messages:
            consumed_events.append(messages[0])

    stats_consume = await profiler.time_async_function(
        consume_event,
        "event_consume",
        iterations=50
    )

    print(f"✅ Event Consume: P95 = {stats_consume['p95_ms']:.2f}ms")


# ============================================================================
# PROFILE TEST 6: AI API CALL TIMING
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.performance
async def test_profile_ai_api_calls(ai_router, profiler):
    """
    Profile AI API call timing

    Measures:
    - GPT-4o-mini latency
    - GPT-4o latency
    - Claude Sonnet latency
    - Fallback mechanism timing
    """
    print("\n" + "="*80)
    print("PROFILE: AI API Call Timing")
    print("="*80 + "\n")

    messages = [
        {"role": "user", "content": "Respond with 'OK' only"}
    ]

    # Test 1: GPT-4o-mini (fastest)
    async def call_mini():
        await ai_router.call_ai(
            model=AIModel.GPT4O_MINI,
            messages=messages,
            max_tokens=5,
            temperature=0,
            allow_fallback=False
        )

    stats_mini = await profiler.time_async_function(
        call_mini,
        "ai_gpt4o_mini",
        iterations=10
    )

    print(f"✅ GPT-4o-mini: P95 = {stats_mini['p95_ms']:.2f}ms")

    # Test 2: GPT-4o (standard)
    async def call_gpt4o():
        await ai_router.call_ai(
            model=AIModel.GPT4O,
            messages=messages,
            max_tokens=5,
            temperature=0,
            allow_fallback=False
        )

    stats_gpt4o = await profiler.time_async_function(
        call_gpt4o,
        "ai_gpt4o",
        iterations=10
    )

    print(f"✅ GPT-4o: P95 = {stats_gpt4o['p95_ms']:.2f}ms")


# ============================================================================
# PERFORMANCE SUMMARY
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.performance
async def test_performance_summary_report(
    db_pool,
    redis_client,
    event_bus,
    ai_router,
    profiler
):
    """
    Generate comprehensive performance summary report

    Runs all profiling tests and generates report
    """
    print("\n" + "="*80)
    print("COMPREHENSIVE PERFORMANCE REPORT")
    print("="*80 + "\n")

    # Run all tests
    await test_profile_instant_analysis(db_pool, event_bus, ai_router, profiler)
    await test_profile_database_queries(db_pool, profiler)
    await test_profile_redis_operations(redis_client, profiler)
    await test_profile_event_processing(db_pool, event_bus, profiler)
    await test_profile_ai_api_calls(ai_router, profiler)

    # Print summary
    profiler.print_summary()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-m", "performance"])
