# Selfology Operations Runbook

> **For:** DevOps Engineers, SREs, On-Call Engineers
> **Version:** 1.0.0
> **Last Updated:** 2025-10-01

---

## Table of Contents

1. [Overview](#overview)
2. [Daily Operations](#daily-operations)
3. [Deployment Procedures](#deployment-procedures)
4. [Incident Response](#incident-response)
5. [Common Issues](#common-issues)
6. [Emergency Contacts](#emergency-contacts)
7. [Runbook Checklist](#runbook-checklist)

---

## Overview

This runbook provides operational procedures for managing Selfology microservices in production.

**Key Contacts:**
- **On-Call Engineer:** @oncall-engineer
- **DevOps Team:** @devops-team
- **Telegram Alerts:** Selfology Alerts Channel

**Production URLs:**
- **Prometheus:** http://n8n-server:9090
- **Grafana:** http://n8n-server:3001
- **Alertmanager:** http://n8n-server:9093

---

## Daily Operations

### Morning Checks (09:00 Daily)

#### 1. Check System Health

```bash
# All services status
./deployment/blue-green-deploy.sh status

# Expected output:
# Active Slot:   blue
# Inactive Slot: green
#
# BLUE SLOT SERVICES:
#   question-selection-blue:      healthy
#   session-management-blue:      healthy
#   ...
```

#### 2. Check Grafana Dashboards

Visit: http://n8n-server:3001

**Dashboards to check:**
- ✅ Selfology Overview (all services)
- ✅ Event Bus Health (pending events <100)
- ✅ AI Router Costs ($10-20/day expected)
- ✅ Error Rates (<1% expected)

#### 3. Check Pending Events

```bash
# SSH to server
ssh user@n8n-server

# Check outbox
docker exec -it n8n-postgres psql -U n8n -d n8n -c "
  SELECT status, COUNT(*)
  FROM selfology.event_outbox
  GROUP BY status;
"

# Expected output:
#  status   | count
# ----------+-------
#  pending  |     5    <- Should be < 100
#  published| 15234
```

**Action if pending > 1000:**
- Check OutboxRelay logs: `docker logs selfology-outbox-relay-blue`
- Verify Redis connection
- Restart OutboxRelay if needed

#### 4. Review Overnight Alerts

```bash
# Check Alertmanager
curl -s http://localhost:9093/api/v2/alerts | jq '.'

# Or visit: http://n8n-server:9093
```

**Action on alerts:**
- Critical alerts: Investigate immediately
- Warning alerts: Add to today's task list
- Resolved alerts: Document in log

---

### Weekly Maintenance (Monday 10:00)

#### 1. Database Cleanup

```bash
# Archive old events (> 30 days)
docker exec -it n8n-postgres psql -U n8n -d n8n -c "
  DELETE FROM selfology.event_outbox
  WHERE status = 'published'
  AND published_at < NOW() - INTERVAL '30 days';
"

# Vacuum tables
docker exec -it n8n-postgres psql -U n8n -d n8n -c "
  VACUUM ANALYZE selfology.event_outbox;
  VACUUM ANALYZE selfology.personality_profiles;
  VACUUM ANALYZE selfology.trait_history;
"
```

#### 2. Redis Memory Check

```bash
# Check Redis memory
docker exec -it n8n-redis redis-cli INFO memory

# Check for high memory usage (>80%)
```

**Action if memory > 80%:**
```bash
# Flush old keys (if safe)
docker exec -it n8n-redis redis-cli FLUSHDB

# Or increase Redis memory limit
```

#### 3. Review AI Costs

```bash
# Check last 7 days AI costs
curl -s 'http://localhost:9090/api/v1/query?query=sum(increase(ai_cost_usd_total[7d]))' | jq '.data.result[0].value[1]'

# Expected: $70-140 per week
```

#### 4. Update Metrics Dashboard

Visit Grafana and review:
- User onboarding completion rate (should be >50%)
- Average analysis latency (should be <500ms p95)
- Event processing throughput

---

## Deployment Procedures

### Standard Deployment (Blue-Green)

**Frequency:** As needed (features, bugfixes)
**Downtime:** Zero
**Duration:** ~10-15 minutes

#### Pre-Deployment Checklist

- [ ] Code reviewed and merged to `main`
- [ ] All tests passing (unit + integration + E2E)
- [ ] Changelog updated
- [ ] Team notified in Slack
- [ ] Backup created

#### Deployment Steps

**Step 1: Create Backup**

```bash
cd /home/ksnk/n8n-enterprise/projects/selfology

# Database backup
docker exec n8n-postgres pg_dump -U n8n -d n8n -n selfology > backups/selfology_$(date +%Y%m%d_%H%M%S).sql

# Verify backup
ls -lh backups/
```

**Step 2: Deploy to Inactive Slot**

```bash
# Check current active slot
./deployment/blue-green-deploy.sh status

# Deploy new version (example: v1.2.0)
export VERSION=1.2.0
./deployment/blue-green-deploy.sh deploy v1.2.0

# Expected output:
# 🚀 Starting Blue-Green deployment...
# Version: v1.2.0
# Active slot: blue
# Target slot: green
#
# Starting services in green slot...
#   Starting question-selection-green...
#   Starting session-management-green...
#   ...
#
# Waiting for all services to become healthy...
#   ✅ question-selection-green is healthy
#   ✅ session-management-green is healthy
#   ...
#
# Running smoke tests on green slot...
#   ✅ Service response check passed
#   ✅ Database connectivity passed
#   ✅ Redis connectivity passed
#   ✅ Event bus check passed
#
# ✅ Deployment to green slot completed successfully
# Run './deployment/blue-green-deploy.sh switch' to switch traffic
```

**Step 3: Verify New Deployment**

```bash
# Manual smoke tests on green slot
# (Depends on load balancer configuration)

# Check logs
docker logs selfology-analysis-worker-green --tail 50

# Check health endpoints
curl http://localhost:8000/health  # (if exposed)
```

**Step 4: Switch Traffic**

```bash
./deployment/blue-green-deploy.sh switch

# Expected output:
# Switching traffic from blue to green...
# Final health check before switching...
#   ✅ All services in green slot are healthy
#
# ✅ Traffic switched to green slot
# Old slot (blue) will remain running for 5 minutes for rollback capability
```

**Step 5: Monitor New Deployment**

```bash
# Watch Grafana for 10 minutes
# - Error rates should remain stable
# - Latency should not increase
# - Event processing should continue

# Check recent errors
curl -s 'http://localhost:9090/api/v1/query?query=rate(http_requests_total{status=~"5.."}[5m])' | jq '.'
```

**Step 6: Cleanup Old Slot** (After 10 min successful monitoring)

```bash
./deployment/blue-green-deploy.sh cleanup

# Expected output:
# Cleaning up inactive slot (blue)...
#   Stopping question-selection-blue...
#   Stopping session-management-blue...
#   ...
#   Removing question-selection-blue...
#   ...
# ✅ Cleanup completed
```

#### Post-Deployment Checklist

- [ ] All services healthy in Grafana
- [ ] Error rate < 1%
- [ ] Latency within SLA (p95 < 500ms)
- [ ] Event processing backlog < 100
- [ ] Team notified: "Deployment v1.2.0 successful"

---

### Emergency Rollback

**When to rollback:**
- Error rate > 5%
- Critical functionality broken
- Performance degradation (latency > 2x normal)

**Rollback Steps:**

```bash
# Immediate rollback
./deployment/blue-green-deploy.sh rollback

# Expected output:
# ⚠️  Rolling back from green to blue...
# Checking if blue slot services are still running...
#   ✅ All services in blue slot are available
#
# Switching traffic back to blue...
# ✅ Rollback completed - traffic switched back to blue
```

**Post-Rollback:**
1. Investigate issue in logs
2. Document root cause
3. Fix issue before re-deploying
4. Notify team

---

## Incident Response

### Severity Levels

**P0 - Critical (Page immediately)**
- Service completely down
- Data loss risk
- Security breach

**P1 - High (Respond within 15 min)**
- Major feature broken
- Error rate > 10%
- Performance severely degraded

**P2 - Medium (Respond within 1 hour)**
- Minor feature broken
- Error rate 5-10%
- Non-critical alerts

**P3 - Low (Respond next business day)**
- Cosmetic issues
- Enhancement requests

---

### P0: Service Down

**Symptoms:**
- Alertmanager: "ServiceDown" alert
- Users cannot use bot
- Grafana shows service unavailable

**Response Steps:**

**1. Acknowledge Alert**
```bash
# Acknowledge in Alertmanager
# Send message to team: "P0 incident: [service] down - investigating"
```

**2. Check Service Logs**
```bash
# Example: analysis-worker down
docker logs selfology-analysis-worker-blue --tail 100

# Look for:
# - Crash stack traces
# - Out of memory errors
# - Connection errors (DB, Redis, AI APIs)
```

**3. Quick Fixes (Try in order)**

**Fix A: Restart Service**
```bash
docker restart selfology-analysis-worker-blue

# Wait 30s, check health
docker ps | grep analysis-worker
docker logs selfology-analysis-worker-blue --tail 20
```

**Fix B: Check Dependencies**
```bash
# Check PostgreSQL
docker exec -it n8n-postgres psql -U n8n -d n8n -c "SELECT 1;"

# Check Redis
docker exec -it n8n-redis redis-cli PING

# Check Qdrant
curl http://localhost:6333/health
```

**Fix C: Rollback to Previous Version**
```bash
./deployment/blue-green-deploy.sh rollback
```

**4. Document Incident**
```bash
# Create incident report
cat > incidents/$(date +%Y%m%d_%H%M%S)_service_down.md <<EOF
# Incident: Analysis Worker Down

**Time:** $(date)
**Severity:** P0
**Impact:** Users unable to get analysis

## Root Cause
[Fill in after investigation]

## Resolution
[What fixed it]

## Prevention
[How to prevent in future]
EOF
```

---

### P1: High Error Rate

**Symptoms:**
- Alertmanager: "HighErrorRate" alert
- Grafana shows error rate > 10%
- Users experiencing failures

**Response Steps:**

**1. Identify Failing Endpoint**
```bash
# Query Prometheus for error breakdown
curl -s 'http://localhost:9090/api/v1/query?query=sum(rate(http_requests_total{status=~"5.."}[5m])) by (service,endpoint)' | jq '.data.result'
```

**2. Check Recent Deployments**
```bash
# Was there a recent deployment?
git log --oneline -10

# If yes: rollback immediately
./deployment/blue-green-deploy.sh rollback
```

**3. Check AI APIs**
```bash
# Check AI Router Circuit Breaker status
curl -s 'http://localhost:9090/api/v1/query?query=circuit_breaker_state' | jq '.data.result'

# If circuit breaker open: wait for recovery or check AI API status
```

**4. Scale Service (If Load Issue)**
```bash
# Example: scale analysis-worker to 3 instances
docker-compose -f deployment/docker-compose.production.yml up -d --scale analysis-worker-blue=3
```

---

### P1: Event Processing Backlog

**Symptoms:**
- Alertmanager: "EventProcessingBacklog" alert
- Grafana shows pending events > 1000
- Users not receiving responses

**Response Steps:**

**1. Check OutboxRelay**
```bash
# Check OutboxRelay logs
docker logs selfology-outbox-relay-blue --tail 100

# Look for:
# - Redis connection errors
# - Event publishing failures
# - Exception stack traces
```

**2. Check Redis**
```bash
# Check Redis connection
docker exec -it n8n-redis redis-cli PING

# Check stream length
docker exec -it n8n-redis redis-cli XLEN selfology:events

# If stream too long (>10000): check consumers
docker exec -it n8n-redis redis-cli XINFO GROUPS selfology:events
```

**3. Restart OutboxRelay**
```bash
docker restart selfology-outbox-relay-blue

# Monitor logs
docker logs -f selfology-outbox-relay-blue
```

**4. Manual Event Processing (Last Resort)**
```bash
# Check oldest pending events
docker exec -it n8n-postgres psql -U n8n -d n8n -c "
  SELECT id, event_type, created_at
  FROM selfology.event_outbox
  WHERE status = 'pending'
  ORDER BY created_at
  LIMIT 10;
"

# If critical, manually republish
# (Use OutboxRelay restart instead)
```

---

## Common Issues

### Issue 1: Instant Analysis Slow (>500ms)

**Symptoms:**
- Alertmanager: "InstantAnalysisSlow"
- Users complaining about delays

**Diagnosis:**
```bash
# Check AI Router metrics
curl -s 'http://localhost:9090/api/v1/query?query=histogram_quantile(0.95, rate(instant_analysis_duration_seconds_bucket[5m]))' | jq '.data.result[0].value[1]'
```

**Possible Causes:**
1. AI API slow/overloaded
2. Database queries slow
3. High load on service

**Solutions:**

**A: Check AI API latency**
```bash
# Check OpenAI status
curl https://status.openai.com/api/v2/status.json

# Switch to different model temporarily
# (Modify AIRouter configuration)
```

**B: Check database**
```bash
# Check slow queries
docker exec -it n8n-postgres psql -U n8n -d n8n -c "
  SELECT pid, now() - query_start AS duration, query
  FROM pg_stat_activity
  WHERE state = 'active'
  AND now() - query_start > interval '5 seconds'
  ORDER BY duration DESC;
"
```

**C: Scale service**
```bash
docker-compose up -d --scale analysis-worker-blue=3
```

---

### Issue 2: Redis Connection Lost

**Symptoms:**
- Services showing "redis": "unhealthy"
- FSM state lost (users reset)
- Rate limiting not working

**Diagnosis:**
```bash
# Check Redis status
docker ps | grep n8n-redis

# Check Redis logs
docker logs n8n-redis --tail 100
```

**Solutions:**

**A: Restart Redis**
```bash
docker restart n8n-redis

# Wait 10s for services to reconnect
```

**B: Check Redis memory**
```bash
docker exec -it n8n-redis redis-cli INFO memory

# If maxmemory reached:
docker exec -it n8n-redis redis-cli CONFIG SET maxmemory 2gb
```

**C: FSM Fallback**
- Services automatically fall back to in-memory state
- No action needed, will sync when Redis returns

---

### Issue 3: AI Costs Too High

**Symptoms:**
- Alertmanager: "HighAICost" (>$10/hour)
- Monthly bill higher than expected

**Diagnosis:**
```bash
# Check costs breakdown by model
curl -s 'http://localhost:9090/api/v1/query?query=sum(increase(ai_cost_usd_total[24h])) by (model)' | jq '.data.result'
```

**Solutions:**

**A: Check model distribution**
```bash
# Should be: 75% GPT-4o, 15% Mini, 10% Claude
# If Claude usage > 20%: investigate why

# Check AI Router logs
docker logs selfology-analysis-worker-blue | grep "Model selected"
```

**B: Increase Mini usage**
- Modify AI Router thresholds
- Route more simple tasks to GPT-4o-mini

**C: Enable caching**
- Implement response caching for common questions
- Cache trait extractions (if safe)

---

### Issue 4: Database Disk Full

**Symptoms:**
- Alertmanager: "DatabaseDiskSpaceLow" (>85%)
- Queries failing with disk full errors

**Diagnosis:**
```bash
# Check disk usage
docker exec -it n8n-postgres df -h

# Check table sizes
docker exec -it n8n-postgres psql -U n8n -d n8n -c "
  SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
  FROM pg_tables
  WHERE schemaname = 'selfology'
  ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
  LIMIT 10;
"
```

**Solutions:**

**A: Archive old data**
```bash
# Archive old events (>90 days)
docker exec -it n8n-postgres psql -U n8n -d n8n -c "
  DELETE FROM selfology.event_outbox
  WHERE status = 'published'
  AND published_at < NOW() - INTERVAL '90 days';
"

# Vacuum
docker exec -it n8n-postgres psql -U n8n -d n8n -c "
  VACUUM FULL selfology.event_outbox;
"
```

**B: Increase disk size** (if on cloud)
- Resize volume in cloud provider
- No downtime needed

---

## Emergency Contacts

### On-Call Rotation

**Primary On-Call:** +1-XXX-XXX-XXXX
**Secondary On-Call:** +1-XXX-XXX-XXXX

**Escalation Path:**
1. Primary On-Call (respond within 15 min)
2. Secondary On-Call (if no response in 30 min)
3. Engineering Manager (P0 only)

### External Vendors

**OpenAI Support:** support@openai.com
**Anthropic Support:** support@anthropic.com
**Telegram Support:** @BotSupport

---

## Runbook Checklist

### Daily Checklist

- [ ] Check system health (`status` command)
- [ ] Review Grafana dashboards
- [ ] Check pending events (<100)
- [ ] Review overnight alerts
- [ ] Check error logs

### Weekly Checklist

- [ ] Database cleanup (archive old events)
- [ ] Redis memory check
- [ ] Review AI costs
- [ ] Update metrics dashboard
- [ ] Review incident reports

### Monthly Checklist

- [ ] Review and update runbook
- [ ] Review SLA compliance (99.9% uptime)
- [ ] Cost optimization review
- [ ] Disaster recovery drill
- [ ] Security audit

---

**Last Updated:** 2025-10-01
**Version:** 1.0.0
**Maintainer:** Selfology DevOps Team

---

**Remember:** When in doubt, **rollback first**, investigate later. User experience is priority #1.
