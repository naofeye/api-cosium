#!/bin/bash
# OptiFlow — Full Backup Script (PostgreSQL + MinIO)
# Usage: ./scripts/backup.sh
set -e

BACKUP_DIR="${BACKUP_DIR:-./backups}"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS="${RETENTION_DAYS:-30}"
POSTGRES_USER="${POSTGRES_USER:-optiflow}"
POSTGRES_DB="${POSTGRES_DB:-optiflow}"

mkdir -p "$BACKUP_DIR"

echo "[$(date)] === OptiFlow Backup ==="

# ---- PostgreSQL backup ----
echo "[$(date)] Backing up PostgreSQL..."
DB_FILE="$BACKUP_DIR/db_${DATE}.sql"
docker compose exec -T postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > "$DB_FILE"
gzip "$DB_FILE"
echo "[$(date)] PostgreSQL backup: ${DB_FILE}.gz ($(du -h "${DB_FILE}.gz" | cut -f1))"

# ---- MinIO backup (optional) ----
if docker compose ps minio 2>/dev/null | grep -q "running"; then
    echo "[$(date)] Backing up MinIO data..."
    MINIO_DIR="$BACKUP_DIR/minio_${DATE}"
    mkdir -p "$MINIO_DIR"
    # Copy MinIO data volume content via a temporary container
    docker compose exec -T minio sh -c "cd /data && tar cf - ." > "$MINIO_DIR/minio_data.tar" 2>/dev/null || true
    if [ -s "$MINIO_DIR/minio_data.tar" ]; then
        gzip "$MINIO_DIR/minio_data.tar"
        echo "[$(date)] MinIO backup: $MINIO_DIR/minio_data.tar.gz"
    else
        rm -rf "$MINIO_DIR"
        echo "[$(date)] MinIO backup skipped (empty or unavailable)"
    fi
else
    echo "[$(date)] MinIO not running — skipping MinIO backup"
fi

# ---- Retention: delete old backups ----
echo "[$(date)] Cleaning backups older than ${RETENTION_DAYS} days..."
find "$BACKUP_DIR" -name "db_*.sql.gz" -mtime +${RETENTION_DAYS} -delete 2>/dev/null || true
find "$BACKUP_DIR" -name "minio_*.tar.gz" -mtime +${RETENTION_DAYS} -delete 2>/dev/null || true
find "$BACKUP_DIR" -type d -name "minio_*" -empty -delete 2>/dev/null || true

REMAINING=$(find "$BACKUP_DIR" -name "db_*.sql.gz" 2>/dev/null | wc -l)
echo "[$(date)] Backup complete. DB backups remaining: $REMAINING"
