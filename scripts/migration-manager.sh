#!/bin/bash

# ============================================
# Alembic Migration Manager for Selfology
# Zero-downtime database migrations
# ============================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
POSTGRES_CONTAINER="n8n-postgres"
POSTGRES_USER="postgres"
POSTGRES_DB="n8n"
ALEMBIC_DIR="alembic"
BACKUP_DIR="/home/ksnk/backups/selfology/migrations"

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# ============================================
# Check Alembic setup
# ============================================
check_setup() {
    print_info "Checking Alembic setup..."

    if [[ ! -d "$ALEMBIC_DIR" ]]; then
        print_error "Alembic directory not found: $ALEMBIC_DIR"
        exit 1
    fi

    if [[ ! -f "alembic.ini" ]]; then
        print_error "alembic.ini not found"
        exit 1
    fi

    # Check if database is accessible
    docker exec "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1" > /dev/null 2>&1
    if [[ $? -ne 0 ]]; then
        print_error "Cannot connect to database"
        exit 1
    fi

    print_success "Alembic setup OK"
}

# ============================================
# Create backup before migration
# ============================================
backup_before_migration() {
    print_info "Creating backup before migration..."

    mkdir -p "$BACKUP_DIR"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="${BACKUP_DIR}/pre_migration_${timestamp}.sql.gz"

    docker exec "$POSTGRES_CONTAINER" pg_dump \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        -n selfology \
        | gzip > "$backup_file"

    if [[ $? -eq 0 ]]; then
        print_success "Backup created: $backup_file"
        echo "$backup_file"
    else
        print_error "Backup failed"
        exit 1
    fi
}

# ============================================
# Show current migration status
# ============================================
migration_status() {
    print_info "Current migration status:"
    echo ""

    alembic current -v

    echo ""
    print_info "Available migrations:"
    alembic history
}

# ============================================
# Generate new migration
# ============================================
generate_migration() {
    local message=$1

    if [[ -z "$message" ]]; then
        print_error "Migration message is required"
        echo "Usage: $0 generate <message>"
        exit 1
    fi

    print_info "Generating migration: $message"

    # Auto-detect changes
    alembic revision --autogenerate -m "$message"

    if [[ $? -eq 0 ]]; then
        print_success "Migration generated successfully"

        # Show the new migration file
        local latest_migration=$(ls -t alembic/versions/*.py | head -1)
        print_info "Created: $latest_migration"

        print_warning "Review the migration file before applying!"
        print_info "Edit: $latest_migration"
    else
        print_error "Migration generation failed"
        exit 1
    fi
}

# ============================================
# Dry-run migration (generate SQL without applying)
# ============================================
dry_run_migration() {
    local target=${1:-head}

    print_info "Dry-run migration to: $target"
    echo ""

    alembic upgrade "$target" --sql

    echo ""
    print_info "This is a dry-run. No changes were applied."
}

# ============================================
# Apply migration with safety checks
# ============================================
apply_migration() {
    local target=${1:-head}

    print_warning "This will apply migrations to: $target"
    echo ""

    # Show what will be done
    print_info "Preview of changes:"
    alembic upgrade "$target" --sql | head -50
    echo ""

    # Confirm
    read -p "Continue with migration? (yes/no): " confirm
    if [[ "$confirm" != "yes" ]]; then
        print_info "Migration cancelled"
        exit 0
    fi

    # Create backup
    local backup_file=$(backup_before_migration)

    # Apply migration
    print_info "Applying migration..."
    alembic upgrade "$target"

    if [[ $? -eq 0 ]]; then
        print_success "Migration applied successfully!"

        # Verify schema
        print_info "Verifying schema..."
        verify_schema

        print_success "All done! Backup saved at: $backup_file"
    else
        print_error "Migration failed!"
        print_warning "Rolling back..."

        # Automatic rollback
        rollback_migration 1

        print_info "Backup is available at: $backup_file"
        exit 1
    fi
}

# ============================================
# Rollback migration
# ============================================
rollback_migration() {
    local steps=${1:-1}

    print_warning "Rolling back $steps migration(s)..."

    # Show current state
    print_info "Current version:"
    alembic current

    # Confirm
    read -p "Continue with rollback? (yes/no): " confirm
    if [[ "$confirm" != "yes" ]]; then
        print_info "Rollback cancelled"
        exit 0
    fi

    # Create backup before rollback
    local backup_file=$(backup_before_migration)

    # Rollback
    alembic downgrade "-$steps"

    if [[ $? -eq 0 ]]; then
        print_success "Rollback completed"
        print_info "New version:"
        alembic current
    else
        print_error "Rollback failed!"
        exit 1
    fi
}

# ============================================
# Verify database schema
# ============================================
verify_schema() {
    print_info "Verifying database schema..."

    # Check if critical tables exist
    local tables=(
        "selfology.users"
        "selfology.onboarding_sessions"
        "selfology.user_answers_new"
        "selfology.questions_metadata"
    )

    local all_ok=true
    for table in "${tables[@]}"; do
        docker exec "$POSTGRES_CONTAINER" psql \
            -U "$POSTGRES_USER" \
            -d "$POSTGRES_DB" \
            -c "SELECT 1 FROM $table LIMIT 1" > /dev/null 2>&1

        if [[ $? -eq 0 ]]; then
            print_success "Table exists: $table"
        else
            print_warning "Table missing: $table"
            all_ok=false
        fi
    done

    if [[ $all_ok == true ]]; then
        print_success "Schema verification passed"
        return 0
    else
        print_warning "Schema verification completed with warnings"
        return 1
    fi
}

# ============================================
# Compare schemas (current vs target)
# ============================================
compare_schemas() {
    print_info "Comparing current schema with models..."

    # Generate a test migration to see differences
    alembic revision --autogenerate -m "schema_check" > /tmp/schema_diff.txt 2>&1

    if grep -q "No changes" /tmp/schema_diff.txt; then
        print_success "Database schema is in sync with models"
        # Remove the test migration
        rm -f $(ls -t alembic/versions/*.py | head -1)
    else
        print_warning "Schema differences detected:"
        cat /tmp/schema_diff.txt

        echo ""
        print_info "A test migration was created. Review it at:"
        ls -t alembic/versions/*.py | head -1

        print_warning "Delete it if not needed, or apply with: $0 apply"
    fi
}

# ============================================
# Stamp database (mark as migrated without running)
# ============================================
stamp_database() {
    local revision=${1:-head}

    print_warning "This will mark the database as migrated to: $revision"
    print_warning "Use this only if migrations were applied manually"
    echo ""

    read -p "Continue? (yes/no): " confirm
    if [[ "$confirm" != "yes" ]]; then
        print_info "Cancelled"
        exit 0
    fi

    alembic stamp "$revision"

    if [[ $? -eq 0 ]]; then
        print_success "Database stamped to: $revision"
    else
        print_error "Stamp failed"
        exit 1
    fi
}

# ============================================
# Show migration SQL
# ============================================
show_sql() {
    local target=${1:-head}

    print_info "SQL for migration to: $target"
    echo ""

    alembic upgrade "$target" --sql
}

# ============================================
# Initialize Alembic (first time setup)
# ============================================
init_alembic() {
    print_info "Initializing Alembic..."

    if [[ -d "$ALEMBIC_DIR" ]]; then
        print_warning "Alembic directory already exists"
        read -p "Reinitialize? (yes/no): " confirm
        if [[ "$confirm" != "yes" ]]; then
            exit 0
        fi
        rm -rf "$ALEMBIC_DIR"
    fi

    alembic init "$ALEMBIC_DIR"

    print_success "Alembic initialized!"
    print_info "Next steps:"
    print_info "1. Edit alembic.ini with your database URL"
    print_info "2. Run: $0 generate 'initial migration'"
    print_info "3. Run: $0 apply"
}

# ============================================
# List all migrations
# ============================================
list_migrations() {
    print_info "All migrations:"
    echo ""

    alembic history --verbose

    echo ""
    print_info "Migration files:"
    ls -lh alembic/versions/*.py 2>/dev/null || echo "No migrations found"
}

# ============================================
# Help
# ============================================
show_help() {
    cat << EOF
Alembic Migration Manager for Selfology

Usage: $0 <command> [options]

Commands:
    status                      Show current migration status
    generate <message>          Generate new migration
    dry-run [target]           Show SQL without applying (default: head)
    apply [target]             Apply migrations (default: head)
    rollback [steps]           Rollback N migrations (default: 1)
    verify                     Verify database schema
    compare                    Compare schema with models
    stamp <revision>           Mark database as migrated to revision
    sql [target]               Show SQL for migration
    list                       List all migrations
    init                       Initialize Alembic (first time)
    help                       Show this help

Examples:
    $0 status
    $0 generate "add user preferences table"
    $0 dry-run
    $0 apply
    $0 rollback 2
    $0 verify

Safety Features:
    - Automatic backup before each migration
    - Dry-run to preview changes
    - Schema verification after migration
    - Rollback support

Backup Location:
    $BACKUP_DIR

EOF
}

# ============================================
# Main
# ============================================
case "${1:-help}" in
    status)
        check_setup
        migration_status
        ;;
    generate)
        check_setup
        generate_migration "$2"
        ;;
    dry-run)
        check_setup
        dry_run_migration "$2"
        ;;
    apply)
        check_setup
        apply_migration "$2"
        ;;
    rollback)
        check_setup
        rollback_migration "$2"
        ;;
    verify)
        check_setup
        verify_schema
        ;;
    compare)
        check_setup
        compare_schemas
        ;;
    stamp)
        check_setup
        stamp_database "$2"
        ;;
    sql)
        check_setup
        show_sql "$2"
        ;;
    list)
        check_setup
        list_migrations
        ;;
    init)
        init_alembic
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
