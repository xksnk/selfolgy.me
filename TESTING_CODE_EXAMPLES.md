# ПРИМЕРЫ PYTEST КОДА ДЛЯ SELFOLOGY TESTING

> Конкретные примеры тестов для каждой критичной части системы

---

## СОДЕРЖАНИЕ

1. [Event Bus Tests](#event-bus-tests)
2. [Onboarding System Tests](#onboarding-system-tests)
3. [Analysis System Tests](#analysis-system-tests)
4. [Profile System Tests](#profile-system-tests)
5. [Contract Tests](#contract-tests)
6. [Load Tests](#load-tests)
7. [Chaos Tests](#chaos-tests)
8. [E2E Tests](#e2e-tests)
9. [Test Fixtures](#test-fixtures)
10. [Conftest Setup](#conftest-setup)

---

## EVENT BUS TESTS

### 1. Unit Tests - Event Publisher

```python
# tests/event_bus/unit/test_event_publisher.py

import pytest
import asyncio
from datetime import datetime
from core.event_bus import EventBus, Event
from core.domain_events import QuestionAnsweredEvent


class TestEventPublisher:
    """Unit tests for Event Bus publishing"""

    @pytest.fixture
    def event_bus(self, mock_redis):
        """Create EventBus with mocked Redis"""
        return EventBus(redis_client=mock_redis)

    @pytest.mark.asyncio
    async def test_publish_simple_event(self, event_bus):
        """Test publishing a simple event"""
        event = Event(
            event_type="test.event",
            payload={"message": "hello"},
            timestamp=datetime.utcnow()
        )

        result = await event_bus.publish(event)

        assert result is True
        assert event_bus.redis_client.xadd.called

    @pytest.mark.asyncio
    async def test_publish_question_answered_event(self, event_bus):
        """Test publishing QuestionAnsweredEvent with full payload"""
        event = QuestionAnsweredEvent(
            user_id=123456,
            session_id="sess_abc123",
            question_id="q_001",
            answer_text="I feel calm and peaceful",
            question_metadata={
                "domain": "EMOTIONS",
                "depth_level": "CONSCIOUS",
                "energy": "OPENING"
            }
        )

        result = await event_bus.publish(event)

        assert result is True
        # Проверяем, что payload сериализовался корректно
        call_args = event_bus.redis_client.xadd.call_args
        assert call_args[0][0] == "events:question.answered"

    @pytest.mark.asyncio
    async def test_publish_with_serialization_error(self, event_bus):
        """Test error handling when payload cannot be serialized"""
        # Создаем событие с не-сериализуемым объектом
        class BadObject:
            pass

        event = Event(
            event_type="test.event",
            payload={"bad": BadObject()},
            timestamp=datetime.utcnow()
        )

        with pytest.raises(ValueError, match="Cannot serialize"):
            await event_bus.publish(event)

    @pytest.mark.asyncio
    async def test_publish_retries_on_redis_error(self, event_bus, mock_redis):
        """Test that publish retries on Redis connection errors"""
        # Simulate Redis error on first call, success on second
        mock_redis.xadd.side_effect = [
            ConnectionError("Redis unavailable"),
            "1234567890-0"  # Redis stream message ID
        ]

        event = Event(event_type="test", payload={})
        result = await event_bus.publish(event, retry_count=3)

        assert result is True
        assert mock_redis.xadd.call_count == 2

    def test_event_serialization(self):
        """Test Event model serialization to JSON"""
        event = QuestionAnsweredEvent(
            user_id=123456,
            session_id="sess_abc",
            question_id="q_001",
            answer_text="My answer"
        )

        json_data = event.model_dump_json()
        restored = QuestionAnsweredEvent.model_validate_json(json_data)

        assert restored.user_id == event.user_id
        assert restored.answer_text == event.answer_text
```

### 2. Unit Tests - Event Subscriber

```python
# tests/event_bus/unit/test_event_subscriber.py

import pytest
import asyncio
from core.event_bus import EventBus, Event
from core.domain_events import QuestionAnsweredEvent


class TestEventSubscriber:
    """Unit tests for Event Bus subscription"""

    @pytest.fixture
    def event_bus(self, mock_redis):
        return EventBus(redis_client=mock_redis)

    @pytest.mark.asyncio
    async def test_subscribe_receives_events(self, event_bus, mock_redis):
        """Test that subscriber receives published events"""
        received_events = []

        async def handler(event: Event):
            received_events.append(event)

        # Mock Redis stream reading
        mock_redis.xreadgroup.return_value = [
            [
                "events:test",
                [
                    (
                        "1234567890-0",
                        {
                            "event_type": "test.event",
                            "payload": '{"message": "hello"}'
                        }
                    )
                ]
            ]
        ]

        # Subscribe and process one batch
        await event_bus.subscribe("test.event", handler, process_once=True)

        assert len(received_events) == 1
        assert received_events[0].event_type == "test.event"

    @pytest.mark.asyncio
    async def test_subscribe_with_consumer_group(self, event_bus, mock_redis):
        """Test consumer group creation and usage"""
        async def handler(event: Event):
            pass

        await event_bus.subscribe(
            "test.event",
            handler,
            consumer_group="analysis_workers",
            consumer_name="worker_1",
            process_once=True
        )

        # Verify consumer group was created
        mock_redis.xgroup_create.assert_called_with(
            "events:test",
            "analysis_workers",
            id="0",
            mkstream=True
        )

    @pytest.mark.asyncio
    async def test_subscribe_acknowledges_messages(self, event_bus, mock_redis):
        """Test that processed messages are acknowledged"""
        async def handler(event: Event):
            pass

        message_id = "1234567890-0"
        mock_redis.xreadgroup.return_value = [
            [
                "events:test",
                [(message_id, {"event_type": "test", "payload": "{}"})]
            ]
        ]

        await event_bus.subscribe(
            "test.event",
            handler,
            consumer_group="workers",
            consumer_name="w1",
            process_once=True
        )

        # Verify ACK was sent
        mock_redis.xack.assert_called_with(
            "events:test",
            "workers",
            message_id
        )

    @pytest.mark.asyncio
    async def test_subscribe_handles_deserialization_errors(self, event_bus, mock_redis):
        """Test error handling for malformed event data"""
        error_logged = False

        async def handler(event: Event):
            pass

        # Mock corrupted data
        mock_redis.xreadgroup.return_value = [
            [
                "events:test",
                [("123-0", {"event_type": "test", "payload": "invalid json"})]
            ]
        ]

        # Should not raise, but log error
        await event_bus.subscribe("test", handler, process_once=True)

        # Verify message was still acknowledged (to prevent reprocessing)
        mock_redis.xack.assert_called()
```

### 3. Integration Tests - Redis Streams

```python
# tests/event_bus/integration/test_redis_streams.py

import pytest
import asyncio
from redis.asyncio import Redis
from core.event_bus import EventBus
from core.domain_events import QuestionAnsweredEvent


@pytest.mark.integration
class TestRedisStreamsIntegration:
    """Integration tests with real Redis"""

    @pytest.fixture
    async def redis_client(self):
        """Create real Redis connection for testing"""
        client = Redis.from_url(
            "redis://localhost:6379",
            decode_responses=True
        )
        yield client
        # Cleanup
        await client.flushdb()
        await client.close()

    @pytest.fixture
    def event_bus(self, redis_client):
        return EventBus(redis_client=redis_client)

    @pytest.mark.asyncio
    async def test_publish_and_subscribe_end_to_end(self, event_bus):
        """Test full publish-subscribe cycle with real Redis"""
        received_events = []

        async def handler(event: QuestionAnsweredEvent):
            received_events.append(event)

        # Start subscriber in background
        subscriber_task = asyncio.create_task(
            event_bus.subscribe(
                "question.answered",
                handler,
                consumer_group="test_workers",
                consumer_name="test_1"
            )
        )

        # Give subscriber time to start
        await asyncio.sleep(0.1)

        # Publish event
        event = QuestionAnsweredEvent(
            user_id=123456,
            session_id="sess_test",
            question_id="q_001",
            answer_text="Test answer"
        )
        await event_bus.publish(event)

        # Wait for processing
        await asyncio.sleep(0.5)

        # Cleanup
        subscriber_task.cancel()

        # Verify event was received
        assert len(received_events) == 1
        assert received_events[0].user_id == 123456
        assert received_events[0].answer_text == "Test answer"

    @pytest.mark.asyncio
    async def test_multiple_consumers_in_group(self, event_bus):
        """Test that events are distributed across consumer group members"""
        consumer1_events = []
        consumer2_events = []

        async def handler1(event):
            consumer1_events.append(event)

        async def handler2(event):
            consumer2_events.append(event)

        # Start two consumers in same group
        task1 = asyncio.create_task(
            event_bus.subscribe(
                "test.event",
                handler1,
                consumer_group="workers",
                consumer_name="worker_1"
            )
        )
        task2 = asyncio.create_task(
            event_bus.subscribe(
                "test.event",
                handler2,
                consumer_group="workers",
                consumer_name="worker_2"
            )
        )

        await asyncio.sleep(0.1)

        # Publish multiple events
        for i in range(10):
            event = Event(event_type="test.event", payload={"index": i})
            await event_bus.publish(event)

        await asyncio.sleep(1)

        # Cleanup
        task1.cancel()
        task2.cancel()

        # Verify events were distributed (not duplicated)
        total_received = len(consumer1_events) + len(consumer2_events)
        assert total_received == 10
        # Both consumers should have received some events
        assert len(consumer1_events) > 0
        assert len(consumer2_events) > 0

    @pytest.mark.asyncio
    async def test_pending_messages_recovery(self, event_bus, redis_client):
        """Test recovery of pending (unacknowledged) messages"""
        # Simulate a consumer that crashes before acknowledging
        async def failing_handler(event):
            raise Exception("Consumer crashed!")

        await event_bus.subscribe(
            "test.event",
            failing_handler,
            consumer_group="workers",
            consumer_name="worker_1",
            process_once=True
        )

        # Event should be in pending list
        pending = await redis_client.xpending(
            "events:test",
            "workers"
        )

        assert pending["pending"] > 0

        # New consumer should be able to claim pending messages
        claimed_events = []

        async def recovery_handler(event):
            claimed_events.append(event)

        await event_bus.claim_pending_messages(
            "test.event",
            "workers",
            "worker_2",
            recovery_handler,
            min_idle_time=0
        )

        assert len(claimed_events) > 0
```

### 4. Contract Tests - Event Schemas

```python
# tests/event_bus/contract/test_event_schemas.py

import pytest
from pydantic import ValidationError
from core.domain_events import (
    QuestionAnsweredEvent,
    AnalysisCompletedEvent,
    ProfileUpdatedEvent,
    FatigueDetectedEvent
)


class TestEventSchemas:
    """Contract tests for event payload schemas"""

    def test_question_answered_event_schema(self):
        """Test QuestionAnsweredEvent schema validation"""
        # Valid event
        event = QuestionAnsweredEvent(
            user_id=123456,
            session_id="sess_abc",
            question_id="q_001",
            answer_text="My answer",
            question_metadata={
                "domain": "EMOTIONS",
                "depth_level": "CONSCIOUS"
            }
        )

        assert event.user_id == 123456
        assert event.question_metadata["domain"] == "EMOTIONS"

    def test_question_answered_event_required_fields(self):
        """Test that required fields are enforced"""
        with pytest.raises(ValidationError) as exc_info:
            QuestionAnsweredEvent(
                user_id=123456,
                session_id="sess_abc",
                # Missing question_id and answer_text
            )

        assert "question_id" in str(exc_info.value)
        assert "answer_text" in str(exc_info.value)

    def test_analysis_completed_event_schema(self):
        """Test AnalysisCompletedEvent with extracted traits"""
        event = AnalysisCompletedEvent(
            user_id=123456,
            analysis_id="analysis_001",
            question_id="q_001",
            extracted_traits={
                "openness": 0.75,
                "conscientiousness": 0.65,
                "extraversion": 0.45,
                "agreeableness": 0.85,
                "neuroticism": 0.35
            },
            confidence=0.82,
            analysis_model="gpt-4o"
        )

        assert event.extracted_traits["openness"] == 0.75
        assert event.confidence == 0.82

    def test_profile_updated_event_schema(self):
        """Test ProfileUpdatedEvent"""
        event = ProfileUpdatedEvent(
            user_id=123456,
            profile_version=5,
            updated_traits=["openness", "conscientiousness"],
            completeness=0.45,
            total_samples=23
        )

        assert event.profile_version == 5
        assert len(event.updated_traits) == 2

    def test_fatigue_detected_event_schema(self):
        """Test FatigueDetectedEvent"""
        event = FatigueDetectedEvent(
            user_id=123456,
            session_id="sess_abc",
            questions_answered=15,
            fatigue_score=0.72,
            suggested_action="PAUSE",
            pause_duration_minutes=30
        )

        assert event.fatigue_score == 0.72
        assert event.suggested_action == "PAUSE"

    def test_event_backward_compatibility(self):
        """Test that events with extra fields don't break"""
        # Simulate receiving event with new fields added in v2
        event_data = {
            "user_id": 123456,
            "session_id": "sess_abc",
            "question_id": "q_001",
            "answer_text": "My answer",
            "question_metadata": {},
            # New fields added in hypothetical v2
            "sentiment_score": 0.8,
            "language_detected": "ru"
        }

        # Should not raise error (extra fields ignored)
        event = QuestionAnsweredEvent(**event_data)
        assert event.user_id == 123456

    def test_event_serialization_roundtrip(self):
        """Test that events survive JSON serialization"""
        original = QuestionAnsweredEvent(
            user_id=123456,
            session_id="sess_abc",
            question_id="q_001",
            answer_text="My answer"
        )

        # Serialize to JSON
        json_str = original.model_dump_json()

        # Deserialize back
        restored = QuestionAnsweredEvent.model_validate_json(json_str)

        assert restored.user_id == original.user_id
        assert restored.answer_text == original.answer_text
```

---

## ONBOARDING SYSTEM TESTS

### 5. Unit Tests - QuestionRouter (Smart Mix)

```python
# tests/systems/onboarding/unit/test_question_router.py

import pytest
from systems.onboarding.question_router import QuestionRouter, RoutingStrategy
from tests.fixtures.factories import QuestionFactory, SessionFactory


class TestQuestionRouter:
    """Unit tests for Smart Mix question routing algorithm"""

    @pytest.fixture
    def router(self):
        return QuestionRouter()

    @pytest.fixture
    def sample_questions(self):
        """Create sample questions with different attributes"""
        return [
            QuestionFactory(
                domain="IDENTITY",
                depth_level="SURFACE",
                energy="OPENING"
            ),
            QuestionFactory(
                domain="EMOTIONS",
                depth_level="CONSCIOUS",
                energy="NEUTRAL"
            ),
            QuestionFactory(
                domain="RELATIONSHIPS",
                depth_level="EDGE",
                energy="PROCESSING"
            ),
            QuestionFactory(
                domain="PAST",
                depth_level="SHADOW",
                energy="HEAVY"
            ),
        ]

    def test_entry_strategy_selects_surface_questions(self, router, sample_questions):
        """Test ENTRY strategy selects SURFACE/OPENING questions"""
        session = SessionFactory(questions_answered=0)

        question = router.select_next_question(
            session=session,
            available_questions=sample_questions,
            strategy=RoutingStrategy.ENTRY
        )

        assert question.depth_level == "SURFACE"
        assert question.energy == "OPENING"

    def test_exploration_strategy_broadens_domains(self, router, sample_questions):
        """Test EXPLORATION strategy covers multiple domains"""
        session = SessionFactory(
            questions_answered=5,
            answered_domains={"IDENTITY": 3, "EMOTIONS": 2}
        )

        # Should prefer unexplored domains
        question = router.select_next_question(
            session=session,
            available_questions=sample_questions,
            strategy=RoutingStrategy.EXPLORATION
        )

        assert question.domain not in ["IDENTITY", "EMOTIONS"]

    def test_deepening_strategy_increases_depth(self, router, sample_questions):
        """Test DEEPENING strategy goes deeper in comfortable domains"""
        session = SessionFactory(
            questions_answered=15,
            answered_domains={"IDENTITY": 8, "EMOTIONS": 5, "RELATIONSHIPS": 2},
            comfortable_domains=["IDENTITY", "EMOTIONS"]
        )

        question = router.select_next_question(
            session=session,
            available_questions=sample_questions,
            strategy=RoutingStrategy.DEEPENING
        )

        # Should go deeper in comfortable domain
        assert question.domain in ["IDENTITY", "EMOTIONS"]
        assert question.depth_level in ["CONSCIOUS", "EDGE"]

    def test_balancing_strategy_avoids_heavy_after_heavy(self, router, sample_questions):
        """Test BALANCING never asks HEAVY→HEAVY questions"""
        session = SessionFactory(
            questions_answered=20,
            last_question_energy="HEAVY"
        )

        question = router.select_next_question(
            session=session,
            available_questions=sample_questions,
            strategy=RoutingStrategy.BALANCING
        )

        # Should select HEALING or OPENING energy
        assert question.energy in ["HEALING", "OPENING", "NEUTRAL"]
        assert question.energy != "HEAVY"

    def test_router_respects_energy_safety(self, router, sample_questions):
        """Test that router never violates energy safety rules"""
        # Add HEAVY questions to available pool
        heavy_questions = [
            QuestionFactory(energy="HEAVY") for _ in range(5)
        ]

        session = SessionFactory(last_question_energy="HEAVY")

        # Try to get next question 10 times
        for _ in range(10):
            question = router.select_next_question(
                session=session,
                available_questions=sample_questions + heavy_questions,
                strategy=RoutingStrategy.BALANCING
            )

            # Should NEVER be HEAVY
            assert question.energy != "HEAVY"

    def test_router_strategy_progression(self, router):
        """Test that routing strategy evolves naturally through session"""
        strategies = []

        for answered in [0, 5, 15, 30, 60, 90]:
            session = SessionFactory(questions_answered=answered)
            strategy = router.determine_strategy(session)
            strategies.append(strategy)

        # Should progress: ENTRY → EXPLORATION → DEEPENING → BALANCING
        assert strategies[0] == RoutingStrategy.ENTRY
        assert strategies[1] == RoutingStrategy.EXPLORATION
        assert strategies[3] == RoutingStrategy.DEEPENING
        assert strategies[5] == RoutingStrategy.BALANCING
```

### 6. Unit Tests - FatigueDetector

```python
# tests/systems/onboarding/unit/test_fatigue_detector.py

import pytest
from datetime import datetime, timedelta
from systems.onboarding.fatigue_detector import FatigueDetector
from tests.fixtures.factories import SessionFactory


class TestFatigueDetector:
    """Unit tests for user fatigue detection"""

    @pytest.fixture
    def detector(self):
        return FatigueDetector()

    def test_no_fatigue_at_start(self, detector):
        """Test that fresh session shows no fatigue"""
        session = SessionFactory(
            questions_answered=3,
            session_duration_minutes=5,
            recent_response_times=[30, 25, 28]  # seconds
        )

        fatigue = detector.calculate_fatigue(session)

        assert fatigue.score < 0.3
        assert fatigue.level == "LOW"
        assert fatigue.should_pause is False

    def test_fatigue_from_long_session(self, detector):
        """Test fatigue detection from session duration"""
        session = SessionFactory(
            questions_answered=45,
            session_duration_minutes=75,  # 1h 15min - pretty long
            recent_response_times=[40, 45, 50, 60, 70]  # slowing down
        )

        fatigue = detector.calculate_fatigue(session)

        assert fatigue.score > 0.7
        assert fatigue.level == "HIGH"
        assert fatigue.should_pause is True

    def test_fatigue_from_slowing_responses(self, detector):
        """Test fatigue detection from increasing response times"""
        session = SessionFactory(
            questions_answered=20,
            session_duration_minutes=30,
            recent_response_times=[
                25, 28, 30, 35, 40, 50, 60, 75, 90, 120
            ]  # Clear upward trend
        )

        fatigue = detector.calculate_fatigue(session)

        assert fatigue.score > 0.6
        assert fatigue.indicators["response_time_trend"] > 0.5

    def test_fatigue_from_decreasing_quality(self, detector):
        """Test fatigue detection from shorter answers"""
        session = SessionFactory(
            questions_answered=30,
            recent_answer_lengths=[
                150, 140, 120, 100, 80, 60, 40, 25, 15, 10
            ]  # Getting shorter and shorter
        )

        fatigue = detector.calculate_fatigue(session)

        assert fatigue.score > 0.5
        assert fatigue.indicators["answer_quality_drop"] > 0.5

    def test_fatigue_from_heavy_questions(self, detector):
        """Test fatigue from answering too many HEAVY questions"""
        session = SessionFactory(
            questions_answered=25,
            recent_question_energies=[
                "HEAVY", "PROCESSING", "HEAVY", "HEAVY", "PROCESSING"
            ]
        )

        fatigue = detector.calculate_fatigue(session)

        assert fatigue.score > 0.6
        assert fatigue.indicators["emotional_load"] > 0.7

    def test_suggested_pause_duration(self, detector):
        """Test that pause duration suggestions are reasonable"""
        # Low fatigue = short pause
        low_fatigue_session = SessionFactory(
            questions_answered=10,
            session_duration_minutes=15
        )
        low_fatigue = detector.calculate_fatigue(low_fatigue_session)

        if low_fatigue.should_pause:
            assert low_fatigue.suggested_pause_minutes <= 15

        # High fatigue = longer pause
        high_fatigue_session = SessionFactory(
            questions_answered=60,
            session_duration_minutes=90
        )
        high_fatigue = detector.calculate_fatigue(high_fatigue_session)

        assert high_fatigue.should_pause is True
        assert high_fatigue.suggested_pause_minutes >= 30

    def test_fatigue_message_templates(self, detector):
        """Test that appropriate care messages are selected"""
        session = SessionFactory(questions_answered=45)
        fatigue = detector.calculate_fatigue(session)

        if fatigue.should_pause:
            message = detector.get_care_message(fatigue)

            assert len(message) > 0
            # Should be caring and empathetic
            assert any(word in message.lower() for word in [
                "отдохни", "пауза", "устал", "забота", "вернись"
            ])
```

### 7. Integration Tests - Onboarding Events

```python
# tests/systems/onboarding/integration/test_onboarding_events.py

import pytest
import asyncio
from systems.onboarding.onboarding_system import OnboardingSystem
from core.event_bus import EventBus
from tests.fixtures.factories import UserFactory, QuestionFactory


@pytest.mark.integration
class TestOnboardingEventPublishing:
    """Integration tests for Onboarding event publishing"""

    @pytest.fixture
    async def system(self, redis_client, db_session):
        """Create OnboardingSystem with real dependencies"""
        event_bus = EventBus(redis_client=redis_client)
        system = OnboardingSystem(
            event_bus=event_bus,
            db_session=db_session
        )
        return system

    @pytest.mark.asyncio
    async def test_publishes_question_answered_event(self, system):
        """Test that answering question publishes event"""
        published_events = []

        # Subscribe to events
        async def event_collector(event):
            published_events.append(event)

        await system.event_bus.subscribe(
            "question.answered",
            event_collector,
            consumer_group="test"
        )

        # User answers question
        user = UserFactory()
        question = QuestionFactory()

        await system.submit_answer(
            user_id=user.telegram_id,
            question_id=question.id,
            answer_text="I feel calm and peaceful"
        )

        await asyncio.sleep(0.5)

        # Verify event was published
        assert len(published_events) == 1
        event = published_events[0]
        assert event.user_id == user.telegram_id
        assert event.question_id == question.id

    @pytest.mark.asyncio
    async def test_publishes_fatigue_detected_event(self, system):
        """Test that fatigue detection publishes event"""
        published_events = []

        async def event_collector(event):
            published_events.append(event)

        await system.event_bus.subscribe(
            "fatigue.detected",
            event_collector,
            consumer_group="test"
        )

        # Simulate long session that triggers fatigue
        user = UserFactory()

        # Answer many questions
        for i in range(50):
            question = QuestionFactory()
            await system.submit_answer(
                user_id=user.telegram_id,
                question_id=question.id,
                answer_text=f"Answer {i}"
            )

        await asyncio.sleep(1)

        # Should have triggered fatigue event
        fatigue_events = [
            e for e in published_events
            if e.event_type == "fatigue.detected"
        ]
        assert len(fatigue_events) > 0
```

---

## ANALYSIS SYSTEM TESTS

### 8. Unit Tests - AnswerAnalyzer

```python
# tests/systems/analysis/unit/test_answer_analyzer.py

import pytest
from systems.analysis.answer_analyzer import AnswerAnalyzer, AnalysisPhase
from tests.fixtures.factories import AnswerFactory


class TestAnswerAnalyzer:
    """Unit tests for AI answer analysis"""

    @pytest.fixture
    def analyzer(self, mock_ai_router):
        return AnswerAnalyzer(ai_router=mock_ai_router)

    @pytest.mark.asyncio
    async def test_instant_analysis_is_fast(self, analyzer):
        """Test that instant analysis completes quickly"""
        answer = AnswerFactory(text="I feel very happy and energetic today")

        import time
        start = time.time()

        result = await analyzer.analyze_instant(answer)

        duration = time.time() - start

        # Must be <500ms
        assert duration < 0.5
        assert result.phase == AnalysisPhase.INSTANT
        assert result.extracted_traits is not None

    @pytest.mark.asyncio
    async def test_deep_analysis_extracts_detailed_traits(self, analyzer):
        """Test that deep analysis provides detailed trait extraction"""
        answer = AnswerFactory(
            text="I've always been someone who seeks deep connections. "
                 "Superficial relationships leave me feeling empty. "
                 "I need authenticity and vulnerability to feel truly connected."
        )

        result = await analyzer.analyze_deep(answer)

        assert result.phase == AnalysisPhase.DEEP
        # Should extract multiple traits
        assert len(result.extracted_traits) >= 3
        # Should have high confidence for clear statements
        assert result.confidence > 0.7

    @pytest.mark.asyncio
    async def test_trait_extraction_for_big_five(self, analyzer):
        """Test extraction of Big Five personality traits"""
        # High Openness answer
        openness_answer = AnswerFactory(
            text="I love exploring new ideas and trying unconventional approaches"
        )

        result = await analyzer.analyze_deep(openness_answer)

        assert "openness" in result.extracted_traits
        assert result.extracted_traits["openness"] > 0.6

    @pytest.mark.asyncio
    async def test_analyzer_handles_short_answers(self, analyzer):
        """Test graceful handling of short/low-quality answers"""
        short_answer = AnswerFactory(text="Yes")

        result = await analyzer.analyze_instant(short_answer)

        # Should complete but with low confidence
        assert result.confidence < 0.4
        # Should flag as low quality
        assert result.quality_score < 0.5

    @pytest.mark.asyncio
    async def test_analyzer_detects_emotional_content(self, analyzer):
        """Test detection of emotional content in answers"""
        emotional_answer = AnswerFactory(
            text="I've been feeling so overwhelmed lately. Everything feels heavy."
        )

        result = await analyzer.analyze_deep(emotional_answer)

        assert result.emotional_valence < 0.3  # Negative
        assert result.emotional_intensity > 0.7  # High intensity

    @pytest.mark.asyncio
    async def test_analyzer_respects_context(self, analyzer):
        """Test that analyzer uses question context"""
        answer = AnswerFactory(
            text="Very often",
            question_context={
                "question_text": "How often do you feel anxious?",
                "domain": "EMOTIONS"
            }
        )

        result = await analyzer.analyze_deep(answer)

        # Should interpret "very often" in context of anxiety question
        assert "neuroticism" in result.extracted_traits
        assert result.extracted_traits["neuroticism"] > 0.6
```

### 9. Integration Tests - Analysis Worker

```python
# tests/systems/analysis/integration/test_analysis_worker.py

import pytest
import asyncio
from systems.analysis.analysis_worker import AnalysisWorker
from core.event_bus import EventBus
from core.domain_events import QuestionAnsweredEvent, AnalysisCompletedEvent
from tests.fixtures.factories import UserFactory


@pytest.mark.integration
class TestAnalysisWorker:
    """Integration tests for Analysis Worker event processing"""

    @pytest.fixture
    async def worker(self, redis_client, db_session, mock_ai_router):
        event_bus = EventBus(redis_client=redis_client)
        worker = AnalysisWorker(
            event_bus=event_bus,
            db_session=db_session,
            ai_router=mock_ai_router
        )
        return worker

    @pytest.mark.asyncio
    async def test_worker_processes_question_answered_event(self, worker):
        """Test worker listens and processes QuestionAnsweredEvent"""
        # Start worker
        worker_task = asyncio.create_task(worker.start())
        await asyncio.sleep(0.1)

        # Publish event
        event = QuestionAnsweredEvent(
            user_id=123456,
            session_id="sess_test",
            question_id="q_001",
            answer_text="I feel calm and peaceful",
            question_metadata={"domain": "EMOTIONS"}
        )

        await worker.event_bus.publish(event)

        # Wait for processing
        await asyncio.sleep(1)

        # Verify analysis was stored in DB
        analysis = await worker.db_session.execute(
            "SELECT * FROM analysis_results WHERE user_id = 123456"
        )
        result = analysis.fetchone()

        assert result is not None
        assert result.question_id == "q_001"

        # Cleanup
        worker_task.cancel()

    @pytest.mark.asyncio
    async def test_worker_publishes_analysis_completed(self, worker):
        """Test worker publishes AnalysisCompletedEvent after processing"""
        completed_events = []

        async def collector(event):
            completed_events.append(event)

        await worker.event_bus.subscribe(
            "analysis.completed",
            collector,
            consumer_group="test"
        )

        # Start worker
        worker_task = asyncio.create_task(worker.start())
        await asyncio.sleep(0.1)

        # Publish input event
        event = QuestionAnsweredEvent(
            user_id=123456,
            session_id="sess_test",
            question_id="q_001",
            answer_text="Test answer"
        )
        await worker.event_bus.publish(event)

        # Wait for processing and event publishing
        await asyncio.sleep(2)

        # Verify AnalysisCompletedEvent was published
        assert len(completed_events) == 1
        assert completed_events[0].user_id == 123456

        worker_task.cancel()

    @pytest.mark.asyncio
    async def test_worker_retry_on_failure(self, worker, mock_ai_router):
        """Test worker retries on AI API failure"""
        # Make AI router fail first time, succeed second time
        mock_ai_router.analyze.side_effect = [
            Exception("API timeout"),
            {"traits": {"openness": 0.7}}
        ]

        worker_task = asyncio.create_task(worker.start())
        await asyncio.sleep(0.1)

        event = QuestionAnsweredEvent(
            user_id=123456,
            question_id="q_001",
            answer_text="Test"
        )
        await worker.event_bus.publish(event)

        await asyncio.sleep(3)

        # Should have retried and succeeded
        assert mock_ai_router.analyze.call_count == 2

        worker_task.cancel()

    @pytest.mark.asyncio
    async def test_worker_handles_queue_backlog(self, worker):
        """Test worker processes backlog efficiently"""
        # Publish 100 events
        for i in range(100):
            event = QuestionAnsweredEvent(
                user_id=123456,
                question_id=f"q_{i:03d}",
                answer_text=f"Answer {i}"
            )
            await worker.event_bus.publish(event)

        # Start worker
        worker_task = asyncio.create_task(worker.start())

        # Wait for processing
        await asyncio.sleep(10)

        # Check that most/all were processed
        analysis_count = await worker.db_session.execute(
            "SELECT COUNT(*) FROM analysis_results WHERE user_id = 123456"
        )
        count = analysis_count.scalar()

        # Should process at least 90% (allowing for timing)
        assert count >= 90

        worker_task.cancel()
```

---

## PROFILE SYSTEM TESTS

### 10. Unit Tests - Soul Architect

```python
# tests/systems/profile/unit/test_soul_architect.py

import pytest
from systems.profile.soul_architect import SoulArchitect, PersonalityProfile
from tests.fixtures.factories import TraitAssessmentFactory


class TestSoulArchitect:
    """Unit tests for Soul Architect multilayer personality model"""

    @pytest.fixture
    def architect(self):
        return SoulArchitect()

    def test_create_empty_profile(self, architect):
        """Test creation of new profile with default traits"""
        profile = architect.create_profile(user_id=123456)

        assert profile.user_id == 123456
        assert profile.completeness == 0.0
        assert profile.total_samples == 0
        # All traits should start at neutral/unknown
        assert profile.big_five.openness.value == 0.5

    def test_update_trait_from_analysis(self, architect):
        """Test updating profile trait from new analysis"""
        profile = architect.create_profile(user_id=123456)

        # Initial state
        assert profile.big_five.openness.samples == 0

        # Update with analysis result
        architect.update_trait(
            profile=profile,
            trait_name="openness",
            new_value=0.75,
            confidence=0.85
        )

        # Should have updated
        assert profile.big_five.openness.samples == 1
        assert profile.big_five.openness.value > 0.5
        assert profile.big_five.openness.confidence > 0.0

    def test_trait_history_tracking(self, architect):
        """Test that trait changes are tracked over time"""
        profile = architect.create_profile(user_id=123456)

        # Make multiple updates
        for value in [0.6, 0.7, 0.75, 0.8]:
            architect.update_trait(
                profile=profile,
                trait_name="openness",
                new_value=value,
                confidence=0.8
            )

        history = architect.get_trait_history(
            profile=profile,
            trait_name="openness"
        )

        assert len(history) == 4
        # Should show progression
        assert history[-1].value > history[0].value

    def test_multilayer_personality_693d(self, architect):
        """Test 693-dimensional personality model"""
        profile = architect.create_profile(user_id=123456)

        # Get full vector
        vector = architect.get_personality_vector(profile)

        # Should be 693 dimensions
        assert len(vector) == 693

        # Components:
        # - Big Five: 5
        # - Core Dynamics: 7
        # - Adaptive Traits: 5
        # - Domain Affinities: 13
        # - Plus extended traits...

    def test_unique_signature_generation(self, architect):
        """Test generation of unique personality signature"""
        profile = architect.create_profile(user_id=123456)

        # Populate with some data
        profile.big_five.openness.value = 0.85
        profile.big_five.conscientiousness.value = 0.45
        profile.core_dynamics.authenticity.value = 0.90

        signature = architect.generate_unique_signature(profile)

        assert signature.thinking_style is not None
        assert signature.decision_pattern is not None
        assert signature.energy_rhythm is not None

    def test_profile_completeness_calculation(self, architect):
        """Test calculation of profile completeness"""
        profile = architect.create_profile(user_id=123456)

        # Empty profile = 0% complete
        assert profile.completeness == 0.0

        # Add some traits
        for _ in range(10):
            architect.update_trait(
                profile=profile,
                trait_name="openness",
                new_value=0.7,
                confidence=0.8
            )

        # Completeness should increase
        assert profile.completeness > 0.0
        assert profile.completeness < 1.0
```

### 11. Integration Tests - Profile Events

```python
# tests/systems/profile/integration/test_profile_events.py

import pytest
import asyncio
from systems.profile.profile_system import ProfileSystem
from core.event_bus import EventBus
from core.domain_events import AnalysisCompletedEvent, ProfileUpdatedEvent


@pytest.mark.integration
class TestProfileEventHandling:
    """Integration tests for Profile System event handling"""

    @pytest.fixture
    async def system(self, redis_client, db_session):
        event_bus = EventBus(redis_client=redis_client)
        system = ProfileSystem(
            event_bus=event_bus,
            db_session=db_session
        )
        return system

    @pytest.mark.asyncio
    async def test_listens_to_analysis_completed(self, system):
        """Test system processes AnalysisCompletedEvent"""
        # Start system
        system_task = asyncio.create_task(system.start())
        await asyncio.sleep(0.1)

        # Publish analysis event
        event = AnalysisCompletedEvent(
            user_id=123456,
            analysis_id="analysis_001",
            question_id="q_001",
            extracted_traits={
                "openness": 0.75,
                "conscientiousness": 0.65
            },
            confidence=0.85
        )

        await system.event_bus.publish(event)
        await asyncio.sleep(1)

        # Verify profile was updated in DB
        profile = await system.db_session.execute(
            "SELECT * FROM personality_profiles WHERE user_id = 123456"
        )
        result = profile.fetchone()

        assert result is not None

        system_task.cancel()

    @pytest.mark.asyncio
    async def test_publishes_profile_updated(self, system):
        """Test system publishes ProfileUpdatedEvent"""
        updated_events = []

        async def collector(event):
            updated_events.append(event)

        await system.event_bus.subscribe(
            "profile.updated",
            collector,
            consumer_group="test"
        )

        # Start system
        system_task = asyncio.create_task(system.start())
        await asyncio.sleep(0.1)

        # Trigger profile update
        event = AnalysisCompletedEvent(
            user_id=123456,
            analysis_id="analysis_001",
            extracted_traits={"openness": 0.8},
            confidence=0.9
        )
        await system.event_bus.publish(event)

        await asyncio.sleep(2)

        # Should have published ProfileUpdatedEvent
        assert len(updated_events) > 0
        assert updated_events[0].user_id == 123456

        system_task.cancel()
```

---

## CONTRACT TESTS

### 12. Producer Contract Tests

```python
# tests/contracts/producers/test_onboarding_contracts.py

import pytest
from systems.onboarding.onboarding_system import OnboardingSystem
from contracts.schemas import EventSchemaValidator


class TestOnboardingProducerContracts:
    """Contract tests for Onboarding System event production"""

    @pytest.fixture
    def validator(self):
        return EventSchemaValidator()

    @pytest.mark.asyncio
    async def test_question_answered_event_contract(self, system, validator):
        """Test QuestionAnsweredEvent matches contract"""
        # Trigger event production
        await system.submit_answer(
            user_id=123456,
            question_id="q_001",
            answer_text="Test answer"
        )

        # Get published event
        event = system.event_bus.last_published_event

        # Validate against contract schema
        is_valid = validator.validate(
            event=event,
            schema_name="question_answered",
            schema_version="v1"
        )

        assert is_valid
        # Verify required fields
        assert validator.has_required_fields(event, [
            "user_id",
            "session_id",
            "question_id",
            "answer_text",
            "timestamp"
        ])

    @pytest.mark.asyncio
    async def test_fatigue_detected_event_contract(self, system, validator):
        """Test FatigueDetectedEvent matches contract"""
        # Trigger fatigue
        for i in range(50):
            await system.submit_answer(
                user_id=123456,
                question_id=f"q_{i}",
                answer_text="Answer"
            )

        # Find fatigue event
        fatigue_event = next(
            e for e in system.event_bus.published_events
            if e.event_type == "fatigue.detected"
        )

        is_valid = validator.validate(
            event=fatigue_event,
            schema_name="fatigue_detected",
            schema_version="v1"
        )

        assert is_valid
```

### 13. Consumer Contract Tests

```python
# tests/contracts/consumers/test_analysis_contracts.py

import pytest
from systems.analysis.analysis_worker import AnalysisWorker
from core.domain_events import QuestionAnsweredEvent


class TestAnalysisConsumerContracts:
    """Contract tests for Analysis System event consumption"""

    @pytest.mark.asyncio
    async def test_handles_v1_question_answered(self, worker):
        """Test worker handles v1 QuestionAnsweredEvent"""
        event = QuestionAnsweredEvent(
            user_id=123456,
            session_id="sess_abc",
            question_id="q_001",
            answer_text="Test answer"
        )

        # Should process without error
        result = await worker.process_event(event)
        assert result is not None

    @pytest.mark.asyncio
    async def test_handles_v2_with_extra_fields(self, worker):
        """Test worker handles future v2 with extra fields"""
        # Simulate v2 event with new fields
        event_data = {
            "user_id": 123456,
            "session_id": "sess_abc",
            "question_id": "q_001",
            "answer_text": "Test answer",
            # v2 fields
            "sentiment": 0.8,
            "language": "ru"
        }

        event = QuestionAnsweredEvent(**event_data)

        # Should not crash on unknown fields
        result = await worker.process_event(event)
        assert result is not None

    @pytest.mark.asyncio
    async def test_graceful_degradation_on_missing_optional(self, worker):
        """Test graceful handling when optional fields missing"""
        # Minimal event with only required fields
        event = QuestionAnsweredEvent(
            user_id=123456,
            question_id="q_001",
            answer_text="Test"
            # Missing optional question_metadata
        )

        # Should still process
        result = await worker.process_event(event)
        assert result is not None
```

---

## LOAD TESTS

### 14. Load Testing with Locust

```python
# tests/load/locustfile.py

from locust import HttpUser, task, between, events
import random


class SelfologyUser(HttpUser):
    """Simulates a Selfology bot user"""

    wait_time = between(5, 15)  # Think time between questions

    def on_start(self):
        """Called when user starts - initialize session"""
        self.user_id = random.randint(100000, 999999)
        self.session_id = f"load_test_sess_{self.user_id}"
        self.questions_answered = 0

    @task(5)
    def answer_question(self):
        """Answer a question (most common action)"""
        self.questions_answered += 1

        payload = {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "question_id": f"q_{random.randint(1, 693)}",
            "answer_text": self.generate_realistic_answer()
        }

        with self.client.post(
            "/api/onboarding/answer",
            json=payload,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status {response.status_code}")

    @task(1)
    def check_profile(self):
        """Check profile (less frequent)"""
        self.client.get(
            f"/api/profile/{self.user_id}",
            name="/api/profile/[user_id]"
        )

    @task(1)
    def chat_with_coach(self):
        """Chat with AI coach (less frequent)"""
        payload = {
            "user_id": self.user_id,
            "message": "Tell me about my personality"
        }

        self.client.post(
            "/api/coach/chat",
            json=payload
        )

    def generate_realistic_answer(self):
        """Generate realistic answer text"""
        templates = [
            "I usually feel quite {} about this",
            "In my experience, I tend to {}",
            "I would say that I {}",
            "Most of the time, I {}",
        ]

        feelings = ["calm", "anxious", "excited", "uncertain", "confident"]

        template = random.choice(templates)
        feeling = random.choice(feelings)

        return template.format(feeling)


# Custom metrics
@events.init_command_line_parser.add_listener
def _(parser):
    parser.add_argument("--target-rps", type=int, default=1000, help="Target requests per second")


@events.test_start.add_listener
def _(environment, **kwargs):
    print(f"Load test starting with target: {environment.parsed_options.target_rps} RPS")


@events.test_stop.add_listener
def _(environment, **kwargs):
    print(f"Load test completed")
    print(f"Total requests: {environment.stats.total.num_requests}")
    print(f"Failures: {environment.stats.total.num_failures}")
    print(f"Median response time: {environment.stats.total.median_response_time}ms")
    print(f"95th percentile: {environment.stats.total.get_response_time_percentile(0.95)}ms")
```

### 15. Performance Benchmark Tests

```python
# tests/load/test_performance_benchmarks.py

import pytest
import asyncio
import time
from systems.analysis.answer_analyzer import AnswerAnalyzer


class TestPerformanceBenchmarks:
    """Performance benchmark tests"""

    @pytest.mark.benchmark
    def test_instant_analysis_performance(self, benchmark, analyzer):
        """Benchmark instant analysis performance"""
        answer = "I feel calm and peaceful today"

        def run_analysis():
            return asyncio.run(analyzer.analyze_instant(answer))

        result = benchmark(run_analysis)

        # Should be <500ms (benchmark will show actual time)
        assert benchmark.stats.mean < 0.5

    @pytest.mark.benchmark
    def test_event_publish_performance(self, benchmark, event_bus):
        """Benchmark event publishing throughput"""
        from core.domain_events import QuestionAnsweredEvent

        event = QuestionAnsweredEvent(
            user_id=123456,
            question_id="q_001",
            answer_text="Test"
        )

        def publish():
            return asyncio.run(event_bus.publish(event))

        result = benchmark(publish)

        # Should publish >1000 events/second
        ops_per_second = 1.0 / benchmark.stats.mean
        assert ops_per_second > 1000

    @pytest.mark.benchmark
    def test_profile_vector_generation(self, benchmark, soul_architect):
        """Benchmark 693D vector generation"""
        profile = soul_architect.create_profile(user_id=123456)

        result = benchmark(soul_architect.get_personality_vector, profile)

        # Should generate vector in <100ms
        assert benchmark.stats.mean < 0.1
```

---

## CHAOS TESTS

### 16. Chaos Test - Kill Analysis Worker

```python
# tests/chaos/test_worker_failure.py

import pytest
import asyncio
import signal
from systems.analysis.analysis_worker import AnalysisWorker
from core.domain_events import QuestionAnsweredEvent


@pytest.mark.chaos
class TestAnalysisWorkerChaos:
    """Chaos tests for Analysis Worker resilience"""

    @pytest.mark.asyncio
    async def test_worker_death_and_recovery(self, event_bus, db_session):
        """Test system recovers when worker dies"""

        # Start first worker
        worker1 = AnalysisWorker(event_bus=event_bus, db_session=db_session)
        worker1_task = asyncio.create_task(worker1.start())

        await asyncio.sleep(0.5)

        # Publish events
        for i in range(10):
            event = QuestionAnsweredEvent(
                user_id=123456,
                question_id=f"q_{i}",
                answer_text=f"Answer {i}"
            )
            await event_bus.publish(event)

        await asyncio.sleep(1)

        # Kill worker brutally
        worker1_task.cancel()
        await asyncio.sleep(0.5)

        # Start new worker (simulates automatic restart)
        worker2 = AnalysisWorker(event_bus=event_bus, db_session=db_session)
        worker2_task = asyncio.create_task(worker2.start())

        await asyncio.sleep(2)

        # Check that pending events were processed by worker2
        result = await db_session.execute(
            "SELECT COUNT(*) FROM analysis_results WHERE user_id = 123456"
        )
        count = result.scalar()

        # Should have processed all or most events
        assert count >= 8  # Allow some timing margin

        worker2_task.cancel()

    @pytest.mark.asyncio
    async def test_multiple_worker_failures(self, event_bus, db_session):
        """Test system survives multiple worker failures"""
        processed = 0
        target = 50

        # Publish target events
        for i in range(target):
            event = QuestionAnsweredEvent(
                user_id=123456,
                question_id=f"q_{i}",
                answer_text=f"Answer {i}"
            )
            await event_bus.publish(event)

        # Start workers and kill them randomly
        for attempt in range(5):
            worker = AnalysisWorker(event_bus=event_bus, db_session=db_session)
            task = asyncio.create_task(worker.start())

            # Let it process for random time
            await asyncio.sleep(random.uniform(0.5, 2.0))

            # Kill it
            task.cancel()

            await asyncio.sleep(0.2)

        # Final worker to clean up
        worker = AnalysisWorker(event_bus=event_bus, db_session=db_session)
        task = asyncio.create_task(worker.start())
        await asyncio.sleep(3)
        task.cancel()

        # Count processed
        result = await db_session.execute(
            "SELECT COUNT(*) FROM analysis_results WHERE user_id = 123456"
        )
        processed = result.scalar()

        # Should eventually process all (no messages lost)
        assert processed >= target * 0.9  # 90% threshold
```

### 17. Chaos Test - Redis Failure

```python
# tests/chaos/test_redis_failure.py

import pytest
import asyncio
from unittest.mock import patch
from redis.exceptions import ConnectionError as RedisConnectionError
from core.event_bus import EventBus
from core.domain_events import QuestionAnsweredEvent


@pytest.mark.chaos
class TestRedisFailureChaos:
    """Chaos tests for Redis unavailability"""

    @pytest.mark.asyncio
    async def test_graceful_degradation_on_redis_down(self, event_bus):
        """Test system degrades gracefully when Redis is unavailable"""

        # Make Redis unavailable
        with patch.object(event_bus.redis_client, 'xadd') as mock_xadd:
            mock_xadd.side_effect = RedisConnectionError("Connection refused")

            event = QuestionAnsweredEvent(
                user_id=123456,
                question_id="q_001",
                answer_text="Test"
            )

            # Should not crash
            result = await event_bus.publish(event, use_fallback=True)

            # Fallback mechanism should activate
            assert result is not None
            # Event should be in fallback queue or handled differently

    @pytest.mark.asyncio
    async def test_circuit_breaker_activates(self, event_bus):
        """Test circuit breaker prevents cascading failures"""

        # Simulate repeated Redis failures
        with patch.object(event_bus.redis_client, 'xadd') as mock_xadd:
            mock_xadd.side_effect = RedisConnectionError("Connection refused")

            # Try to publish many events
            for i in range(100):
                event = QuestionAnsweredEvent(
                    user_id=123456,
                    question_id=f"q_{i}",
                    answer_text="Test"
                )
                await event_bus.publish(event, use_fallback=True)

            # Circuit breaker should have opened after threshold
            assert event_bus.circuit_breaker.is_open()

            # Further attempts should fail fast (not try Redis)
            assert mock_xadd.call_count < 100  # Stopped trying after threshold

    @pytest.mark.asyncio
    async def test_recovery_after_redis_comes_back(self, event_bus):
        """Test system recovers when Redis comes back online"""

        # Redis fails
        with patch.object(event_bus.redis_client, 'xadd') as mock_xadd:
            mock_xadd.side_effect = RedisConnectionError("Connection refused")

            # Publish events (will fail)
            for i in range(10):
                event = QuestionAnsweredEvent(
                    user_id=123456,
                    question_id=f"q_{i}",
                    answer_text="Test"
                )
                await event_bus.publish(event, use_fallback=True)

        # Redis comes back (no more mock)
        # Circuit breaker should eventually close
        await asyncio.sleep(2)  # Wait for circuit breaker timeout

        # New events should work
        event = QuestionAnsweredEvent(
            user_id=123456,
            question_id="q_recovery",
            answer_text="Test"
        )
        result = await event_bus.publish(event)

        assert result is True
```

### 18. Chaos Test - Database Timeout

```python
# tests/chaos/test_db_timeout.py

import pytest
import asyncio
from unittest.mock import patch
from sqlalchemy.exc import OperationalError
from systems.profile.profile_system import ProfileSystem


@pytest.mark.chaos
class TestDatabaseTimeoutChaos:
    """Chaos tests for database timeouts"""

    @pytest.mark.asyncio
    async def test_retry_on_db_timeout(self, profile_system):
        """Test system retries on database timeout"""

        # Make first 2 DB calls timeout, 3rd succeeds
        with patch.object(profile_system.db_session, 'execute') as mock_execute:
            mock_execute.side_effect = [
                OperationalError("connection timeout", None, None),
                OperationalError("connection timeout", None, None),
                {"user_id": 123456}  # Success on 3rd attempt
            ]

            # Should retry and eventually succeed
            result = await profile_system.update_profile(
                user_id=123456,
                traits={"openness": 0.8}
            )

            assert result is not None
            assert mock_execute.call_count == 3

    @pytest.mark.asyncio
    async def test_eventual_consistency_on_db_failure(self, profile_system):
        """Test eventual consistency when DB write fails"""

        # DB write fails completely
        with patch.object(profile_system.db_session, 'commit') as mock_commit:
            mock_commit.side_effect = OperationalError("deadlock", None, None)

            # Update should be queued for retry
            await profile_system.update_profile(
                user_id=123456,
                traits={"openness": 0.8},
                eventual_consistency=True
            )

            # Check retry queue
            pending = await profile_system.get_pending_writes()
            assert len(pending) > 0
```

---

## E2E TESTS

### 19. Complete User Journey E2E Test

```python
# tests/e2e/test_complete_user_journey.py

import pytest
import asyncio
from tests.fixtures.factories import UserFactory


@pytest.mark.e2e
class TestCompleteUserJourney:
    """End-to-end test of complete user journey"""

    @pytest.mark.asyncio
    async def test_full_onboarding_to_insight(
        self,
        telegram_system,
        onboarding_system,
        analysis_system,
        profile_system,
        coach_system
    ):
        """
        Test complete flow:
        /start → onboarding → answer questions → AI analysis →
        profile update → coach generates insight
        """
        user = UserFactory()

        # 1. User starts bot
        response = await telegram_system.handle_command(
            user_id=user.telegram_id,
            command="/start"
        )
        assert "Добро пожаловать" in response.text

        # 2. User starts onboarding
        response = await telegram_system.handle_command(
            user_id=user.telegram_id,
            command="/onboarding"
        )
        assert response.contains_question

        # 3. User answers first question
        response = await telegram_system.handle_message(
            user_id=user.telegram_id,
            text="I feel calm and peaceful most of the time"
        )

        # Should get instant feedback
        assert response.text is not None
        await asyncio.sleep(0.5)

        # 4. Wait for deep analysis to complete
        await asyncio.sleep(3)

        # Verify analysis was saved
        analysis = await analysis_system.get_latest_analysis(user.telegram_id)
        assert analysis is not None
        assert analysis.extracted_traits is not None

        # 5. Answer more questions (simulate 10 questions)
        for i in range(9):
            response = await telegram_system.handle_message(
                user_id=user.telegram_id,
                text=f"Answer number {i+2}"
            )
            await asyncio.sleep(1)

        # 6. Check profile was updated
        profile = await profile_system.get_profile(user.telegram_id)
        assert profile is not None
        assert profile.total_samples >= 10
        assert profile.completeness > 0.0

        # 7. User chats with coach
        response = await coach_system.handle_message(
            user_id=user.telegram_id,
            message="Tell me about my personality"
        )

        # Coach should use personality context
        assert response.text is not None
        assert len(response.text) > 50  # Substantial response

        # 8. Verify coach used profile
        # (check that profile was loaded)
        assert coach_system.last_profile_loaded.user_id == user.telegram_id

    @pytest.mark.asyncio
    async def test_fatigue_detection_in_journey(
        self,
        telegram_system,
        onboarding_system
    ):
        """Test that fatigue detection works during real session"""
        user = UserFactory()

        await telegram_system.handle_command(
            user_id=user.telegram_id,
            command="/onboarding"
        )

        # Answer many questions quickly
        for i in range(50):
            response = await telegram_system.handle_message(
                user_id=user.telegram_id,
                text=f"Quick answer {i}"
            )
            await asyncio.sleep(0.2)  # Very quick

        # Should have triggered fatigue detection
        session = await onboarding_system.get_session(user.telegram_id)
        assert session.fatigue_detected is True

        # Last response should suggest pause
        assert "отдохни" in response.text.lower() or "пауза" in response.text.lower()
```

---

## TEST FIXTURES

### 20. Factory Fixtures

```python
# tests/fixtures/factories.py

import factory
from factory import Faker, fuzzy
from datetime import datetime, timedelta
import random


class UserFactory(factory.Factory):
    """Factory for creating test users"""

    class Meta:
        model = dict

    telegram_id = fuzzy.FuzzyInteger(100000, 999999)
    username = Faker('user_name')
    first_name = Faker('first_name')
    language_code = 'ru'
    created_at = Faker('date_time_this_year')


class QuestionFactory(factory.Factory):
    """Factory for creating test questions"""

    class Meta:
        model = dict

    id = factory.Sequence(lambda n: f"q_{n:03d}")
    text = Faker('sentence', nb_words=10)
    domain = fuzzy.FuzzyChoice([
        "IDENTITY", "EMOTIONS", "RELATIONSHIPS", "CAREER",
        "SPIRITUALITY", "CREATIVITY", "BODY", "PAST", "FUTURE"
    ])
    depth_level = fuzzy.FuzzyChoice([
        "SURFACE", "CONSCIOUS", "EDGE", "SHADOW", "CORE"
    ])
    energy = fuzzy.FuzzyChoice([
        "OPENING", "NEUTRAL", "PROCESSING", "HEAVY", "HEALING"
    ])


class AnswerFactory(factory.Factory):
    """Factory for creating test answers"""

    class Meta:
        model = dict

    user_id = fuzzy.FuzzyInteger(100000, 999999)
    question_id = factory.LazyFunction(lambda: f"q_{random.randint(1, 693):03d}")
    answer_text = Faker('paragraph', nb_sentences=3)
    answered_at = Faker('date_time_this_month')


class SessionFactory(factory.Factory):
    """Factory for creating test onboarding sessions"""

    class Meta:
        model = dict

    user_id = fuzzy.FuzzyInteger(100000, 999999)
    session_id = factory.Sequence(lambda n: f"sess_{n}")
    questions_answered = fuzzy.FuzzyInteger(0, 100)
    started_at = Faker('date_time_this_week')
    session_duration_minutes = fuzzy.FuzzyInteger(5, 120)

    @factory.lazy_attribute
    def recent_response_times(self):
        """Generate realistic response times"""
        base = 30  # 30 seconds base
        count = min(self.questions_answered, 10)
        return [base + random.uniform(-10, 20) for _ in range(count)]

    @factory.lazy_attribute
    def answered_domains(self):
        """Generate answered domains distribution"""
        domains = ["IDENTITY", "EMOTIONS", "RELATIONSHIPS", "CAREER"]
        total = self.questions_answered
        distribution = {}
        for domain in domains[:total // 5]:
            distribution[domain] = random.randint(1, total // 4)
        return distribution


class TraitAssessmentFactory(factory.Factory):
    """Factory for creating trait assessments"""

    class Meta:
        model = dict

    value = fuzzy.FuzzyFloat(0.0, 1.0)
    confidence = fuzzy.FuzzyFloat(0.5, 1.0)
    variance = fuzzy.FuzzyFloat(0.05, 0.2)
    samples = fuzzy.FuzzyInteger(1, 50)
```

---

## CONFTEST SETUP

### 21. Pytest Conftest

```python
# tests/conftest.py

import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from redis.asyncio import Redis
from unittest.mock import Mock, AsyncMock

from core.config import settings
from core.database import Base
from core.event_bus import EventBus


# --- Database Fixtures ---

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine"""
    # Use separate test database
    test_db_url = settings.database_url.replace("/n8n", "/n8n_test")

    engine = create_async_engine(
        test_db_url,
        echo=False,
        future=True
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create database session for test"""
    async_session = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        yield session
        await session.rollback()  # Rollback after each test


# --- Redis Fixtures ---

@pytest.fixture(scope="session")
async def redis_client():
    """Create Redis client for tests"""
    client = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        encoding="utf-8"
    )

    # Select test database (different from production)
    await client.select(15)

    yield client

    # Cleanup
    await client.flushdb()
    await client.close()


@pytest.fixture
def mock_redis():
    """Create mocked Redis client"""
    mock = AsyncMock(spec=Redis)
    mock.xadd = AsyncMock(return_value="1234567890-0")
    mock.xreadgroup = AsyncMock(return_value=[])
    mock.xack = AsyncMock(return_value=1)
    mock.xgroup_create = AsyncMock(return_value=True)
    return mock


# --- Event Bus Fixtures ---

@pytest.fixture
def event_bus(redis_client):
    """Create EventBus with real Redis"""
    return EventBus(redis_client=redis_client)


@pytest.fixture
def mock_event_bus(mock_redis):
    """Create EventBus with mocked Redis"""
    return EventBus(redis_client=mock_redis)


# --- AI Router Fixtures ---

@pytest.fixture
def mock_ai_router():
    """Create mocked AI router"""
    mock = AsyncMock()

    # Default successful responses
    mock.analyze = AsyncMock(return_value={
        "traits": {
            "openness": 0.7,
            "conscientiousness": 0.6,
            "extraversion": 0.5,
            "agreeableness": 0.8,
            "neuroticism": 0.4
        },
        "confidence": 0.85
    })

    mock.chat = AsyncMock(return_value={
        "response": "This is a test AI response",
        "model_used": "gpt-4o-mini"
    })

    return mock


# --- System Fixtures ---

@pytest.fixture
async def onboarding_system(event_bus, db_session):
    """Create OnboardingSystem for tests"""
    from systems.onboarding.onboarding_system import OnboardingSystem

    system = OnboardingSystem(
        event_bus=event_bus,
        db_session=db_session
    )
    return system


@pytest.fixture
async def analysis_system(event_bus, db_session, mock_ai_router):
    """Create AnalysisSystem for tests"""
    from systems.analysis.analysis_system import AnalysisSystem

    system = AnalysisSystem(
        event_bus=event_bus,
        db_session=db_session,
        ai_router=mock_ai_router
    )
    return system


@pytest.fixture
async def profile_system(event_bus, db_session):
    """Create ProfileSystem for tests"""
    from systems.profile.profile_system import ProfileSystem

    system = ProfileSystem(
        event_bus=event_bus,
        db_session=db_session
    )
    return system


# --- Pytest Configuration ---

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test"
    )
    config.addinivalue_line(
        "markers", "chaos: mark test as chaos engineering test"
    )
    config.addinivalue_line(
        "markers", "benchmark: mark test as performance benchmark"
    )


def pytest_collection_modifyitems(config, items):
    """Auto-skip slow tests unless explicitly requested"""
    if not config.getoption("--run-slow"):
        skip_slow = pytest.mark.skip(reason="need --run-slow option to run")
        for item in items:
            if "e2e" in item.keywords or "chaos" in item.keywords:
                item.add_marker(skip_slow)


def pytest_addoption(parser):
    """Add custom pytest options"""
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="run slow tests (e2e, chaos)"
    )
```

---

## PYTEST.INI CONFIGURATION

```ini
# pytest.ini

[pytest]
# Test discovery
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Async support
asyncio_mode = auto

# Coverage
addopts =
    --verbose
    --strict-markers
    --cov=selfology_bot
    --cov=systems
    --cov=core
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=85

# Test markers
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (with real services)
    e2e: End-to-end tests (full system)
    chaos: Chaos engineering tests
    benchmark: Performance benchmarks
    slow: Slow tests (skip by default)

# Logging
log_cli = true
log_cli_level = INFO
log_file = logs/pytest.log
log_file_level = DEBUG

# Timeout
timeout = 300
timeout_method = thread

# Parallel execution
testpaths = tests
```

---

## ЗАПУСК ТЕСТОВ

### Команды для запуска

```bash
# Все тесты
pytest

# Только unit тесты (быстрые)
pytest -m unit

# Integration тесты
pytest -m integration

# E2E тесты (медленные)
pytest -m e2e --run-slow

# Chaos тесты
pytest -m chaos --run-slow

# Конкретный файл
pytest tests/event_bus/unit/test_event_publisher.py

# Конкретный тест
pytest tests/event_bus/unit/test_event_publisher.py::TestEventPublisher::test_publish_simple_event

# С coverage
pytest --cov=core --cov-report=html

# Параллельно (быстрее)
pytest -n 4

# С подробным выводом
pytest -vv

# Остановиться на первом падении
pytest -x

# Re-run failed tests
pytest --lf

# Benchmark tests
pytest -m benchmark --benchmark-only
```

---

**Файл:** `/home/ksnk/n8n-enterprise/projects/selfology/TESTING_CODE_EXAMPLES.md`

**Статус:** Готов к использованию

**Следующий шаг:** Начать имплементацию с Event Bus тестов (Фаза 0)
