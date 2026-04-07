#!/bin/bash
# OptiFlow — Backup de la base de donnees PostgreSQL
set -e

cd "$(dirname "$0")/.."

COMPOSE_FILE="${1:-docker-compose.prod.yml}"
BACKUP_DIR="backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/optiflow_${TIMESTAMP}.dump"

mkdir -p "$BACKUP_DIR"

echo "Backup de la base de donnees..."
echo "  Compose: $COMPOSE_FILE"
echo "  Fichier: $BACKUP_FILE"

if ! docker compose -f "$COMPOSE_FILE" ps postgres 2>/dev/null | grep -q "running"; then
    echo "ERREUR: PostgreSQL n'est pas demarre."
    exit 1
fi

docker compose -f "$COMPOSE_FILE" exec -T postgres \
    pg_dump -U optiflow -Fc optiflow > "$BACKUP_FILE"

SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "Backup termine: $BACKUP_FILE ($SIZE)"

# Supprimer les backups de plus de 30 jours
find "$BACKUP_DIR" -name "optiflow_*.dump" -mtime +30 -delete 2>/dev/null || true
echo "Backups > 30 jours supprimes."
