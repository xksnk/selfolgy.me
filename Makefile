# Selfology Makefile - DevOps Automation
# Quick commands for common operations

.PHONY: help dev prod test backup deploy clean

# Default target
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m

##@ General

help: ## Display this help
	@echo ""
	@echo "$(BLUE)Selfology DevOps Commands$(NC)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make $(GREEN)<target>$(NC)\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(BLUE)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
	@echo ""

##@ Development

dev: ## Start development environment with hot reload
	@echo "$(GREEN)Starting dev environment...$(NC)"
	./dev.sh start

dev-logs: ## Watch development logs
	@echo "$(BLUE)Watching logs...$(NC)"
	./dev.sh logs

dev-stop: ## Stop development environment
	@echo "$(YELLOW)Stopping dev environment...$(NC)"
	./dev.sh stop

dev-restart: ## Restart development environment
	@echo "$(YELLOW)Restarting dev environment...$(NC)"
	./dev.sh restart

dev-shell: ## Enter development container shell
	@echo "$(BLUE)Opening shell...$(NC)"
	./dev.sh shell

dev-clean: ## Clean development environment
	@echo "$(RED)Cleaning dev environment...$(NC)"
	./dev.sh clean

local: ## Run locally without Docker (fastest)
	@echo "$(GREEN)Starting local environment...$(NC)"
	./run-local.sh

##@ Testing

test: ## Run all tests
	@echo "$(BLUE)Running all tests...$(NC)"
	pytest tests/ -v

test-unit: ## Run unit tests only
	@echo "$(BLUE)Running unit tests...$(NC)"
	pytest tests/unit/ -v -n auto

test-integration: ## Run integration tests
	@echo "$(BLUE)Running integration tests...$(NC)"
	pytest tests/integration/ -v

test-e2e: ## Run end-to-end tests
	@echo "$(BLUE)Running E2E tests...$(NC)"
	pytest tests/e2e/ -v

test-coverage: ## Run tests with coverage report
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	pytest tests/ --cov=selfology_bot --cov=systems --cov=core --cov-report=html --cov-report=term

test-load: ## Run load tests with k6
	@echo "$(YELLOW)Running load tests (this will take ~20 minutes)...$(NC)"
	k6 run tests/performance/load-test.js

##@ Database

db-status: ## Show database migration status
	@echo "$(BLUE)Database migration status:$(NC)"
	./scripts/migration-manager.sh status

db-migrate: ## Apply database migrations
	@echo "$(YELLOW)Applying migrations...$(NC)"
	./scripts/migration-manager.sh apply

db-rollback: ## Rollback last migration
	@echo "$(RED)Rolling back migration...$(NC)"
	./scripts/migration-manager.sh rollback

db-generate: ## Generate new migration (usage: make db-generate MSG="description")
	@if [ -z "$(MSG)" ]; then \
		echo "$(RED)Error: MSG is required$(NC)"; \
		echo "Usage: make db-generate MSG=\"add user preferences table\""; \
		exit 1; \
	fi
	@echo "$(GREEN)Generating migration: $(MSG)$(NC)"
	./scripts/migration-manager.sh generate "$(MSG)"

db-verify: ## Verify database schema
	@echo "$(BLUE)Verifying schema...$(NC)"
	./scripts/migration-manager.sh verify

##@ Backup & Restore

backup: ## Create full backup
	@echo "$(GREEN)Creating full backup...$(NC)"
	./scripts/backup-restore.sh backup-full

backup-db: ## Create database-only backup
	@echo "$(GREEN)Creating database backup...$(NC)"
	./scripts/backup-restore.sh backup-db

backup-list: ## List all backups
	@echo "$(BLUE)Available backups:$(NC)"
	./scripts/backup-restore.sh list

backup-clean: ## Remove old backups
	@echo "$(YELLOW)Cleaning old backups...$(NC)"
	./scripts/backup-restore.sh clean

restore: ## Restore from backup (usage: make restore FILE=/path/to/backup.tar.gz)
	@if [ -z "$(FILE)" ]; then \
		echo "$(RED)Error: FILE is required$(NC)"; \
		echo "Usage: make restore FILE=/path/to/backup.tar.gz"; \
		exit 1; \
	fi
	@echo "$(RED)Restoring from: $(FILE)$(NC)"
	./scripts/backup-restore.sh restore-full "$(FILE)"

##@ Deployment

deploy: ## Deploy to production (Blue-Green)
	@echo "$(YELLOW)Starting Blue-Green deployment...$(NC)"
	@echo "$(RED)WARNING: This will deploy to PRODUCTION!$(NC)"
	@read -p "Continue? (yes/no): " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		./scripts/deploy.sh; \
	else \
		echo "$(BLUE)Deployment cancelled$(NC)"; \
	fi

deploy-dev: ## Deploy to development
	@echo "$(GREEN)Deploying to development...$(NC)"
	docker-compose -f docker-compose.dev.yml up -d --build

deploy-staging: ## Deploy to staging
	@echo "$(GREEN)Deploying to staging...$(NC)"
	docker-compose -f docker-compose.microservices.yml up -d --build

rollback: ## Rollback production deployment
	@echo "$(RED)Rolling back production deployment...$(NC)"
	./scripts/deploy.sh --rollback

##@ Monitoring

monitor-events: ## Open Event Bus Monitor
	@echo "$(BLUE)Event Bus Monitor: http://localhost:8080$(NC)"
	@if command -v xdg-open > /dev/null; then \
		xdg-open http://localhost:8080; \
	elif command -v open > /dev/null; then \
		open http://localhost:8080; \
	fi

monitor-grafana: ## Open Grafana Dashboard
	@echo "$(BLUE)Grafana: http://localhost:3000$(NC)"
	@if command -v xdg-open > /dev/null; then \
		xdg-open http://localhost:3000; \
	elif command -v open > /dev/null; then \
		open http://localhost:3000; \
	fi

monitor-metrics: ## Open Prometheus
	@echo "$(BLUE)Prometheus: http://localhost:9090$(NC)"
	@if command -v xdg-open > /dev/null; then \
		xdg-open http://localhost:9090; \
	elif command -v open > /dev/null; then \
		open http://localhost:9090; \
	fi

logs: ## View all container logs
	@echo "$(BLUE)Viewing logs...$(NC)"
	docker-compose -f docker-compose.microservices.yml logs -f

logs-telegram: ## View Telegram System logs
	@echo "$(BLUE)Viewing Telegram System logs...$(NC)"
	docker-compose -f docker-compose.microservices.yml logs -f telegram-system

logs-analysis: ## View Analysis System logs
	@echo "$(BLUE)Viewing Analysis System logs...$(NC)"
	docker-compose -f docker-compose.microservices.yml logs -f analysis-system

##@ Production

prod-start: ## Start production services
	@echo "$(GREEN)Starting production services...$(NC)"
	docker-compose -f docker-compose.selfology.yml up -d

prod-stop: ## Stop production services
	@echo "$(YELLOW)Stopping production services...$(NC)"
	docker-compose -f docker-compose.selfology.yml down

prod-logs: ## View production logs
	@echo "$(BLUE)Viewing production logs...$(NC)"
	docker-compose -f docker-compose.selfology.yml logs -f

prod-status: ## Check production status
	@echo "$(BLUE)Production status:$(NC)"
	docker-compose -f docker-compose.selfology.yml ps

##@ Microservices

services-start: ## Start all microservices
	@echo "$(GREEN)Starting all microservices...$(NC)"
	docker-compose -f docker-compose.microservices.yml up -d

services-stop: ## Stop all microservices
	@echo "$(YELLOW)Stopping all microservices...$(NC)"
	docker-compose -f docker-compose.microservices.yml down

services-restart: ## Restart all microservices
	@echo "$(YELLOW)Restarting all microservices...$(NC)"
	docker-compose -f docker-compose.microservices.yml restart

services-status: ## Check microservices status
	@echo "$(BLUE)Microservices status:$(NC)"
	docker-compose -f docker-compose.microservices.yml ps

services-logs: ## View microservices logs
	@echo "$(BLUE)Viewing microservices logs...$(NC)"
	docker-compose -f docker-compose.microservices.yml logs -f

##@ Code Quality

lint: ## Run linters
	@echo "$(BLUE)Running linters...$(NC)"
	black --check selfology_bot/ systems/ core/
	ruff check selfology_bot/ systems/ core/

format: ## Format code
	@echo "$(GREEN)Formatting code...$(NC)"
	black selfology_bot/ systems/ core/

type-check: ## Run type checking
	@echo "$(BLUE)Running type checking...$(NC)"
	mypy selfology_bot/ systems/ core/ --ignore-missing-imports

security-scan: ## Run security scan
	@echo "$(BLUE)Running security scan...$(NC)"
	bandit -r selfology_bot/ systems/ core/

quality: lint type-check security-scan ## Run all quality checks

##@ Cleanup

clean: ## Clean temporary files
	@echo "$(YELLOW)Cleaning temporary files...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete
	@echo "$(GREEN)Cleanup complete!$(NC)"

clean-all: clean ## Clean everything including Docker
	@echo "$(RED)Cleaning Docker resources...$(NC)"
	docker-compose -f docker-compose.dev.yml down -v --remove-orphans
	docker-compose -f docker-compose.microservices.yml down -v --remove-orphans
	docker system prune -f
	@echo "$(GREEN)Full cleanup complete!$(NC)"

##@ Documentation

docs: ## Generate documentation
	@echo "$(BLUE)Generating documentation...$(NC)"
	@echo "Documentation files:"
	@ls -1 *.md

docs-open: ## Open main documentation
	@echo "$(BLUE)Opening documentation...$(NC)"
	@if command -v xdg-open > /dev/null; then \
		xdg-open DEVOPS_STRATEGY.md; \
	elif command -v open > /dev/null; then \
		open DEVOPS_STRATEGY.md; \
	fi

##@ Utilities

status: ## Show system status
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(GREEN)Selfology System Status$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@echo "$(YELLOW)Docker Containers:$(NC)"
	@docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "selfology|n8n-postgres|n8n-redis|qdrant" || echo "No containers running"
	@echo ""
	@echo "$(YELLOW)Database Status:$(NC)"
	@docker exec n8n-postgres psql -U postgres -d n8n -c "SELECT schemaname, count(*) as tables FROM pg_tables WHERE schemaname = 'selfology' GROUP BY schemaname;" 2>/dev/null || echo "Database not accessible"
	@echo ""
	@echo "$(YELLOW)Disk Usage:$(NC)"
	@df -h . | tail -1
	@echo ""
	@echo "$(YELLOW)Last Backup:$(NC)"
	@ls -t /home/ksnk/backups/selfology/*.tar.gz 2>/dev/null | head -1 || echo "No backups found"
	@echo ""
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"

health: ## Check system health
	@echo "$(BLUE)Checking system health...$(NC)"
	@echo ""
	@echo "$(YELLOW)Telegram System:$(NC)"
	@curl -sf http://localhost:8001/health && echo " ✅ OK" || echo " ❌ DOWN"
	@echo ""
	@echo "$(YELLOW)Event Bus Monitor:$(NC)"
	@curl -sf http://localhost:8080/health && echo " ✅ OK" || echo " ❌ DOWN"
	@echo ""
	@echo "$(YELLOW)Monitoring System:$(NC)"
	@curl -sf http://localhost:9090/-/healthy && echo " ✅ OK" || echo " ❌ DOWN"
	@echo ""

setup: ## Initial setup (run once)
	@echo "$(GREEN)Setting up Selfology...$(NC)"
	@echo ""
	@echo "1. Checking dependencies..."
	@command -v docker >/dev/null 2>&1 || (echo "$(RED)Docker not found!$(NC)" && exit 1)
	@command -v docker-compose >/dev/null 2>&1 || (echo "$(RED)Docker Compose not found!$(NC)" && exit 1)
	@command -v python3 >/dev/null 2>&1 || (echo "$(RED)Python3 not found!$(NC)" && exit 1)
	@echo "   ✅ All dependencies found"
	@echo ""
	@echo "2. Creating directories..."
	@mkdir -p logs backups
	@echo "   ✅ Directories created"
	@echo ""
	@echo "3. Setting permissions..."
	@chmod +x scripts/*.sh dev.sh run-local.sh
	@echo "   ✅ Permissions set"
	@echo ""
	@echo "4. Checking .env file..."
	@test -f .env || (echo "$(RED).env file not found!$(NC)" && exit 1)
	@echo "   ✅ .env file exists"
	@echo ""
	@echo "$(GREEN)Setup complete! Ready to start.$(NC)"
	@echo ""
	@echo "Next steps:"
	@echo "  make dev        - Start development"
	@echo "  make test       - Run tests"
	@echo "  make status     - Check system status"

##@ Phase Management (9-Week Refactoring)

phase-0: ## Start Phase 0: Foundation
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(GREEN)Phase 0: Foundation (Week 1)$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo ""
	@echo "Tasks:"
	@echo "  - Create Event Bus on Redis Streams"
	@echo "  - Define Domain Events"
	@echo "  - Create BaseSystem interface"
	@echo "  - Setup Event Bus monitoring"
	@echo ""
	@echo "Run: git checkout -b phase-0-foundation"

phase-status: ## Show refactoring progress
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(GREEN)Selfology Refactoring Progress$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@cat REFACTORING_PROGRESS.md | grep -A 3 "## 📊 ОБЩИЙ ПРОГРЕСС"
	@echo ""
	@echo "For full progress: cat REFACTORING_PROGRESS.md"

.PHONY: dev dev-logs dev-stop dev-restart dev-shell dev-clean local
.PHONY: test test-unit test-integration test-e2e test-coverage test-load
.PHONY: db-status db-migrate db-rollback db-generate db-verify
.PHONY: backup backup-db backup-list backup-clean restore
.PHONY: deploy deploy-dev deploy-staging rollback
.PHONY: monitor-events monitor-grafana monitor-metrics logs
.PHONY: prod-start prod-stop prod-logs prod-status
.PHONY: services-start services-stop services-restart services-status services-logs
.PHONY: lint format type-check security-scan quality
.PHONY: clean clean-all
.PHONY: docs docs-open
.PHONY: status health setup
.PHONY: phase-0 phase-status
