# Selfology Microservices API Documentation

> **Version:** 1.0.0
> **Last Updated:** 2025-10-01
> **Architecture:** Event-Driven Microservices

---

## Table of Contents

1. [Overview](#overview)
2. [Event-Driven Architecture](#event-driven-architecture)
3. [Microservices APIs](#microservices-apis)
4. [Event Catalog](#event-catalog)
5. [Error Handling](#error-handling)
6. [Authentication](#authentication)
7. [Rate Limiting](#rate-limiting)

---

## Overview

Selfology uses an **event-driven microservices architecture** where services communicate asynchronously via Redis Streams. Each microservice:

- Listens to specific event types
- Processes events independently
- Publishes new events via Outbox Pattern
- Provides health check endpoints

**Core Components:**
- **Event Bus**: Redis Streams for async communication
- **Outbox Pattern**: Guaranteed event delivery
- **Circuit Breaker**: Fault tolerance for external dependencies
- **AI Router**: Intelligent model selection with fallback chains

---

## Event-Driven Architecture

### Event Flow

```
User Action → TelegramGateway → Event Bus → Microservices → Event Bus → Response
```

### Outbox Pattern

All events are published via the Outbox Pattern to ensure guaranteed delivery:

1. Event written to `selfology.event_outbox` table (transactional)
2. OutboxRelay polls for pending events
3. Event published to Redis Streams
4. Outbox record marked as `published`

**Table Schema:**
```sql
CREATE TABLE selfology.event_outbox (
    id BIGSERIAL PRIMARY KEY,
    event_type VARCHAR(255) NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    trace_id VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    published_at TIMESTAMP WITH TIME ZONE
);
```

---

## Microservices APIs

### 1. Question Selection Service

**Purpose:** Selects next question using Smart Mix algorithm

**Events Consumed:**
- `session.created` - Initializes question selection for new session
- `user.answer.submitted` - Selects next question after answer

**Events Published:**
- `question.selected` - Question ready for user

**Event Payload Examples:**

**Input: `session.created`**
```json
{
  "event_type": "session.created",
  "payload": {
    "user_id": 123456,
    "session_id": 1,
    "timestamp": "2025-10-01T10:00:00Z"
  },
  "trace_id": "session_123456_1"
}
```

**Output: `question.selected`**
```json
{
  "event_type": "question.selected",
  "payload": {
    "user_id": 123456,
    "session_id": 1,
    "question_id": "q_identity_001",
    "question_text": "What makes you feel most alive?",
    "domain": "IDENTITY",
    "depth_level": "CONSCIOUS",
    "energy_dynamics": "OPENING",
    "timestamp": "2025-10-01T10:00:01Z"
  },
  "trace_id": "session_123456_1"
}
```

**Health Check:**
```bash
GET /health
Response: {"status": "healthy", "service": "question_selection", "uptime": 3600}
```

---

### 2. Session Management Service

**Purpose:** Manages onboarding sessions lifecycle

**Events Consumed:**
- `user.onboarding.initiated` - Creates new session

**Events Published:**
- `session.created` - New session initialized
- `session.completed` - Onboarding finished
- `session.timeout` - Session expired (30 min inactivity)

**Event Payload Examples:**

**Input: `user.onboarding.initiated`**
```json
{
  "event_type": "user.onboarding.initiated",
  "payload": {
    "user_id": 123456,
    "timestamp": "2025-10-01T10:00:00Z"
  },
  "trace_id": "onboarding_123456"
}
```

**Output: `session.created`**
```json
{
  "event_type": "session.created",
  "payload": {
    "user_id": 123456,
    "session_id": 1,
    "status": "active",
    "started_at": "2025-10-01T10:00:00Z",
    "timeout_at": "2025-10-01T10:30:00Z"
  },
  "trace_id": "onboarding_123456"
}
```

**Database Tables:**
```sql
-- Onboarding sessions
selfology.onboarding_sessions
  - id, user_id, status, started_at, completed_at, timeout_at

-- User answers
selfology.user_answers_new
  - id, user_id, session_id, question_id, answer_text, created_at
```

---

### 3. Analysis Worker Service

**Purpose:** Dual-phase psychological analysis (instant + deep)

**Events Consumed:**
- `user.answer.submitted` - Analyzes user answer

**Events Published:**
- `answer.analyzed.instant` - Quick feedback (<500ms)
- `answer.analyzed.deep` - Comprehensive analysis (2-10s)
- `trait.extracted` - Personality traits identified

**Event Payload Examples:**

**Input: `user.answer.submitted`**
```json
{
  "event_type": "user.answer.submitted",
  "payload": {
    "user_id": 123456,
    "session_id": 1,
    "question_id": "q_identity_001",
    "answer_text": "I feel most alive when creating art and helping others grow.",
    "answer_length": 62
  },
  "trace_id": "answer_123456_q1"
}
```

**Output: `answer.analyzed.instant`**
```json
{
  "event_type": "answer.analyzed.instant",
  "payload": {
    "user_id": 123456,
    "question_id": "q_identity_001",
    "sentiment": "positive",
    "quality_score": 0.85,
    "key_themes": ["creativity", "altruism"],
    "brief_insight": "You find meaning in creative expression and supporting others.",
    "latency_ms": 320,
    "timestamp": "2025-10-01T10:00:02Z"
  },
  "trace_id": "answer_123456_q1"
}
```

**Output: `trait.extracted`**
```json
{
  "event_type": "trait.extracted",
  "payload": {
    "user_id": 123456,
    "traits": {
      "openness": {"value": 0.82, "confidence": 0.75},
      "conscientiousness": {"value": 0.65, "confidence": 0.70},
      "extraversion": {"value": 0.55, "confidence": 0.65},
      "agreeableness": {"value": 0.78, "confidence": 0.80},
      "neuroticism": {"value": 0.42, "confidence": 0.60}
    },
    "model_used": "gpt-4o",
    "cost_usd": 0.0024,
    "timestamp": "2025-10-01T10:00:08Z"
  },
  "trace_id": "answer_123456_q1"
}
```

**AI Router Configuration:**
```python
# Model selection by complexity
SIMPLE_TASK:  GPT-4o-mini (15% of requests)
STANDARD_TASK: GPT-4o (75% of requests)
PREMIUM_TASK: Claude Sonnet 4 (10% of requests)

# Fallback chain
Claude Sonnet 4 → GPT-4o → GPT-4o-mini
```

---

### 4. Profile Storage Service

**Purpose:** Manages multilayer personality profiles

**Events Consumed:**
- `trait.extracted` - Updates profile with new traits

**Events Published:**
- `profile.updated` - Profile data changed
- `profile.created` - New profile initialized

**Profile Structure:**
```json
{
  "big_five": {
    "openness": {"value": 0.82, "confidence": 0.75},
    "conscientiousness": {"value": 0.65, "confidence": 0.70},
    "extraversion": {"value": 0.55, "confidence": 0.65},
    "agreeableness": {"value": 0.78, "confidence": 0.80},
    "neuroticism": {"value": 0.42, "confidence": 0.60}
  },
  "core_dynamics": {
    "self_awareness": 0.70,
    "emotional_regulation": 0.65,
    "motivation": 0.75,
    "resilience": 0.68
  },
  "adaptive_traits": {
    "learning_style": "visual-kinesthetic",
    "stress_response": "problem-solving",
    "decision_pattern": "intuitive-analytical"
  },
  "domain_affinities": {
    "IDENTITY": 0.85,
    "EMOTIONS": 0.78,
    "RELATIONSHIPS": 0.70,
    "GROWTH": 0.88
  }
}
```

**Database Tables:**
```sql
selfology.personality_profiles
  - id, user_id (unique), profile_data (JSONB), created_at, updated_at
```

**Vector Storage:**
- **Qdrant Collection**: `user_profiles_512d`
- **Vector Size**: 512 dimensions
- **Use Case**: Semantic search for similar profiles

---

### 5. Trait Evolution Service

**Purpose:** Tracks personality trait changes over time

**Events Consumed:**
- `trait.extracted` - Records trait changes

**Events Published:**
- `trait.evolution.detected` - Significant changes identified
- `trait.pattern.identified` - Patterns in trait evolution

**Pattern Types:**
- `increasing` - Trait value growing over time
- `decreasing` - Trait value declining
- `stable` - Little variation
- `oscillating` - High variance

**Event Payload Example:**

**Output: `trait.evolution.detected`**
```json
{
  "event_type": "trait.evolution.detected",
  "payload": {
    "user_id": 123456,
    "significant_changes": [
      {
        "trait_name": "openness",
        "old_value": 0.70,
        "new_value": 0.82,
        "change": 0.12,
        "trigger": "creative_answers"
      }
    ],
    "analysis_period_days": 7,
    "timestamp": "2025-10-01T10:00:10Z"
  }
}
```

**Database Tables:**
```sql
selfology.trait_history
  - id, user_id, trait_category, trait_name
  - old_value, new_value, confidence
  - trigger, timestamp
```

---

### 6. Telegram Gateway Service

**Purpose:** Pure event-driven gateway (NO business logic)

**Events Consumed:**
- `question.selected` - Send question to user
- `coach.message.ready` - Send coach response
- `state.change.requested` - Update FSM state

**Events Published:**
- `user.message.received` - User sent message
- `user.answer.submitted` - User answered question
- `user.onboarding.initiated` - /start command

**Features:**
- **Rate Limiting**: 30 requests per 60 seconds (per user)
- **FSM State**: Redis (with fallback to memory)
- **Circuit Breaker**: Protects Telegram API calls

**User States (FSM):**
```python
class UserStates:
    new_user = "new_user"
    gdpr_pending = "gdpr_pending"
    onboarding_active = "onboarding_active"
    waiting_for_answer = "waiting_for_answer"
    processing_answer = "processing_answer"
    onboarding_paused = "onboarding_paused"
    onboarding_complete = "onboarding_complete"
    chat_active = "chat_active"
    chat_paused = "chat_paused"
```

---

### 7. Coach Interaction Service

**Purpose:** Personalized AI coaching with profile context

**Events Consumed:**
- `user.message.received` - User chat message (in chat_active state)
- `profile.updated` - Adapt coaching style

**Events Published:**
- `coach.message.ready` - AI response ready for user

**Context Loading:**
1. Load user profile (Big Five traits)
2. Load last 10 conversation messages
3. Build personalized system prompt
4. Call AI with full context

**Personalization Example:**
```python
if openness > 0.6:
    style = "creative metaphors and non-standard approaches"
else:
    style = "practical actions and concrete steps"

if conscientiousness > 0.6:
    format = "structured plans with clear steps"
else:
    format = "flexible guidance with room for spontaneity"
```

**Event Payload Example:**

**Output: `coach.message.ready`**
```json
{
  "event_type": "coach.message.ready",
  "payload": {
    "user_id": 123456,
    "message_text": "I hear that you're feeling anxious about your career...",
    "model_used": "gpt-4o",
    "tokens_used": 450,
    "cost_usd": 0.0135,
    "timestamp": "2025-10-01T10:15:00Z"
  }
}
```

---

### 8. Outbox Relay Service

**Purpose:** Publishes pending events from outbox to Redis Streams

**Configuration:**
- **Polling Interval**: 1 second (production)
- **Batch Size**: 100 events per poll
- **Schema**: `selfology`

**Process:**
1. Poll `selfology.event_outbox` WHERE status='pending'
2. Publish each event to Redis Stream
3. Mark as `status='published'`
4. Retry on failure (exponential backoff)

**Health Check:**
```bash
GET /health
Response: {
  "status": "healthy",
  "service": "outbox_relay",
  "pending_events": 0,
  "published_total": 15234,
  "failed_total": 12
}
```

---

## Event Catalog

### Complete Event Types

#### Onboarding Events
- `user.onboarding.initiated` - User starts onboarding
- `session.created` - New session created
- `session.completed` - Onboarding finished
- `session.timeout` - Session expired
- `question.selected` - Question ready
- `user.answer.submitted` - User answered

#### Analysis Events
- `answer.analyzed.instant` - Quick analysis ready
- `answer.analyzed.deep` - Deep analysis ready
- `trait.extracted` - Traits identified

#### Profile Events
- `profile.created` - New profile
- `profile.updated` - Profile changed
- `trait.evolution.detected` - Significant changes
- `trait.pattern.identified` - Patterns found

#### Chat Events
- `user.message.received` - User sent message
- `coach.message.ready` - AI response ready
- `conversation.started` - Chat session began
- `conversation.ended` - Chat session ended

#### Gateway Events
- `message.send.requested` - Send message to user
- `state.change.requested` - Change FSM state

#### System Events
- `insight.generated` - Background insight ready
- `insight.ready_for_user` - Show insight to user

---

## Error Handling

### Error Response Format

```json
{
  "error": {
    "code": "ANALYSIS_FAILED",
    "message": "Failed to analyze answer",
    "details": {
      "reason": "AI API timeout",
      "retry_after": 5
    },
    "trace_id": "answer_123456_q1"
  }
}
```

### Error Codes

**Service Errors:**
- `SERVICE_UNAVAILABLE` - Service down
- `SERVICE_DEGRADED` - Partial functionality

**Analysis Errors:**
- `ANALYSIS_FAILED` - AI analysis error
- `AI_API_TIMEOUT` - AI API timeout
- `FALLBACK_CHAIN_EXHAUSTED` - All AI models failed

**Profile Errors:**
- `PROFILE_NOT_FOUND` - User profile missing
- `PROFILE_UPDATE_FAILED` - Update error

**Event Errors:**
- `EVENT_PUBLISH_FAILED` - Could not publish event
- `INVALID_EVENT_PAYLOAD` - Malformed event

---

## Authentication

### Internal Authentication

Microservices communicate via internal network without authentication (trusted environment).

### External Authentication

Telegram Gateway validates:
- Telegram bot token
- User ID from Telegram
- HMAC signature verification

---

## Rate Limiting

### User Rate Limits

**Telegram Gateway:**
- 30 requests per 60 seconds (per user)
- Algorithm: Sliding window (Redis sorted sets)
- Fail-open on Redis error

**Implementation:**
```python
class RateLimiter:
    def __init__(self, redis_client, max_requests=30, window_seconds=60):
        self.redis_client = redis_client
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def is_allowed(self, user_id: int) -> bool:
        key = f"rate_limit:user:{user_id}"
        now = datetime.now().timestamp()

        # Add current request
        await self.redis_client.zadd(key, {str(now): now})

        # Remove old requests
        cutoff = now - self.window_seconds
        await self.redis_client.zremrangebyscore(key, 0, cutoff)

        # Count requests in window
        count = await self.redis_client.zcard(key)

        return count <= self.max_requests
```

---

## Monitoring & Observability

### Health Checks

All services expose `/health` endpoint:

```json
{
  "status": "healthy",
  "service": "analysis_worker",
  "uptime": 3600,
  "database": "healthy",
  "redis": "healthy",
  "ai_router": "healthy",
  "metrics": {
    "requests_total": 1234,
    "errors_total": 5,
    "avg_latency_ms": 320
  }
}
```

### Metrics

**Prometheus Metrics:**
- `request_duration_seconds` - Request latency histogram
- `instant_analysis_duration_seconds` - Analysis latency
- `event_outbox_pending_count` - Events pending
- `ai_cost_usd_total` - AI API costs
- `circuit_breaker_state` - Circuit breaker status

---

## Best Practices

### Event Publishing

1. Always use Outbox Pattern (never direct publish)
2. Include `trace_id` for request tracing
3. Keep payloads small (<10KB)
4. Use idempotent event handlers

### Error Handling

1. Log all errors with `trace_id`
2. Use Circuit Breaker for external APIs
3. Implement retry with exponential backoff
4. Provide clear error messages

### Performance

1. Target: Instant analysis <500ms (p95)
2. Database queries <300ms (p95)
3. Redis operations <50ms (p95)
4. Event processing <200ms (p95)

---

## Support

For issues or questions:
- **GitHub**: [selfology/issues](https://github.com/selfology/issues)
- **Email**: support@selfology.me
- **Telegram**: @SelfologySupport

---

**Last Updated:** 2025-10-01
**Version:** 1.0.0
**Maintainer:** Selfology Team
