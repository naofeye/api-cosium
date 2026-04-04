#!/bin/bash
# OptiFlow — Restauration de backup PostgreSQL
set -e

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    echo "Example: $0 backups/optiflow_2026-04-04_120000.sql.gz"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Erreur: fichier '$BACKUP_FILE' introuvable."
    exit 1
fi

echo "========================================="
echo "  OptiFlow AI — Restauration Backup"
echo "========================================="
echo "Fichier: $BACKUP_FILE"
echo ""
echo "⚠️  ATTENTION: Cette operation va REMPLACER toute la base de donnees !"
echo "Les donnees actuelles seront perdues."
echo ""
read -p "Tapez 'oui' pour confirmer: " confirm

if [ "$confirm" != "oui" ]; then
    echo "Annule."
    exit 0
fi

echo ""
echo "Restauration en cours..."
gunzip -c "$BACKUP_FILE" | docker compose exec -T postgres psql -U ${POSTGRES_USER:-optiflow} -d ${POSTGRES_DB:-optiflow} 2>&1

echo ""
echo "✅ Restauration terminee."
echo "Redemarrez l'API pour prendre en compte les changements:"
echo "  docker compose restart api"
