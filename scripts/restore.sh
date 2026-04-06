#!/bin/bash
# OptiFlow — Restore Script (PostgreSQL)
# Usage: ./scripts/restore.sh backups/db_YYYYMMDD_HHMMSS.sql.gz
set -e

BACKUP_FILE="$1"
POSTGRES_USER="${POSTGRES_USER:-optiflow}"
POSTGRES_DB="${POSTGRES_DB:-optiflow}"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    echo "Example: $0 backups/db_20260405_120000.sql.gz"
    echo ""
    echo "Available backups:"
    ls -lht backups/db_*.sql.gz 2>/dev/null || echo "  (aucun backup trouve)"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Erreur: fichier '$BACKUP_FILE' introuvable."
    exit 1
fi

echo "========================================="
echo "  OptiFlow AI — Restauration Backup"
echo "========================================="
echo "Fichier : $BACKUP_FILE"
echo "Taille  : $(du -h "$BACKUP_FILE" | cut -f1)"
echo ""
echo "ATTENTION: Cette operation va REMPLACER toute la base de donnees !"
echo "Les donnees actuelles seront perdues."
echo ""
read -p "Tapez 'oui' pour confirmer: " confirm

if [ "$confirm" != "oui" ]; then
    echo "Annule."
    exit 0
fi

echo ""
echo "[$(date)] Restauration en cours..."
gunzip -c "$BACKUP_FILE" | docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" 2>&1

echo ""
echo "[$(date)] Restauration terminee depuis $BACKUP_FILE"
echo "Redemarrez l'API pour prendre en compte les changements:"
echo "  docker compose restart api"
