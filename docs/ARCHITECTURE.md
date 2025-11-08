# Selfology Architecture Documentation

> **Event-Driven Microservices Architecture**
> **Version:** 1.0.0
> **Last Updated:** 2025-10-01

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Microservices](#microservices)
4. [Event Flow](#event-flow)
5. [Data Architecture](#data-architecture)
6. [Infrastructure](#infrastructure)
7. [Resilience Patterns](#resilience-patterns)
8. [Scalability](#scalability)

---

## System Overview

Selfology is an AI-powered psychological coaching platform built on **event-driven microservices architecture**.

### Core Principles

✅ **Event-Driven**: Async communication via Redis Streams
✅ **Microservices**: 8 independent, loosely-coupled services
✅ **Guaranteed Delivery**: Outbox Pattern ensures no lost events
✅ **Fault Tolerance**: Circuit Breaker + Retry Pattern + Fallbacks
✅ **Cost Optimization**: Smart AI routing (Claude → GPT-4o → Mini)
✅ **Zero Downtime**: Blue-Green deployments
✅ **Observability**: Prometheus + Grafana + Alertmanager

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          TELEGRAM BOT                               │
│                     (User Interface Layer)                          │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     TELEGRAM GATEWAY SERVICE                        │
│  • Pure event-driven gateway (NO business logic)                    │
│  • FSM state management (Redis + fallback)                          │
│  • Rate limiting (30 req/60s per user)                              │
│  • Circuit Breaker for Telegram API                                 │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          EVENT BUS (Redis Streams)                  │
│  ┌────────────────┐                                                 │
│  │  Outbox Relay  │  Polls DB outbox → publishes to Redis          │
│  └────────────────┘                                                 │
│                                                                      │
│  Stream: selfology:events                                           │
│  Consumer Groups: question_selection, session_management, etc.      │
└─────────────────────────────────────────────────────────────────────┘
        │            │            │            │            │
        ▼            ▼            ▼            ▼            ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Question   │ │   Session    │ │   Analysis   │ │   Profile    │
│  Selection   │ │ Management   │ │   Worker     │ │   Storage    │
│              │ │              │ │              │ │              │
│ Smart Mix    │ │ Lifecycle    │ │ Dual-Phase   │ │ Multi-Layer  │
│ Algorithm    │ │ Tracking     │ │ Analysis     │ │ Profiles     │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
                                         │
                                         ▼
                                  ┌─────────────┐
                                  │  AI Router  │
                                  │             │
                                  │ Claude 10%  │
                                  │ GPT-4o 75%  │
                                  │ Mini   15%  │
                                  └─────────────┘
        │            │
        ▼            ▼
┌──────────────┐ ┌──────────────┐
│    Trait     │ │    Coach     │
│  Evolution   │ │ Interaction  │
│              │ │              │
│ Pattern      │ │ Personal.    │
│ Detection    │ │ Coaching     │
└──────────────┘ └──────────────┘

                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       STORAGE LAYER                                 │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │  PostgreSQL  │  │    Redis     │  │    Qdrant    │             │
│  │              │  │              │  │              │             │
│  │ • Profiles   │  │ • Event Bus  │  │ • Vectors    │             │
│  │ • Sessions   │  │ • FSM State  │  │ • Semantic   │             │
│  │ • History    │  │ • Cache      │  │   Search     │             │
│  │ • Outbox     │  │ • Rate Limit │  │              │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
└─────────────────────────────────────────────────────────────────────┘

                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    MONITORING & OBSERVABILITY                       │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │ Prometheus   │  │   Grafana    │  │ Alertmanager │             │
│  │              │  │              │  │              │             │
│  │ Metrics      │  │ Dashboards   │  │ Telegram     │             │
│  │ Collection   │  │ Visualization│  │ Alerts       │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Microservices

### 1. Question Selection Service

**Responsibility:** Smart Mix algorithm для выбора следующего вопроса

**Architecture:**
```
QuestionSelectionService (BaseSystem)
├── SmartMixAlgorithm
│   ├── ENTRY: First question (low energy)
│   ├── EXPLORATION: Discover domains
│   ├── DEEPENING: Go deeper into domains
│   └── BALANCING: Energy management
├── QuestionRepository (DB access)
└── EventHandlers (session.created, user.answer.submitted)
```

**Routing Strategies:**
- **ENTRY** (0-1 answers): Low energy, broad domains
- **EXPLORATION** (2-4 answers): Discover user preferences
- **DEEPENING** (5-8 answers): Dive deeper into top domains
- **BALANCING** (9+ answers): Balance energy, avoid fatigue

**Database:**
- Table: `selfology.questions_metadata`
- Indexes: `(domain, depth_level)`, `(energy_dynamics)`

---

### 2. Session Management Service

**Responsibility:** Управление lifecycle онбординга

**Architecture:**
```
SessionManagementService (BaseSystem)
├── SessionRepository (CRUD)
├── TimeoutMonitor (background task)
│   └── Checks every 5 minutes
│       └── Timeout: 30 minutes inactivity
└── EventHandlers (user.onboarding.initiated)
```

**Session States:**
- `active` - In progress
- `paused` - User paused
- `completed` - Finished successfully
- `timeout` - Expired (30 min)

**Database:**
- Table: `selfology.onboarding_sessions`
- Columns: `id, user_id, status, started_at, completed_at, timeout_at`

---

### 3. Analysis Worker Service

**Responsibility:** Dual-phase psychological analysis

**Architecture:**
```
AnalysisWorkerService (BaseSystem)
├── AnalysisEngine
│   ├── analyze_instant (<500ms target)
│   │   ├── Sentiment analysis
│   │   ├── Quality scoring
│   │   └── Brief insight
│   └── analyze_deep (2-10s)
│       ├── Trait extraction (Big Five)
│       ├── Pattern identification
│       └── Comprehensive insights
├── AIRouter
│   ├── Claude Sonnet 4 (10% premium)
│   ├── GPT-4o (75% standard)
│   └── GPT-4o-mini (15% simple)
└── CircuitBreaker (per AI model)
```

**Analysis Phases:**

**Phase 1: Instant Analysis** (parallel to Phase 2)
- Target: <500ms
- Model: GPT-4o-mini
- Purpose: Immediate user feedback
- Output: Sentiment, quality, brief insight

**Phase 2: Deep Analysis** (background)
- Target: 2-10s
- Model: GPT-4o or Claude Sonnet 4
- Purpose: Comprehensive trait extraction
- Output: Big Five traits, patterns, insights

---

### 4. Profile Storage Service

**Responsibility:** Multilayer personality profiles

**Architecture:**
```
ProfileStorageService (BaseSystem)
├── ProfileManager (CRUD)
│   └── Deep merge for nested updates
├── VectorStorageClient (Qdrant)
│   ├── Collection: user_profiles_512d
│   ├── Circuit Breaker protection
│   └── Graceful degradation (DB-only mode)
└── EventHandlers (trait.extracted)
```

**Profile Structure:**
```
personality_profiles (JSONB)
├── big_five (openness, conscientiousness, extraversion, agreeableness, neuroticism)
├── core_dynamics (self_awareness, emotional_regulation, motivation, resilience)
├── adaptive_traits (learning_style, stress_response, decision_pattern)
└── domain_affinities (IDENTITY, EMOTIONS, RELATIONSHIPS, etc.)
```

**Vector Storage:**
- **Qdrant Collection**: `user_profiles_512d`
- **Vector Size**: 512D embeddings
- **Use Case**: Semantic profile search

---

### 5. Trait Evolution Service

**Responsibility:** Отслеживание изменений черт личности

**Architecture:**
```
TraitEvolutionService (BaseSystem)
├── TraitHistoryManager
│   └── Records all trait changes
├── EvolutionAnalyzer
│   ├── detect_pattern (increasing/decreasing/stable/oscillating)
│   ├── calculate_strength (0-1)
│   └── find_significant_changes (threshold: 0.2)
└── EventHandlers (trait.extracted)
```

**Pattern Types:**
- **Increasing**: Trend > +0.15
- **Decreasing**: Trend < -0.15
- **Stable**: Variation < 0.05
- **Oscillating**: StdDev > 0.15

**Database:**
- Table: `selfology.trait_history`
- Columns: `user_id, trait_category, trait_name, old_value, new_value, confidence, trigger, timestamp`

---

### 6. Telegram Gateway Service

**Responsibility:** Pure event-driven gateway (NO business logic)

**Architecture:**
```
TelegramGatewayService (BaseSystem)
├── RateLimiter (Redis sorted sets)
│   └── 30 req/60s per user (sliding window)
├── StateManager (Redis + fallback)
│   ├── Primary: Redis with TTL
│   └── Fallback: In-memory dict
├── Bot (aiogram)
│   ├── Command handlers
│   ├── Message handlers
│   └── Callback handlers
└── CircuitBreaker (Telegram API)
```

**Key Changes from Old Controller:**
- ❌ Removed: OnboardingOrchestrator, QuestionRouter, AnswerAnalyzer
- ✅ Added: Pure event routing, Rate limiting, FSM state management

**FSM States:**
```python
new_user → gdpr_pending → onboarding_active → waiting_for_answer
    → processing_answer → onboarding_complete → chat_active
```

---

### 7. Coach Interaction Service

**Responsibility:** Персонализированный AI коучинг

**Architecture:**
```
CoachInteractionService (BaseSystem)
├── ContextLoader
│   ├── load_user_context (profile + history)
│   └── build_system_prompt (personalized)
├── StyleAdapter
│   └── Adapts tone based on Big Five
├── ConversationManager
│   └── Saves conversation history
└── AIRouter (GPT-4o for coaching)
```

**Personalization Logic:**
```python
if openness > 0.6:
    style = "creative metaphors"
else:
    style = "practical actions"

if conscientiousness > 0.6:
    format = "structured plans"
else:
    format = "flexible guidance"

if extraversion > 0.6:
    tone = "energetic, inspiring"
else:
    tone = "calm, thoughtful"
```

---

### 8. Outbox Relay Service

**Responsibility:** Гарантированная доставка событий

**Architecture:**
```
OutboxRelay
├── Polling (every 1s)
├── Batch Processing (100 events)
├── Event Publishing (Redis Streams)
└── Retry Logic (exponential backoff)
```

**Process:**
1. Poll `selfology.event_outbox WHERE status='pending'` (LIMIT 100)
2. For each event: publish to Redis Stream
3. Mark as `status='published'`
4. On failure: retry with backoff (1s, 2s, 4s, 8s, 16s)

---

## Event Flow

### Complete User Journey

```
1. User: /start
   ↓
2. TelegramGateway → user.onboarding.initiated
   ↓
3. SessionManagement → session.created
   ↓
4. QuestionSelection → question.selected
   ↓
5. TelegramGateway → sends question to user
   ↓
6. User: answers question
   ↓
7. TelegramGateway → user.answer.submitted
   ↓
8. AnalysisWorker → answer.analyzed.instant (320ms)
   ↓
9. TelegramGateway → sends instant feedback
   ↓
10. AnalysisWorker → answer.analyzed.deep (background, 5s)
    ↓
11. AnalysisWorker → trait.extracted
    ↓
12. ProfileStorage → profile.updated
    ↓
13. TraitEvolution → trait.evolution.detected
    ↓
14. QuestionSelection → question.selected (next question)
    ↓
15. Repeat steps 5-14 (3-10 times)
    ↓
16. SessionManagement → session.completed
    ↓
17. User: sends chat message
    ↓
18. CoachInteraction → coach.message.ready
    ↓
19. TelegramGateway → sends coach response
```

**Total Latency:**
- Instant feedback: <500ms (p95)
- Next question ready: <2s (p95)
- Deep analysis: 2-10s (background, non-blocking)

---

## Data Architecture

### PostgreSQL Schema: `selfology`

**Tables:**
```sql
-- Event Outbox (Outbox Pattern)
event_outbox (id, event_type, payload, status, trace_id, created_at, published_at)
  Indexes: (status, created_at), (trace_id)

-- Onboarding
questions_metadata (id, question_id, question_text, domain, depth_level, energy_dynamics)
  Indexes: (domain, depth_level), (energy_dynamics)

onboarding_sessions (id, user_id, status, started_at, completed_at, timeout_at)
  Indexes: (user_id, status), (timeout_at)

user_answers_new (id, user_id, session_id, question_id, answer_text, created_at)
  Indexes: (user_id, session_id), (question_id)

-- Profiles
personality_profiles (id, user_id UNIQUE, profile_data JSONB, created_at, updated_at)
  Indexes: (user_id), GIN(profile_data)

trait_history (id, user_id, trait_category, trait_name, old_value, new_value, confidence, trigger, timestamp)
  Indexes: (user_id, timestamp), (trait_name)

unique_signatures (id, user_id UNIQUE, thinking_style, decision_pattern, energy_rhythm, ...)
  Indexes: (user_id)

-- Conversations
conversations (id, user_id, role, content, created_at)
  Indexes: (user_id, created_at)

-- Insights
insights (id, user_id, insight_type, content, created_at)
  Indexes: (user_id, created_at)
```

### Redis Data Structures

**Event Bus:**
```
Stream: selfology:events
  Consumer Groups: question_selection, session_management, analysis_worker, ...
```

**FSM State:**
```
Key: fsm:state:{user_id}
Value: "onboarding_active"
TTL: 3600s
```

**Rate Limiting:**
```
Key: rate_limit:user:{user_id}
Type: Sorted Set (timestamps as scores)
TTL: 60s
```

### Qdrant Collections

**user_profiles_512d:**
- Vector size: 512D
- Distance: Cosine
- Payload: {user_id, profile_summary, created_at}
- Use case: Similar profile search

---

## Infrastructure

### Production Deployment

**Docker Compose:**
- 8 microservices × 2 slots (blue/green) = 16 containers
- Outbox Relay (critical)
- Prometheus (metrics)
- Grafana (dashboards)
- Alertmanager (notifications)

**Resource Limits:**
```yaml
analysis-worker:
  limits:
    cpus: '1.0'
    memory: 1024M
  reservations:
    cpus: '0.5'
    memory: 512M

other-services:
  limits:
    cpus: '0.5'
    memory: 512M
  reservations:
    cpus: '0.25'
    memory: 256M
```

**Networks:**
- `selfology-network` (internal)
- `n8n-network` (shared services: PostgreSQL, Redis, Qdrant)

---

## Resilience Patterns

### 1. Outbox Pattern

**Problem:** Events lost if service crashes between DB write and event publish

**Solution:**
```python
async with conn.transaction():
    # 1. Save data to DB
    await conn.execute("INSERT INTO user_answers ...")

    # 2. Save event to outbox (same transaction)
    outbox = OutboxPublisher(schema="selfology")
    await outbox.publish(conn, "user.answer.submitted", payload)

# 3. OutboxRelay publishes later (guaranteed)
```

**Benefits:**
- ✅ Atomic (DB + outbox in same transaction)
- ✅ Guaranteed delivery (even if service crashes)
- ✅ No event loss

---

### 2. Circuit Breaker

**Problem:** Cascading failures when external service is down

**Solution:**
```python
class CircuitBreaker:
    states = [CLOSED, OPEN, HALF_OPEN]

    async def call(self, func):
        if self.state == OPEN:
            raise CircuitBreakerOpenError()

        try:
            result = await func()
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise
```

**Applied To:**
- AI API calls (Claude, OpenAI)
- Qdrant vector storage
- Telegram API

**Configuration:**
- Failure threshold: 5
- Timeout: 60s
- Half-open tries: 3

---

### 3. Retry Pattern

**Problem:** Transient failures (network issues, timeouts)

**Solution:**
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(RetryableError)
)
async def call_ai(self, messages):
    # Auto-retries with backoff: 1s, 2s, 4s
    return await self.client.create(messages=messages)
```

**Applied To:**
- AI API calls
- Database queries (timeouts)
- External API calls

---

### 4. AI Fallback Chain

**Problem:** AI model unavailable or fails

**Solution:**
```python
models = [
    (AIModel.CLAUDE_SONNET_4, "premium"),
    (AIModel.GPT4O, "standard"),
    (AIModel.GPT4O_MINI, "fallback")
]

for model, tier in models:
    try:
        with self.circuit_breakers[model]:
            result = await self._call_model(model, messages)
            return result
    except Exception:
        logger.warning(f"{model} failed, trying next...")

raise AllModelsFailed()
```

**Benefits:**
- ✅ High availability (3 fallback levels)
- ✅ Cost optimization (try cheaper models)
- ✅ Graceful degradation

---

## Scalability

### Horizontal Scaling

**Microservices:**
- Each service can scale independently
- Stateless design (state in Redis/PostgreSQL)
- Consumer groups distribute load

**Example:**
```bash
# Scale Analysis Worker to 3 instances
docker-compose up -d --scale analysis-worker-blue=3
```

**Load Distribution:**
- Redis Consumer Groups distribute events
- Each instance processes different events
- No coordination needed

---

### Database Scaling

**Read Replicas:**
```
Master (write) → Replica 1 (read)
              → Replica 2 (read)
```

**Connection Pooling:**
```python
pool = await asyncpg.create_pool(
    min_size=5,
    max_size=20
)
```

---

### Caching Strategy

**Redis Caching:**
- User profiles (TTL: 1 hour)
- FSM state (TTL: 1 hour)
- Question metadata (TTL: 24 hours)

**Cache Invalidation:**
- `profile.updated` → invalidate profile cache
- `state.change.requested` → update FSM state

---

## Performance Targets

### Latency Targets (p95)

- Instant analysis: <500ms ✅
- Question selection: <200ms ✅
- Profile query: <300ms ✅
- Event processing: <200ms ✅
- Chat response: <3s ✅

### Throughput Targets

- 100 concurrent users ✅
- 1000 requests/minute ✅
- 10,000 events/minute ✅

### Availability Targets

- Service uptime: 99.9% (3 nines)
- Zero-downtime deployments ✅
- Automatic failover ✅

---

## Security

### Network Security
- Internal microservices: No authentication (trusted network)
- External APIs: API keys + HTTPS

### Rate Limiting
- 30 requests per 60 seconds (per user)
- Fail-open on Redis error

### Data Privacy
- User data in PostgreSQL (encrypted at rest)
- No PII in logs
- GDPR compliant

---

## Future Enhancements

### Short-term (Q1 2026)
- [ ] Kubernetes deployment
- [ ] Multi-region support
- [ ] GraphQL API gateway
- [ ] Real-time analytics dashboard

### Long-term (Q2-Q4 2026)
- [ ] Machine learning pipeline for trait prediction
- [ ] Voice interaction support
- [ ] Mobile app (React Native)
- [ ] Enterprise SaaS offering

---

**Last Updated:** 2025-10-01
**Version:** 1.0.0
**Maintainer:** Selfology Team
