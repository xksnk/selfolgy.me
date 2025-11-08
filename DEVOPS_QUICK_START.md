# DevOps Quick Start Guide

> Get started with Selfology DevOps automation in 5 minutes

## Prerequisites

- Docker & Docker Compose installed
- Python 3.11+
- Git
- Access to n8n-enterprise infrastructure

## Quick Start

### 1. Initial Setup (One-time)

```bash
# Check everything is ready
make setup

# Start existing n8n infrastructure (if not running)
cd /home/ksnk/n8n-enterprise
docker-compose up -d

# Return to Selfology
cd /home/ksnk/n8n-enterprise/projects/selfology
```

### 2. Development Workflow

```bash
# Start development environment with hot reload
make dev

# Watch logs in another terminal
make dev-logs

# Make changes to code...
# Files are watched, bot restarts automatically in ~2 seconds

# Run tests
make test

# Check system status
make status

# Stop when done
make dev-stop
```

### 3. Database Operations

```bash
# Check migration status
make db-status

# Generate new migration
make db-generate MSG="add new table"

# Apply migrations
make db-migrate

# Rollback if needed
make db-rollback
```

### 4. Backup & Restore

```bash
# Create full backup
make backup

# List backups
make backup-list

# Restore from backup
make restore FILE=/path/to/backup.tar.gz
```

### 5. Deployment

```bash
# Deploy to development
make deploy-dev

# Deploy to staging
make deploy-staging

# Deploy to production (Blue-Green)
make deploy

# Rollback if needed
make rollback
```

## Common Commands

| Command | Description |
|---------|-------------|
| `make help` | Show all available commands |
| `make status` | Show system status |
| `make health` | Check service health |
| `make logs` | View all logs |
| `make clean` | Clean temporary files |

## Key Files

### Configuration
- `.env` - Environment variables
- `docker-compose.microservices.yml` - All 6 systems
- `docker-compose.dev.yml` - Development setup

### Scripts
- `scripts/deploy.sh` - Blue-green deployment
- `scripts/backup-restore.sh` - Backup automation
- `scripts/migration-manager.sh` - Database migrations
- `dev.sh` - Development helper

### Monitoring
- http://localhost:8080 - Event Bus Monitor
- http://localhost:9090 - Prometheus Metrics
- http://localhost:3000 - Grafana Dashboard

## Development Modes

### Docker Dev (Recommended)
```bash
make dev
# Pros: Full isolation, production-like
# Cons: ~2 second restart
```

### Local Dev (Fastest)
```bash
make local
# Pros: Instant restart, easy debugging
# Cons: Requires local Python setup
```

## Troubleshooting

### Services won't start?
```bash
# Check if n8n services are running
docker ps | grep n8n

# Check network
docker network ls | grep n8n
```

### Hot reload not working?
```bash
# Check dev container logs
make dev-logs

# Look for "Restarting process" messages
```

### Database connection failed?
```bash
# Check PostgreSQL is running
docker exec n8n-postgres psql -U postgres -c "SELECT 1"

# Verify connection string in .env
cat .env | grep DATABASE_URL
```

### Clean start?
```bash
# Stop everything
make clean-all

# Start fresh
make dev
```

## Phase-by-Phase Development

### Week 1: Phase 0 - Foundation
```bash
git checkout -b phase-0-foundation
# Create Event Bus
# Setup monitoring
# CI/CD pipeline
```

### Week 2: Phase 1 - Onboarding System
```bash
git checkout -b phase-1-onboarding
# Build Onboarding System
# Docker image
# Integration tests
```

### Weeks 3-9: Continue...
Follow REFACTORING_PROGRESS.md for detailed tasks.

## Monitoring & Observability

### Event Bus Monitor
```bash
make monitor-events
# Opens http://localhost:8080
# Real-time event stream
# System health metrics
```

### Grafana Dashboards
```bash
make monitor-grafana
# Opens http://localhost:3000
# System metrics
# Business KPIs
```

### Logs
```bash
# All logs
make logs

# Specific system
make logs-telegram
make logs-analysis

# Search logs
grep "ERROR" logs/*/latest.log
```

## Testing Strategy

### Unit Tests (Fast)
```bash
make test-unit
# ~30 seconds
# 60% of tests
```

### Integration Tests
```bash
make test-integration
# ~2 minutes
# 30% of tests
```

### E2E Tests
```bash
make test-e2e
# ~5 minutes
# 10% of tests
```

### Load Tests
```bash
make test-load
# ~20 minutes
# 100 concurrent users
```

## CI/CD Pipeline

### Automatic on Push
- **feature/*** → Runs tests, deploys to dev
- **develop** → Runs tests, deploys to staging
- **main** → Runs tests, requires approval, deploys to production

### Manual Triggers
```bash
# Trigger CI manually
git commit --allow-empty -m "Trigger CI"
git push
```

## Production Deployment

### Blue-Green Strategy
```bash
make deploy

# What happens:
# 1. Backup database
# 2. Run migrations
# 3. Deploy to Green environment
# 4. Health checks on Green
# 5. Switch traffic to Green
# 6. Monitor for 5 minutes
# 7. Shut down Blue (old version)
```

### Rollback
```bash
make rollback
# Instant switch back to previous version
# <2 minute downtime
```

## Best Practices

### Before Committing
```bash
# Format code
make format

# Run quality checks
make quality

# Run tests
make test

# Check status
make status
```

### Daily Workflow
```bash
# Morning
make dev
make dev-logs  # in separate terminal

# Edit code...
# Tests run automatically

# Evening
make dev-stop
make clean
```

### Before Deployment
```bash
# Backup
make backup

# Test migrations
make db-status
make db-migrate  # in dev

# Check health
make health

# Deploy
make deploy
```

## Emergency Procedures

### Service Down
```bash
# Check logs
make logs

# Restart service
make services-restart

# If persistent, rollback
make rollback
```

### Database Issues
```bash
# Restore from backup
make backup-list
make restore FILE=/path/to/latest/backup.tar.gz

# Verify
make db-verify
```

### High Load
```bash
# Check metrics
make monitor-grafana

# Scale analysis workers
docker-compose -f docker-compose.microservices.yml up -d --scale analysis-worker=4
```

## Documentation

- `DEVOPS_STRATEGY.md` - Complete strategy document
- `REFACTORING_PROGRESS.md` - 9-week plan tracking
- `ARCHITECTURE_REFACTORING_PLAN.md` - Technical architecture
- `DEVOPS_GUIDE.md` - Original DevOps guide
- `CLAUDE.md` - Project overview

## Getting Help

### Commands
```bash
make help           # Show all commands
make status         # System status
make health         # Health checks
```

### Logs
```bash
make logs           # All logs
make dev-logs       # Dev logs
make prod-logs      # Production logs
```

### Monitoring
```bash
make monitor-events     # Event Bus
make monitor-grafana    # Grafana
make monitor-metrics    # Prometheus
```

## Next Steps

1. **Run Setup**: `make setup`
2. **Start Dev**: `make dev`
3. **Watch Logs**: `make dev-logs`
4. **Make Changes**: Edit code, auto-reload
5. **Run Tests**: `make test`
6. **Check Progress**: `make phase-status`

## Quick Reference Card

```bash
# Start
make dev              # Development
make prod-start       # Production

# Monitor
make status           # System status
make health           # Health checks
make logs             # View logs

# Database
make db-status        # Migration status
make db-migrate       # Apply migrations
make backup           # Create backup

# Deploy
make deploy-dev       # To development
make deploy-staging   # To staging
make deploy           # To production

# Test
make test             # All tests
make test-unit        # Fast tests
make test-load        # Load test

# Stop
make dev-stop         # Development
make prod-stop        # Production
make clean-all        # Complete cleanup
```

---

**Ready to start?**

```bash
make setup && make dev
```

🚀 Happy coding!
