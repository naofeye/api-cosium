#!/bin/bash
# OptiFlow — Restauration de la base de donnees PostgreSQL
set -e

cd "$(dirname "$0")/.."

COMPOSE_FILE="${1:-docker-compose.prod.yml}"
BACKUP_FILE="${2}"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: ./scripts/restore_db.sh [compose-file] <backup-file>"
    echo ""
    echo "Backups disponibles:"
    ls -lh backups/optiflow_*.dump 2>/dev/null || echo "  Aucun backup trouve."
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERREUR: Fichier backup introuvable: $BACKUP_FILE"
    exit 1
fi

echo "ATTENTION: Ceci va REMPLACER toutes les donnees de la base."
echo "  Compose: $COMPOSE_FILE"
echo "  Backup: $BACKUP_FILE"
echo ""
read -p "Confirmer la restauration ? (oui/non) " confirm
if [ "$confirm" != "oui" ]; then
    echo "Restauration annulee."
    exit 0
fi

echo "Restauration en cours..."
docker compose -f "$COMPOSE_FILE" exec -T postgres \
    pg_restore -U "${POSTGRES_USER:-optiflow}" -d "${POSTGRES_DB:-optiflow}" --clean --if-exists < "$BACKUP_FILE"

echo "Restauration terminee."
echo "Redemarrer l'API pour appliquer les changements: docker compose -f $COMPOSE_FILE restart api worker"
