# DevOps Strategy for Selfology Refactoring

> 9-Week Refactoring Plan - Complete Automation & Monitoring Strategy

**Date:** 2025-09-30
**Duration:** 9 weeks (2025-09-30 to 2025-12-02)
**Goal:** Zero-downtime transition from monolith to 6 microservices

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Infrastructure Architecture](#infrastructure-architecture)
3. [CI/CD Pipeline Strategy](#cicd-pipeline-strategy)
4. [Database Migration Strategy](#database-migration-strategy)
5. [Monitoring & Observability](#monitoring--observability)
6. [Backup & Disaster Recovery](#backup--disaster-recovery)
7. [Blue-Green Deployment](#blue-green-deployment)
8. [Development Workflow](#development-workflow)
9. [Week-by-Week DevOps Tasks](#week-by-week-devops-tasks)
10. [Tools & Technologies](#tools--technologies)

---

## Executive Summary

### Challenges
- Transition from monolith to 6 microservices
- Zero downtime requirement
- Event-driven architecture with Redis Streams
- Multiple environments (dev/staging/production)
- 9-week aggressive timeline

### Solutions
- **Automated CI/CD**: GitHub Actions with multi-stage pipeline
- **Blue-Green Deployment**: Zero-downtime releases
- **Comprehensive Monitoring**: Event Bus + System metrics
- **Automated Backups**: Daily database + vector storage backups
- **Hot Reload Dev**: 2-second restart time for developers

### Success Metrics

| Metric | Before | Target | Current |
|--------|--------|--------|---------|
| Uptime | 95% | 99.9% | TBD |
| Deployment Time | 30 min | <5 min | TBD |
| Test Coverage | 40% | 85%+ | TBD |
| Dev Restart Time | 30 sec | 2 sec | 2 sec ✅ |
| Rollback Time | Manual (hours) | <2 min | TBD |

---

## Infrastructure Architecture

### Current Infrastructure (n8n-enterprise)

**Existing Services** (DO NOT RECREATE):
```yaml
Services:
  - n8n-postgres:5432 (PostgreSQL 15)
  - n8n-redis:6379 (Redis 7)
  - qdrant:6333 (Vector DB)
  - chromadb:8000 (Vector DB)
  - ollama:11434 (Local AI)
  - n8n-main:5678 (Workflows)

Network: docker-compose_n8n-network
```

### Target Architecture (6 Microservices)

```
┌─────────────────────────────────────────────────────────┐
│                    Load Balancer (Nginx)                 │
│                     Port 80/443                          │
└──────────────┬──────────────────────────────────────────┘
               │
    ┌──────────┴──────────────────┐
    │                             │
┌───▼────────────────┐    ┌──────▼───────────────┐
│  Blue Environment  │    │  Green Environment   │
│  (Production)      │    │  (Staging)           │
└───┬────────────────┘    └──────┬───────────────┘
    │                             │
    └──────────┬────────┬─────────┘
               │        │
    ┌──────────▼────────▼─────────────────────┐
    │                                          │
    │       6 Microservices Layer             │
    │                                          │
    │  ┌──────────────────────────────────┐  │
    │  │ 1. Telegram System    :8001      │  │
    │  │ 2. Onboarding System  :8002      │  │
    │  │ 3. Analysis System    :8003      │  │
    │  │ 4. Profile System     :8004      │  │
    │  │ 5. Coach System       :8005      │  │
    │  │ 6. Monitoring System  :9090      │  │
    │  └──────────────────────────────────┘  │
    │                                          │
    └──────────┬───────────────────────────────┘
               │
    ┌──────────▼─────────────────────────────┐
    │                                         │
    │     Event Bus Layer (Redis Streams)    │
    │     - selfology:events                 │
    │     - Event Monitor :8080              │
    │                                         │
    └──────────┬─────────────────────────────┘
               │
    ┌──────────▼─────────────────────────────┐
    │                                         │
    │      Data Layer (Existing n8n)         │
    │      - PostgreSQL (schemas per system) │
    │      - Redis (cache + events)          │
    │      - Qdrant (vectors)                │
    │                                         │
    └─────────────────────────────────────────┘
```

### Port Mapping

| Service | Port | Description |
|---------|------|-------------|
| Telegram System | 8001 | User interface gateway |
| Onboarding System | 8002 | Smart questioning |
| Analysis System | 8003 | AI analysis |
| Profile System | 8004 | Soul Architect |
| Coach System | 8005 | AI coaching |
| Monitoring System | 9090 | Prometheus metrics |
| Grafana Dashboard | 3000 | Visualization |
| Event Bus Monitor | 8080 | Real-time event tracking |

---

## CI/CD Pipeline Strategy

### Pipeline Stages

```
┌─────────────────────────────────────────────────────────┐
│                    CI/CD Pipeline                        │
└─────────────────────────────────────────────────────────┘

Stage 1: Code Quality (5 min)
├── Black formatting check
├── Ruff linting
├── MyPy type checking
├── Bandit security scan
└── Safety dependency scan

Stage 2: Testing (10 min)
├── Unit tests (parallel)
├── Integration tests (with services)
├── E2E tests
└── Coverage report (>85% required)

Stage 3: Database Migrations (5 min)
├── Test migrations (dry-run)
├── Apply to test DB
├── Rollback test
└── Verify schema

Stage 4: Build Docker Images (15 min)
├── Build 6 system images (parallel)
├── Tag with commit SHA
├── Push to registry
└── Sign images

Stage 5: Deploy (Environment-specific)
├── Development: Auto-deploy on 'develop' branch
├── Staging: Auto-deploy after dev success
└── Production: Manual approval + Blue-Green

Stage 6: Post-Deployment
├── Smoke tests
├── Health checks
├── Performance tests
└── Alert on failure
```

### Branch Strategy

```
main (production)
  ├── Protected branch
  ├── Requires PR approval
  ├── All checks must pass
  └── Triggers production deployment

develop (staging)
  ├── Auto-deploys to staging
  ├── Integration testing ground
  └── Merges to main via PR

feature/* (development)
  ├── Created from develop
  ├── CI runs on every push
  ├── Auto-deploys to dev environment
  └── Merged to develop via PR

phase-* (refactoring phases)
  ├── Long-lived feature branches
  ├── Used during 9-week refactoring
  └── Merged to develop when phase complete
```

### Deployment Triggers

| Branch | Trigger | Environment | Approval Required |
|--------|---------|-------------|-------------------|
| feature/* | Push | Dev | No |
| develop | Push | Dev + Staging | No |
| main | Push | Production | Yes |
| phase-* | Push | Dev | No |

---

## Database Migration Strategy

### Zero-Downtime Migrations

**Principles:**
1. Always backward compatible
2. Multi-step migrations for breaking changes
3. Automatic backups before each migration
4. Rollback capability
5. Dry-run testing

**Migration Workflow:**

```bash
# 1. Generate migration
./scripts/migration-manager.sh generate "add user_preferences table"

# 2. Review generated SQL
./scripts/migration-manager.sh dry-run

# 3. Test in development
./scripts/migration-manager.sh apply

# 4. Test rollback
./scripts/migration-manager.sh rollback 1

# 5. Apply in staging (CI/CD)
# Automatic in pipeline

# 6. Apply in production (with backup)
# Automatic in blue-green deployment
```

**Schema Organization:**

```sql
-- Each system has its own schema
selfology.telegram_system
  ├── telegram_users
  └── telegram_fsm_states

selfology.onboarding_system
  ├── onboarding_sessions
  ├── session_answers
  └── questions_metadata

selfology.analysis_system
  ├── analysis_queue
  ├── analysis_results
  └── extracted_traits

selfology.profile_system
  ├── personality_profiles
  ├── trait_history
  └── unique_signatures

selfology.coach_system
  ├── chat_sessions
  ├── chat_messages
  └── generated_insights

selfology.monitoring_system
  ├── system_metrics
  └── alert_history
```

**Critical Migration Rules:**

1. **Add Column** (Safe):
   ```sql
   ALTER TABLE users ADD COLUMN new_field TEXT DEFAULT 'default_value';
   ```

2. **Remove Column** (Multi-step):
   ```sql
   -- Step 1: Make nullable, deploy code that ignores it
   ALTER TABLE users ALTER COLUMN old_field DROP NOT NULL;

   -- Step 2: (Next release) Drop column
   ALTER TABLE users DROP COLUMN old_field;
   ```

3. **Rename Column** (Multi-step):
   ```sql
   -- Step 1: Add new column, copy data
   ALTER TABLE users ADD COLUMN new_name TEXT;
   UPDATE users SET new_name = old_name;

   -- Step 2: (Next release) Drop old column
   ALTER TABLE users DROP COLUMN old_name;
   ```

---

## Monitoring & Observability

### Four Pillars of Observability

#### 1. Metrics (Prometheus + Grafana)

**System Metrics:**
- CPU, Memory, Disk usage per service
- Request rate, error rate, duration (RED metrics)
- Event Bus throughput
- Database connection pool
- Cache hit rates

**Business Metrics:**
- Active users
- Onboarding completion rate
- AI analysis queue length
- Average response time
- Cost per AI call

**Dashboards:**
```
Grafana Dashboard (http://localhost:3000)
├── System Overview
│   ├── Service health
│   ├── Resource usage
│   └── Error rates
├── Event Bus Monitor
│   ├── Event throughput
│   ├── Event lag
│   └── Consumer health
├── AI Performance
│   ├── Model usage
│   ├── API costs
│   └── Response times
└── Business Metrics
    ├── User activity
    ├── Conversion rates
    └── System efficiency
```

#### 2. Logging (Structured + Centralized)

**Log Format:**
```json
{
  "timestamp": "2025-09-30T10:30:45.123Z",
  "level": "INFO",
  "system": "onboarding",
  "trace_id": "abc123-def456",
  "user_id": "12345",
  "event_type": "question.answered",
  "message": "User answered question",
  "context": {
    "question_id": "Q001",
    "domain": "IDENTITY",
    "depth": "CONSCIOUS"
  }
}
```

**Log Aggregation:**
- Each service writes to `/app/logs/<system>/`
- Logs are volume-mounted to host
- Centralized log viewer: `scripts/log_viewer.py`
- Retention: 30 days

#### 3. Distributed Tracing

**Trace ID Propagation:**
```python
# Generated at entry point (Telegram)
trace_id = generate_trace_id()

# Passed through all events
event = {
    "trace_id": trace_id,
    "event_type": "user.answer.submitted",
    "data": {...}
}

# All systems log with trace_id
logger.info("Processing event", extra={"trace_id": trace_id})
```

**Trace Timeline Example:**
```
Trace ID: abc123-def456
├── [00:00.000] Telegram: User sends message
├── [00:00.050] Onboarding: Question selected
├── [00:00.100] Event Bus: Event published
├── [00:01.500] Analysis: AI analysis started
├── [00:08.300] Analysis: AI analysis completed
├── [00:08.350] Profile: Profile updated
└── [00:08.400] Telegram: Response sent
Total: 8.4 seconds
```

#### 4. Alerts (Proactive Monitoring)

**Alert Levels:**
- **CRITICAL**: Immediate action required (page on-call)
- **WARNING**: Monitor closely
- **INFO**: Informational

**Alert Rules:**

```yaml
Critical Alerts:
  - Service down for >2 minutes
  - Error rate >10% for >5 minutes
  - Database connection failures
  - Event Bus lag >10,000 events
  - Disk space <10%

Warning Alerts:
  - Error rate >5% for >10 minutes
  - Response time >5s for >10 minutes
  - Memory usage >80%
  - AI API rate limit approaching

Info Alerts:
  - Deployment completed
  - Migration applied
  - Backup completed
```

**Alert Channels:**
- Telegram notifications
- Webhook to monitoring system
- Email for critical alerts

---

## Backup & Disaster Recovery

### Backup Strategy

**Daily Automated Backups:**
```bash
# Scheduled via cron: 2 AM daily
0 2 * * * /home/ksnk/n8n-enterprise/projects/selfology/scripts/backup-restore.sh backup-full

# What's backed up:
# 1. PostgreSQL (all selfology schemas)
# 2. Redis data (Event Bus state)
# 3. Qdrant vectors (personality data)
# 4. Configuration files
```

**Backup Types:**

| Type | Frequency | Retention | Size Estimate |
|------|-----------|-----------|---------------|
| Full | Daily | 30 days | ~2 GB |
| Incremental | Hourly | 7 days | ~100 MB |
| Pre-migration | Before each migration | 90 days | ~2 GB |
| Pre-deployment | Before production deploy | 90 days | ~2 GB |

**Backup Storage:**
- **Local**: `/home/ksnk/backups/selfology/`
- **Remote**: S3 bucket (optional, configured via `S3_BUCKET` env var)

### Disaster Recovery Plan

**Recovery Time Objectives (RTO):**
- Database failure: **15 minutes**
- Service failure: **5 minutes** (auto-restart)
- Complete system failure: **1 hour**

**Recovery Point Objectives (RPO):**
- Maximum data loss: **1 hour** (last incremental backup)

**DR Procedures:**

1. **Service Failure** (Automatic):
   ```bash
   # Docker restart policy handles this
   restart: unless-stopped
   ```

2. **Database Corruption**:
   ```bash
   # Stop all services
   docker-compose -f docker-compose.microservices.yml down

   # Restore from latest backup
   ./scripts/backup-restore.sh restore-full /path/to/backup.tar.gz

   # Start services
   docker-compose -f docker-compose.microservices.yml up -d
   ```

3. **Complete System Failure**:
   ```bash
   # Restore infrastructure from backup
   # Documented in: DISASTER_RECOVERY.md
   ```

---

## Blue-Green Deployment

### Strategy

**Concept:**
- Two identical environments: Blue (production) and Green (staging)
- Deploy to Green while Blue serves traffic
- Test Green thoroughly
- Switch traffic from Blue to Green
- Keep Blue as instant rollback

**Implementation:**

```bash
# Automated deployment script
./scripts/deploy.sh

# What it does:
# 1. Pre-flight checks
# 2. Database backup
# 3. Run migrations
# 4. Deploy Green environment
# 5. Health checks on Green
# 6. Smoke tests on Green
# 7. Switch traffic to Green (Nginx config)
# 8. Monitor metrics for 5 minutes
# 9. If OK: shut down Blue
# 10. If ERROR: rollback to Blue
```

**Nginx Configuration:**

```nginx
upstream selfology_backend {
    # Initially points to Blue (port 8001)
    server localhost:8001;
}

# During deployment, switches to Green (port 8002)
# After verification, Green becomes new Blue
```

**Rollback:**
```bash
# Automatic rollback if any check fails
# Manual rollback:
./scripts/deploy.sh --rollback

# Rollback time: <2 minutes
```

---

## Development Workflow

### Daily Development Cycle

```bash
# Morning: Start development environment
./dev.sh start

# Watch logs in separate terminal
./dev.sh logs

# Edit code...
# Automatic restart (2 seconds)
# Test in Telegram bot
# Repeat

# Evening: Stop environment
./dev.sh stop
```

### Feature Development Flow

```
1. Create feature branch
   git checkout -b feature/add-new-question-type

2. Make changes (hot reload active)

3. Run tests locally
   pytest tests/

4. Commit & push
   git commit -m "Add new question type"
   git push origin feature/add-new-question-type

5. CI/CD runs automatically
   - Code quality checks
   - Tests
   - Builds Docker image
   - Deploys to dev environment

6. Create PR to develop
   - Review required
   - All checks must pass

7. Merge to develop
   - Auto-deploys to staging

8. Test in staging

9. Create PR to main
   - Final review
   - Deploy to production (blue-green)
```

### Testing Strategy

**Test Pyramid:**
```
        ╱╲
       ╱E2E╲      10% - Full user flows
      ╱────╲
     ╱ Int. ╲     30% - System integration
    ╱────────╲
   ╱   Unit   ╲   60% - Individual functions
  ╱────────────╲
```

**Test Commands:**
```bash
# Unit tests (fast)
pytest tests/unit/ -n auto

# Integration tests (services)
pytest tests/integration/

# E2E tests (full flows)
pytest tests/e2e/

# With coverage
pytest --cov=selfology_bot --cov=systems --cov=core

# Performance tests
k6 run tests/performance/load-test.js
```

---

## Week-by-Week DevOps Tasks

### Week 1 (Phase 0): Foundation
**DevOps Tasks:**
- [x] Hot reload setup (DONE)
- [ ] Event Bus monitoring tool
- [ ] Logging standardization
- [ ] Backup automation setup
- [ ] CI/CD pipeline (basic)

**Deliverables:**
- Event Bus Monitor running at :8080
- Automated daily backups
- Basic GitHub Actions pipeline

### Week 2 (Phase 1): Onboarding System
**DevOps Tasks:**
- [ ] Docker image for Onboarding System
- [ ] Health check endpoints
- [ ] Integration tests for Event Bus
- [ ] Monitoring dashboards

**Deliverables:**
- Onboarding System containerized
- CI pipeline builds and tests system
- Dashboard shows system metrics

### Week 3 (Phase 2): Analysis System
**DevOps Tasks:**
- [ ] Analysis Worker scaling config
- [ ] AI API rate limiting
- [ ] Cost tracking metrics
- [ ] Queue monitoring

**Deliverables:**
- Analysis System + Workers containerized
- Auto-scaling based on queue length
- Cost tracking dashboard

### Week 4 (Phase 3): Profile System
**DevOps Tasks:**
- [ ] Qdrant backup integration
- [ ] Vector index monitoring
- [ ] Profile migration scripts
- [ ] Database schema per system

**Deliverables:**
- Profile System containerized
- Soul-Architect migrations applied
- Vector backups automated

### Week 5 (Phase 4): Telegram System
**DevOps Tasks:**
- [ ] FSM state persistence
- [ ] Webhook vs long-polling config
- [ ] User session monitoring
- [ ] Rate limiting per user

**Deliverables:**
- Telegram System containerized
- Session management robust
- User activity dashboards

### Week 6 (Phase 5): Coach System
**DevOps Tasks:**
- [ ] AI chat session monitoring
- [ ] Context loading performance
- [ ] Conversation history backups
- [ ] Personalization metrics

**Deliverables:**
- Coach System containerized
- Chat performance monitored
- Personalization effectiveness tracked

### Week 7 (Phase 6): Integration
**DevOps Tasks:**
- [ ] Full system integration tests
- [ ] Event flow optimization
- [ ] End-to-end monitoring
- [ ] Documentation complete

**Deliverables:**
- All 6 systems running together
- E2E tests passing
- Complete monitoring stack

### Week 8 (Phase 7): Testing
**DevOps Tasks:**
- [ ] Load testing (100 concurrent users)
- [ ] Chaos engineering tests
- [ ] Performance profiling
- [ ] Security audit

**Deliverables:**
- Load test results
- Chaos test report
- Performance optimization applied
- Security vulnerabilities fixed

### Week 9 (Phase 8): Production Deployment
**DevOps Tasks:**
- [ ] Blue-green deployment setup
- [ ] Production migration plan
- [ ] Rollback procedures tested
- [ ] Monitoring alerts configured

**Deliverables:**
- Production deployment successful
- Zero downtime achieved
- All systems healthy
- Documentation complete

---

## Tools & Technologies

### Infrastructure
- **Docker**: Containerization
- **Docker Compose**: Multi-container orchestration
- **Nginx**: Load balancing, reverse proxy

### CI/CD
- **GitHub Actions**: Automated pipeline
- **Docker Registry**: ghcr.io (GitHub Container Registry)
- **Pytest**: Testing framework
- **k6**: Load testing

### Monitoring
- **Prometheus**: Metrics collection
- **Grafana**: Visualization
- **FastAPI**: Event Bus Monitor web UI
- **Redis**: Event streaming

### Database
- **PostgreSQL**: Primary database
- **Alembic**: Schema migrations
- **pg_dump**: Backups

### Development
- **watchmedo**: Hot reload
- **Black/Ruff**: Code quality
- **MyPy**: Type checking
- **Bandit**: Security scanning

### Observability
- **Structured Logging**: JSON logs
- **Trace ID**: Distributed tracing
- **Custom Metrics**: Business KPIs

---

## Quick Reference

### Essential Commands

```bash
# Development
./dev.sh start              # Start dev environment
./dev.sh logs               # Watch logs
./dev.sh stop               # Stop dev environment

# Deployment
./scripts/deploy.sh         # Blue-green deployment
./scripts/deploy.sh --rollback  # Rollback

# Backups
./scripts/backup-restore.sh backup-full     # Full backup
./scripts/backup-restore.sh restore-full <file>  # Restore
./scripts/backup-restore.sh list            # List backups

# Migrations
./scripts/migration-manager.sh status       # Current status
./scripts/migration-manager.sh generate <msg>  # New migration
./scripts/migration-manager.sh apply        # Apply migrations
./scripts/migration-manager.sh rollback     # Rollback

# Monitoring
# Event Bus: http://localhost:8080
# Grafana: http://localhost:3000
# Prometheus: http://localhost:9090

# Testing
pytest tests/                               # All tests
pytest tests/unit/ -n auto                  # Fast unit tests
k6 run tests/performance/load-test.js       # Load test
```

### Key Files

```
/home/ksnk/n8n-enterprise/projects/selfology/
├── docker-compose.microservices.yml    # All 6 systems
├── docker-compose.dev.yml              # Development
├── .github/workflows/ci-cd-pipeline.yml  # CI/CD
├── scripts/
│   ├── deploy.sh                       # Blue-green deployment
│   ├── backup-restore.sh               # Backup automation
│   ├── migration-manager.sh            # Database migrations
│   └── dev.sh                          # Development helper
├── core/
│   └── event_bus_monitor.py            # Event monitoring
└── DEVOPS_STRATEGY.md                  # This document
```

---

## Success Criteria

### Technical Goals
- [ ] Zero downtime deployment achieved
- [ ] All 6 microservices running independently
- [ ] Event-driven communication functional
- [ ] Test coverage >85%
- [ ] Automated CI/CD pipeline active
- [ ] Monitoring and alerting configured
- [ ] Backup and restore tested

### Performance Goals
- [ ] Deployment time <5 minutes
- [ ] Rollback time <2 minutes
- [ ] Service restart <10 seconds
- [ ] Event processing latency <100ms
- [ ] 99.9% uptime

### Team Goals
- [ ] Documentation complete
- [ ] Team trained on new architecture
- [ ] Runbooks created
- [ ] Incident response procedures defined

---

**Last Updated:** 2025-09-30
**Next Review:** Weekly during refactoring
**Owner:** DevOps Team
