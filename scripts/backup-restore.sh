#!/bin/bash

# ============================================
# Selfology Backup & Restore Script
# Автоматизация бэкапов и восстановления
# ============================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/home/ksnk/backups/selfology}"
S3_BUCKET="${S3_BUCKET:-s3://selfology-backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
POSTGRES_CONTAINER="n8n-postgres"
POSTGRES_USER="postgres"
POSTGRES_DB="n8n"
REDIS_CONTAINER="n8n-redis"

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
# Create full backup
# ============================================
backup_full() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_name="selfology_full_${timestamp}"
    local backup_path="${BACKUP_DIR}/${backup_name}"

    print_info "Creating full backup: $backup_name"
    mkdir -p "$backup_path"

    # 1. Backup PostgreSQL (all selfology schemas)
    print_info "Backing up PostgreSQL..."
    docker exec "$POSTGRES_CONTAINER" pg_dump \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        -n selfology \
        --format=custom \
        --verbose \
        > "${backup_path}/postgres_selfology.dump"

    if [[ $? -eq 0 ]]; then
        local size=$(du -h "${backup_path}/postgres_selfology.dump" | cut -f1)
        print_success "PostgreSQL backup: ${size}"
    else
        print_error "PostgreSQL backup failed"
        return 1
    fi

    # 2. Backup Redis (Event Bus data)
    print_info "Backing up Redis..."
    docker exec "$REDIS_CONTAINER" redis-cli --rdb /data/dump.rdb SAVE
    docker cp "${REDIS_CONTAINER}:/data/dump.rdb" "${backup_path}/redis.rdb"

    if [[ $? -eq 0 ]]; then
        local size=$(du -h "${backup_path}/redis.rdb" | cut -f1)
        print_success "Redis backup: ${size}"
    else
        print_error "Redis backup failed"
        return 1
    fi

    # 3. Backup Qdrant vectors
    print_info "Backing up Qdrant vectors..."
    docker exec qdrant /bin/sh -c "cd /qdrant/storage && tar czf /tmp/qdrant_backup.tar.gz collections/"
    docker cp qdrant:/tmp/qdrant_backup.tar.gz "${backup_path}/qdrant_vectors.tar.gz"

    if [[ $? -eq 0 ]]; then
        local size=$(du -h "${backup_path}/qdrant_vectors.tar.gz" | cut -f1)
        print_success "Qdrant backup: ${size}"
    else
        print_warning "Qdrant backup failed (non-critical)"
    fi

    # 4. Backup application config
    print_info "Backing up configuration..."
    cp .env "${backup_path}/env_backup" 2>/dev/null || true
    cp -r alembic/versions "${backup_path}/alembic_versions" 2>/dev/null || true

    # 5. Create metadata file
    cat > "${backup_path}/metadata.json" <<EOF
{
    "timestamp": "$timestamp",
    "type": "full",
    "version": "$(git describe --tags --always 2>/dev/null || echo 'unknown')",
    "commit": "$(git rev-parse HEAD 2>/dev/null || echo 'unknown')",
    "hostname": "$(hostname)",
    "created_by": "$(whoami)"
}
EOF

    # 6. Compress backup
    print_info "Compressing backup..."
    tar -czf "${backup_path}.tar.gz" -C "$BACKUP_DIR" "$backup_name"
    rm -rf "$backup_path"

    local total_size=$(du -h "${backup_path}.tar.gz" | cut -f1)
    print_success "Full backup completed: ${backup_path}.tar.gz (${total_size})"

    # 7. Upload to S3 (if configured)
    if command -v aws &> /dev/null && [[ -n "$S3_BUCKET" ]]; then
        print_info "Uploading to S3..."
        aws s3 cp "${backup_path}.tar.gz" "${S3_BUCKET}/${backup_name}.tar.gz"
        print_success "Uploaded to S3"
    fi

    echo "${backup_path}.tar.gz"
}

# ============================================
# Backup only database
# ============================================
backup_database() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="${BACKUP_DIR}/db_backup_${timestamp}.sql.gz"

    mkdir -p "$BACKUP_DIR"

    print_info "Creating database backup..."
    docker exec "$POSTGRES_CONTAINER" pg_dump \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        -n selfology \
        | gzip > "$backup_file"

    if [[ $? -eq 0 ]]; then
        local size=$(du -h "$backup_file" | cut -f1)
        print_success "Database backup: $backup_file (${size})"
        echo "$backup_file"
    else
        print_error "Database backup failed"
        return 1
    fi
}

# ============================================
# Incremental backup (only changed data)
# ============================================
backup_incremental() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_name="selfology_incremental_${timestamp}"
    local backup_path="${BACKUP_DIR}/${backup_name}"
    local last_backup=$(find "$BACKUP_DIR" -name "selfology_full_*.tar.gz" | sort -r | head -1)

    if [[ -z "$last_backup" ]]; then
        print_warning "No full backup found. Creating full backup instead..."
        backup_full
        return
    fi

    print_info "Creating incremental backup (since last full backup)"
    mkdir -p "$backup_path"

    # Get timestamp of last full backup
    local last_timestamp=$(basename "$last_backup" | sed 's/selfology_full_//' | sed 's/.tar.gz//')

    # Backup only changed rows (using created_at/updated_at)
    print_info "Backing up changed data since $last_timestamp..."
    docker exec "$POSTGRES_CONTAINER" psql \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        -c "COPY (SELECT * FROM selfology.users WHERE updated_at > '$(date -d @${last_timestamp:0:8} +%Y-%m-%d)') TO STDOUT" \
        > "${backup_path}/users_incremental.csv"

    # Create metadata
    cat > "${backup_path}/metadata.json" <<EOF
{
    "timestamp": "$timestamp",
    "type": "incremental",
    "base_backup": "$last_backup",
    "version": "$(git describe --tags --always 2>/dev/null || echo 'unknown')"
}
EOF

    tar -czf "${backup_path}.tar.gz" -C "$BACKUP_DIR" "$backup_name"
    rm -rf "$backup_path"

    print_success "Incremental backup completed: ${backup_path}.tar.gz"
}

# ============================================
# Restore from backup
# ============================================
restore_full() {
    local backup_file=$1

    if [[ ! -f "$backup_file" ]]; then
        print_error "Backup file not found: $backup_file"
        return 1
    fi

    print_warning "WARNING: This will overwrite current data!"
    read -p "Continue? (yes/no): " confirm

    if [[ "$confirm" != "yes" ]]; then
        print_info "Restore cancelled"
        return 0
    fi

    local restore_dir=$(mktemp -d)
    print_info "Extracting backup to $restore_dir..."
    tar -xzf "$backup_file" -C "$restore_dir"

    local backup_name=$(basename "$backup_file" .tar.gz)
    local backup_path="${restore_dir}/${backup_name}"

    # 1. Restore PostgreSQL
    if [[ -f "${backup_path}/postgres_selfology.dump" ]]; then
        print_info "Restoring PostgreSQL..."

        # Drop existing schema
        docker exec "$POSTGRES_CONTAINER" psql \
            -U "$POSTGRES_USER" \
            -d "$POSTGRES_DB" \
            -c "DROP SCHEMA IF EXISTS selfology CASCADE;"

        # Restore from dump
        docker exec -i "$POSTGRES_CONTAINER" pg_restore \
            -U "$POSTGRES_USER" \
            -d "$POSTGRES_DB" \
            --verbose \
            < "${backup_path}/postgres_selfology.dump"

        if [[ $? -eq 0 ]]; then
            print_success "PostgreSQL restored"
        else
            print_error "PostgreSQL restore failed"
            rm -rf "$restore_dir"
            return 1
        fi
    fi

    # 2. Restore Redis
    if [[ -f "${backup_path}/redis.rdb" ]]; then
        print_info "Restoring Redis..."

        docker exec "$REDIS_CONTAINER" redis-cli FLUSHALL
        docker cp "${backup_path}/redis.rdb" "${REDIS_CONTAINER}:/data/dump.rdb"
        docker restart "$REDIS_CONTAINER"
        sleep 5

        print_success "Redis restored"
    fi

    # 3. Restore Qdrant
    if [[ -f "${backup_path}/qdrant_vectors.tar.gz" ]]; then
        print_info "Restoring Qdrant vectors..."

        docker cp "${backup_path}/qdrant_vectors.tar.gz" qdrant:/tmp/
        docker exec qdrant /bin/sh -c "cd /qdrant/storage && rm -rf collections && tar xzf /tmp/qdrant_vectors.tar.gz"
        docker restart qdrant
        sleep 10

        print_success "Qdrant restored"
    fi

    # 4. Restore config
    if [[ -f "${backup_path}/env_backup" ]]; then
        print_warning "Backup contains .env file. Restore it manually if needed."
    fi

    rm -rf "$restore_dir"
    print_success "Full restore completed!"
}

# ============================================
# Restore only database
# ============================================
restore_database() {
    local backup_file=$1

    if [[ ! -f "$backup_file" ]]; then
        print_error "Backup file not found: $backup_file"
        return 1
    fi

    print_warning "WARNING: This will overwrite current database!"
    read -p "Continue? (yes/no): " confirm

    if [[ "$confirm" != "yes" ]]; then
        print_info "Restore cancelled"
        return 0
    fi

    print_info "Restoring database..."

    # Drop and recreate schema
    docker exec "$POSTGRES_CONTAINER" psql \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        -c "DROP SCHEMA IF EXISTS selfology CASCADE; CREATE SCHEMA selfology;"

    # Restore
    gunzip -c "$backup_file" | docker exec -i "$POSTGRES_CONTAINER" psql \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB"

    if [[ $? -eq 0 ]]; then
        print_success "Database restored successfully"
    else
        print_error "Database restore failed"
        return 1
    fi
}

# ============================================
# List available backups
# ============================================
list_backups() {
    print_info "Available backups in $BACKUP_DIR:"
    echo ""

    if [[ ! -d "$BACKUP_DIR" ]]; then
        print_warning "Backup directory does not exist"
        return
    fi

    local backups=$(find "$BACKUP_DIR" -name "*.tar.gz" -o -name "*.sql.gz" | sort -r)

    if [[ -z "$backups" ]]; then
        print_warning "No backups found"
        return
    fi

    printf "%-50s %-10s %-15s\n" "Backup Name" "Size" "Date"
    echo "--------------------------------------------------------------------------------"

    while IFS= read -r backup; do
        local name=$(basename "$backup")
        local size=$(du -h "$backup" | cut -f1)
        local date=$(date -r "$backup" "+%Y-%m-%d %H:%M")
        printf "%-50s %-10s %-15s\n" "$name" "$size" "$date"
    done <<< "$backups"

    echo ""
    print_info "Total backups: $(echo "$backups" | wc -l)"
}

# ============================================
# Clean old backups
# ============================================
clean_old_backups() {
    print_info "Cleaning backups older than $RETENTION_DAYS days..."

    if [[ ! -d "$BACKUP_DIR" ]]; then
        print_warning "Backup directory does not exist"
        return
    fi

    local deleted=0
    while IFS= read -r backup; do
        rm -f "$backup"
        print_info "Deleted: $(basename "$backup")"
        ((deleted++))
    done < <(find "$BACKUP_DIR" -name "*.tar.gz" -o -name "*.sql.gz" -mtime +$RETENTION_DAYS)

    if [[ $deleted -eq 0 ]]; then
        print_info "No old backups to clean"
    else
        print_success "Deleted $deleted old backup(s)"
    fi
}

# ============================================
# Verify backup integrity
# ============================================
verify_backup() {
    local backup_file=$1

    if [[ ! -f "$backup_file" ]]; then
        print_error "Backup file not found: $backup_file"
        return 1
    fi

    print_info "Verifying backup integrity: $(basename "$backup_file")"

    # Check if it's a tar.gz
    if [[ "$backup_file" == *.tar.gz ]]; then
        tar -tzf "$backup_file" > /dev/null 2>&1
        if [[ $? -eq 0 ]]; then
            print_success "Backup archive is valid"

            # List contents
            print_info "Contents:"
            tar -tzf "$backup_file"
        else
            print_error "Backup archive is corrupted"
            return 1
        fi
    fi

    # Check if it's a sql.gz
    if [[ "$backup_file" == *.sql.gz ]]; then
        gunzip -t "$backup_file"
        if [[ $? -eq 0 ]]; then
            print_success "Backup is valid"
        else
            print_error "Backup is corrupted"
            return 1
        fi
    fi

    # Check metadata
    if [[ "$backup_file" == *.tar.gz ]]; then
        local temp_dir=$(mktemp -d)
        tar -xzf "$backup_file" -C "$temp_dir"

        local backup_name=$(basename "$backup_file" .tar.gz)
        if [[ -f "${temp_dir}/${backup_name}/metadata.json" ]]; then
            print_info "Metadata:"
            cat "${temp_dir}/${backup_name}/metadata.json"
        fi

        rm -rf "$temp_dir"
    fi

    return 0
}

# ============================================
# Automated backup (cron job)
# ============================================
setup_cron() {
    print_info "Setting up automated backups..."

    local cron_schedule="${1:-0 2 * * *}"  # Default: 2 AM daily
    local script_path="$(realpath "$0")"

    # Create cron job
    local cron_cmd="$cron_schedule $script_path backup-full >> /var/log/selfology-backup.log 2>&1"

    (crontab -l 2>/dev/null | grep -v "$script_path"; echo "$cron_cmd") | crontab -

    print_success "Automated backup scheduled: $cron_schedule"
    print_info "Logs: /var/log/selfology-backup.log"
}

# ============================================
# Main
# ============================================
show_help() {
    cat << EOF
Selfology Backup & Restore Script

Usage: $0 <command> [options]

Commands:
    backup-full              Create full backup (DB + Redis + Qdrant)
    backup-db                Backup only database
    backup-incremental       Create incremental backup
    restore-full <file>      Restore from full backup
    restore-db <file>        Restore only database
    list                     List available backups
    clean                    Remove old backups (older than $RETENTION_DAYS days)
    verify <file>            Verify backup integrity
    setup-cron [schedule]    Setup automated backups (default: 2 AM daily)

Examples:
    $0 backup-full
    $0 restore-full /path/to/backup.tar.gz
    $0 list
    $0 clean
    $0 setup-cron "0 3 * * *"  # 3 AM daily

Environment Variables:
    BACKUP_DIR              Backup directory (default: /home/ksnk/backups/selfology)
    S3_BUCKET               S3 bucket for remote backups (optional)
    RETENTION_DAYS          Days to keep backups (default: 30)

EOF
}

case "${1:-help}" in
    backup-full)
        backup_full
        ;;
    backup-db)
        backup_database
        ;;
    backup-incremental)
        backup_incremental
        ;;
    restore-full)
        restore_full "$2"
        ;;
    restore-db)
        restore_database "$2"
        ;;
    list)
        list_backups
        ;;
    clean)
        clean_old_backups
        ;;
    verify)
        verify_backup "$2"
        ;;
    setup-cron)
        setup_cron "$2"
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
