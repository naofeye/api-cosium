#!/bin/bash
# OptiFlow — Backup PostgreSQL avec rotation (7 jours)
set -e

BACKUP_DIR="/opt/optiflow/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/optiflow_${DATE}.sql.gz"
RETENTION_DAYS=7

mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting backup..."
docker compose -f docker-compose.prod.yml exec -T postgres \
    pg_dump -U "${POSTGRES_USER:-optiflow}" "${POSTGRES_DB:-optiflow}" \
    | gzip > "$BACKUP_FILE"

echo "[$(date)] Backup created: $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"

# Rotation: supprimer les backups de plus de 7 jours
find "$BACKUP_DIR" -name "optiflow_*.sql.gz" -mtime +${RETENTION_DAYS} -delete
echo "[$(date)] Old backups cleaned (retention: ${RETENTION_DAYS} days)"

REMAINING=$(find "$BACKUP_DIR" -name "optiflow_*.sql.gz" | wc -l)
echo "[$(date)] Backups remaining: $REMAINING"
