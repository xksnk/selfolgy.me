#!/bin/bash

# ============================================
# Selfology Blue-Green Deployment Script
# Реализует zero-downtime deployment для Фазы 8
# ============================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
COMPOSE_FILE="docker-compose.microservices.yml"
COMPOSE_FILE_BLUE="docker-compose.blue.yml"
COMPOSE_FILE_GREEN="docker-compose.green.yml"
NGINX_CONF="/etc/nginx/sites-available/selfology"
BACKUP_DIR="/home/ksnk/backups/selfology"
HEALTHCHECK_TIMEOUT=60
ROLLBACK_TIMEOUT=300

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}========================================${NC}"
}

# ============================================
# Pre-flight checks
# ============================================
preflight_checks() {
    print_header "Pre-flight Checks"

    # Check if running as root or with sudo
    if [[ $EUID -eq 0 ]]; then
        print_warning "Running as root. Consider using a non-root user with sudo."
    fi

    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi
    print_success "Docker: $(docker --version)"

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed"
        exit 1
    fi
    print_success "Docker Compose: $(docker-compose --version)"

    # Check disk space (need at least 5GB)
    available_space=$(df -BG . | tail -1 | awk '{print $4}' | sed 's/G//')
    if [[ $available_space -lt 5 ]]; then
        print_error "Not enough disk space. Available: ${available_space}GB, Required: 5GB"
        exit 1
    fi
    print_success "Disk space: ${available_space}GB available"

    # Check if services are running
    if ! docker ps | grep -q "n8n-postgres"; then
        print_error "n8n-postgres is not running. Start it first."
        exit 1
    fi
    print_success "PostgreSQL is running"

    if ! docker ps | grep -q "n8n-redis"; then
        print_error "n8n-redis is not running. Start it first."
        exit 1
    fi
    print_success "Redis is running"

    print_success "All pre-flight checks passed!"
}

# ============================================
# Database backup
# ============================================
backup_database() {
    print_header "Database Backup"

    mkdir -p "$BACKUP_DIR"
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="$BACKUP_DIR/selfology_backup_$TIMESTAMP.sql"

    print_info "Creating database backup..."
    docker exec n8n-postgres pg_dump -U postgres -d n8n -n selfology > "$BACKUP_FILE"

    if [[ -f "$BACKUP_FILE" ]]; then
        BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        print_success "Backup created: $BACKUP_FILE ($BACKUP_SIZE)"

        # Compress backup
        gzip "$BACKUP_FILE"
        print_success "Backup compressed: ${BACKUP_FILE}.gz"

        # Keep only last 7 backups
        print_info "Cleaning old backups (keeping last 7)..."
        ls -t "$BACKUP_DIR"/selfology_backup_*.sql.gz | tail -n +8 | xargs -r rm

        echo "$BACKUP_FILE.gz"
    else
        print_error "Backup failed!"
        exit 1
    fi
}

# ============================================
# Database migrations
# ============================================
run_migrations() {
    print_header "Database Migrations"

    print_info "Running Alembic migrations..."

    # Test migrations in dry-run mode first
    print_info "Testing migrations (dry-run)..."
    docker run --rm \
        --network docker-compose_n8n-network \
        -e DATABASE_URL="postgresql+asyncpg://n8n:${DB_PASSWORD}@n8n-postgres:5432/n8n" \
        -v "$(pwd):/app" \
        python:3.11-slim \
        bash -c "cd /app && pip install -q alembic && alembic upgrade head --sql" > /tmp/migration.sql

    if [[ $? -eq 0 ]]; then
        print_success "Migration SQL generated successfully"
        print_info "Preview of SQL changes:"
        head -n 20 /tmp/migration.sql
    else
        print_error "Migration test failed!"
        exit 1
    fi

    # Apply migrations
    print_info "Applying migrations..."
    docker run --rm \
        --network docker-compose_n8n-network \
        -e DATABASE_URL="postgresql+asyncpg://n8n:${DB_PASSWORD}@n8n-postgres:5432/n8n" \
        -v "$(pwd):/app" \
        python:3.11-slim \
        bash -c "cd /app && pip install -q alembic && alembic upgrade head"

    if [[ $? -eq 0 ]]; then
        print_success "Migrations applied successfully"
    else
        print_error "Migration failed!"
        print_info "Rolling back database..."
        restore_database "$1"
        exit 1
    fi
}

# ============================================
# Restore database from backup
# ============================================
restore_database() {
    local backup_file=$1
    print_header "Database Restore"

    if [[ ! -f "$backup_file" ]]; then
        print_error "Backup file not found: $backup_file"
        exit 1
    fi

    print_warning "Restoring database from backup..."

    # Decompress if needed
    if [[ $backup_file == *.gz ]]; then
        gunzip -c "$backup_file" | docker exec -i n8n-postgres psql -U postgres -d n8n
    else
        cat "$backup_file" | docker exec -i n8n-postgres psql -U postgres -d n8n
    fi

    if [[ $? -eq 0 ]]; then
        print_success "Database restored successfully"
    else
        print_error "Database restore failed!"
        exit 1
    fi
}

# ============================================
# Health check
# ============================================
health_check() {
    local service=$1
    local port=$2
    local max_attempts=$((HEALTHCHECK_TIMEOUT / 5))
    local attempt=1

    print_info "Waiting for $service to be healthy..."

    while [[ $attempt -le $max_attempts ]]; do
        if curl -f -s "http://localhost:$port/health" > /dev/null 2>&1; then
            print_success "$service is healthy!"
            return 0
        fi

        print_info "Attempt $attempt/$max_attempts - waiting for $service..."
        sleep 5
        ((attempt++))
    done

    print_error "$service health check failed after $HEALTHCHECK_TIMEOUT seconds"
    return 1
}

# ============================================
# Smoke tests
# ============================================
run_smoke_tests() {
    local environment=$1
    print_header "Smoke Tests - $environment"

    local base_url="http://localhost"
    if [[ $environment == "green" ]]; then
        base_url="http://localhost:8002"  # Green environment port
    fi

    # Test 1: Telegram System
    print_info "Testing Telegram System..."
    if curl -f -s "${base_url}:8001/health" | grep -q "ok"; then
        print_success "Telegram System: OK"
    else
        print_error "Telegram System: FAILED"
        return 1
    fi

    # Test 2: Event Bus Monitor
    print_info "Testing Event Bus Monitor..."
    if curl -f -s "${base_url}:8080/health" | grep -q "ok"; then
        print_success "Event Bus Monitor: OK"
    else
        print_error "Event Bus Monitor: FAILED"
        return 1
    fi

    # Test 3: Monitoring System
    print_info "Testing Monitoring System..."
    if curl -f -s "${base_url}:9090/-/healthy" > /dev/null 2>&1; then
        print_success "Monitoring System: OK"
    else
        print_warning "Monitoring System: Warning (non-critical)"
    fi

    # Test 4: Database connectivity
    print_info "Testing database connectivity..."
    docker exec n8n-postgres psql -U postgres -d n8n -c "SELECT 1" > /dev/null 2>&1
    if [[ $? -eq 0 ]]; then
        print_success "Database: OK"
    else
        print_error "Database: FAILED"
        return 1
    fi

    # Test 5: Redis connectivity
    print_info "Testing Redis connectivity..."
    docker exec n8n-redis redis-cli ping > /dev/null 2>&1
    if [[ $? -eq 0 ]]; then
        print_success "Redis: OK"
    else
        print_error "Redis: FAILED"
        return 1
    fi

    print_success "All smoke tests passed!"
    return 0
}

# ============================================
# Deploy green environment
# ============================================
deploy_green() {
    print_header "Deploying Green Environment"

    print_info "Pulling latest images..."
    docker-compose -f "$COMPOSE_FILE_GREEN" pull

    print_info "Starting green environment..."
    docker-compose -f "$COMPOSE_FILE_GREEN" up -d

    print_info "Waiting for services to stabilize..."
    sleep 10

    # Health checks
    if ! health_check "telegram-green" 8002; then
        print_error "Green environment health check failed"
        return 1
    fi

    if ! health_check "event-monitor-green" 8082; then
        print_error "Green environment health check failed"
        return 1
    fi

    # Smoke tests
    if ! run_smoke_tests "green"; then
        print_error "Green environment smoke tests failed"
        return 1
    fi

    print_success "Green environment deployed and healthy!"
    return 0
}

# ============================================
# Switch traffic to green
# ============================================
switch_to_green() {
    print_header "Switching Traffic to Green"

    print_info "Updating Nginx configuration..."

    # Backup current config
    cp "$NGINX_CONF" "${NGINX_CONF}.backup"

    # Update upstream to green
    sed -i 's/localhost:8001/localhost:8002/g' "$NGINX_CONF"
    sed -i 's/localhost:8080/localhost:8082/g' "$NGINX_CONF"

    # Test Nginx config
    nginx -t
    if [[ $? -ne 0 ]]; then
        print_error "Nginx configuration test failed"
        # Restore backup
        mv "${NGINX_CONF}.backup" "$NGINX_CONF"
        return 1
    fi

    # Reload Nginx
    systemctl reload nginx
    if [[ $? -eq 0 ]]; then
        print_success "Traffic switched to green environment"
        return 0
    else
        print_error "Failed to reload Nginx"
        mv "${NGINX_CONF}.backup" "$NGINX_CONF"
        return 1
    fi
}

# ============================================
# Monitor metrics
# ============================================
monitor_metrics() {
    print_header "Monitoring Metrics"

    local duration=${1:-300}  # Default 5 minutes
    local interval=10
    local iterations=$((duration / interval))

    print_info "Monitoring for $duration seconds..."

    for i in $(seq 1 $iterations); do
        # Check error rate
        error_count=$(docker logs selfology-telegram-green 2>&1 | grep -c "ERROR")

        # Check response time
        response_time=$(curl -o /dev/null -s -w '%{time_total}' http://localhost:8002/health)

        # Check memory usage
        memory_usage=$(docker stats --no-stream --format "{{.MemPerc}}" selfology-telegram-green | sed 's/%//')

        echo -ne "\rIteration $i/$iterations - Errors: $error_count, Response: ${response_time}s, Memory: ${memory_usage}%   "

        # Alert if error rate is high
        if [[ $error_count -gt 100 ]]; then
            echo ""
            print_error "High error rate detected: $error_count errors"
            return 1
        fi

        # Alert if response time is high
        if (( $(echo "$response_time > 5.0" | bc -l) )); then
            echo ""
            print_error "High response time detected: ${response_time}s"
            return 1
        fi

        # Alert if memory usage is high
        if (( $(echo "$memory_usage > 90" | bc -l) )); then
            echo ""
            print_error "High memory usage detected: ${memory_usage}%"
            return 1
        fi

        sleep $interval
    done

    echo ""
    print_success "Metrics monitoring passed!"
    return 0
}

# ============================================
# Rollback to blue
# ============================================
rollback_to_blue() {
    print_header "Rolling Back to Blue Environment"

    print_warning "Initiating rollback..."

    # Switch traffic back to blue
    print_info "Switching traffic back to blue..."
    mv "${NGINX_CONF}.backup" "$NGINX_CONF" 2>/dev/null || true
    nginx -t && systemctl reload nginx

    # Stop green environment
    print_info "Stopping green environment..."
    docker-compose -f "$COMPOSE_FILE_GREEN" down

    print_success "Rollback completed!"
}

# ============================================
# Complete deployment
# ============================================
complete_deployment() {
    print_header "Completing Deployment"

    # Stop blue environment
    print_info "Stopping blue environment..."
    docker-compose -f "$COMPOSE_FILE_BLUE" down

    # Rename green to blue
    print_info "Promoting green to blue..."
    mv "$COMPOSE_FILE_GREEN" "$COMPOSE_FILE_BLUE"

    # Clean up old images
    print_info "Cleaning up old Docker images..."
    docker system prune -f

    print_success "Deployment completed successfully!"
}

# ============================================
# Main deployment flow
# ============================================
main() {
    print_header "Selfology Blue-Green Deployment"

    local skip_backup=false
    local skip_tests=false

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-backup)
                skip_backup=true
                shift
                ;;
            --skip-tests)
                skip_tests=true
                shift
                ;;
            --rollback)
                rollback_to_blue
                exit 0
                ;;
            --help)
                echo "Usage: $0 [options]"
                echo "Options:"
                echo "  --skip-backup    Skip database backup"
                echo "  --skip-tests     Skip smoke tests"
                echo "  --rollback       Rollback to previous version"
                echo "  --help           Show this help message"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Pre-flight checks
    preflight_checks

    # Backup database
    if [[ $skip_backup == false ]]; then
        backup_file=$(backup_database)
    else
        print_warning "Skipping database backup"
    fi

    # Run migrations
    run_migrations "$backup_file"

    # Deploy green environment
    if ! deploy_green; then
        print_error "Green deployment failed!"
        if [[ $skip_backup == false ]]; then
            restore_database "$backup_file"
        fi
        rollback_to_blue
        exit 1
    fi

    # Run smoke tests
    if [[ $skip_tests == false ]]; then
        if ! run_smoke_tests "green"; then
            print_error "Smoke tests failed!"
            rollback_to_blue
            exit 1
        fi
    else
        print_warning "Skipping smoke tests"
    fi

    # Switch traffic
    if ! switch_to_green; then
        print_error "Traffic switch failed!"
        rollback_to_blue
        exit 1
    fi

    print_success "Traffic switched to green environment!"
    print_info "Monitoring metrics for 5 minutes..."

    # Monitor for 5 minutes
    if ! monitor_metrics 300; then
        print_error "Metrics monitoring failed!"
        print_warning "Initiating automatic rollback..."
        rollback_to_blue
        exit 1
    fi

    # Complete deployment
    complete_deployment

    print_success "========================================="
    print_success "Deployment completed successfully!"
    print_success "========================================="

    print_info "Next steps:"
    print_info "1. Monitor logs: docker-compose logs -f"
    print_info "2. Check metrics: http://localhost:9090"
    print_info "3. View events: http://localhost:8080"
}

# Run main
main "$@"
