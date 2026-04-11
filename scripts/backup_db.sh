#!/bin/bash
# OptiFlow — Backup de la base de donnees PostgreSQL
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

COMPOSE_FILE="${1:-docker-compose.yml}"
BACKUP_DIR="runtime/backups"
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
    pg_dump -U "${POSTGRES_USER:-optiflow}" -Fc "${POSTGRES_DB:-optiflow}" > "$BACKUP_FILE"

SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "Backup termine: $BACKUP_FILE ($SIZE)"

# Verification de l'integrite du backup
echo "Verification de l'integrite du backup..."
if pg_restore --list "$BACKUP_FILE" > /dev/null 2>&1; then
    echo "Backup valide."
else
    echo "ERREUR: Le backup est corrompu ou invalide: $BACKUP_FILE"
    exit 1
fi

# Supprimer les backups de plus de 90 jours
find "$BACKUP_DIR" -name "optiflow_*.dump" -mtime +90 -delete 2>/dev/null || true
echo "Backups > 90 jours supprimes."
