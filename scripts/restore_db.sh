#!/bin/bash
# OptiFlow — Restauration de la base de donnees PostgreSQL
# Options : --dry-run (verifie sans restaurer), --no-pre-backup (skip backup pre-restore)
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

DRY_RUN=0
PRE_BACKUP=1
POSITIONAL=()
while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run) DRY_RUN=1; shift ;;
        --no-pre-backup) PRE_BACKUP=0; shift ;;
        -h|--help)
            echo "Usage: ./scripts/restore_db.sh [--dry-run] [--no-pre-backup] [compose-file] <backup-file>"
            exit 0 ;;
        *) POSITIONAL+=("$1"); shift ;;
    esac
done
set -- "${POSITIONAL[@]}"

COMPOSE_FILE="${1:-docker-compose.yml}"
BACKUP_FILE="${2}"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: ./scripts/restore_db.sh [--dry-run] [--no-pre-backup] [compose-file] <backup-file>"
    echo ""
    echo "Backups disponibles:"
    ls -lh runtime/backups/optiflow_*.dump 2>/dev/null || echo "  Aucun backup trouve."
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERREUR: Fichier backup introuvable: $BACKUP_FILE"
    exit 1
fi

# Verification d'integrite avant restore
echo "[1/4] Verification du backup..."
if ! pg_restore --list "$BACKUP_FILE" > /dev/null 2>&1; then
    echo "ERREUR: backup corrompu ou format invalide: $BACKUP_FILE"
    exit 1
fi
ITEMS=$(pg_restore --list "$BACKUP_FILE" 2>/dev/null | grep -c "^[0-9]" || echo "0")
SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "  OK ($ITEMS items, $SIZE)"

if [ "$DRY_RUN" -eq 1 ]; then
    echo ""
    echo "[DRY-RUN] Aucune modification effectuee."
    echo "Pour restaurer reellement: $0 $@"
    exit 0
fi

echo ""
echo "ATTENTION: Ceci va REMPLACER toutes les donnees de la base."
echo "  Compose: $COMPOSE_FILE"
echo "  Backup: $BACKUP_FILE"
echo ""
read -p "Confirmer la restauration ? (oui/non) " confirm
if [ "$confirm" != "oui" ]; then
    echo "Restauration annulee."
    exit 0
fi

# Pre-restore backup (filet de securite)
if [ "$PRE_BACKUP" -eq 1 ]; then
    PRE_FILE="runtime/backups/pre-restore_$(date +%Y%m%d_%H%M%S).dump"
    echo "[2/4] Backup pre-restore: $PRE_FILE"
    if docker compose -f "$COMPOSE_FILE" exec -T postgres \
        pg_dump -U "${POSTGRES_USER:-optiflow}" -Fc "${POSTGRES_DB:-optiflow}" > "$PRE_FILE" 2>/dev/null; then
        echo "  OK ($(du -h "$PRE_FILE" | cut -f1))"
    else
        echo "  WARN: backup pre-restore echoue, on continue (--no-pre-backup pour skip silencieux)"
    fi
fi

echo "[3/4] Restauration en cours..."
if docker compose -f "$COMPOSE_FILE" exec -T postgres \
    pg_restore -U "${POSTGRES_USER:-optiflow}" -d "${POSTGRES_DB:-optiflow}" --clean --if-exists --no-owner < "$BACKUP_FILE"; then
    echo "  OK"
else
    echo "ERREUR: La restauration a echoue (exit code $?)."
    [ "$PRE_BACKUP" -eq 1 ] && echo "  Pour rollback: $0 $COMPOSE_FILE $PRE_FILE"
    exit 1
fi

echo "[4/4] Restauration terminee."
echo "Redemarrer pour appliquer: docker compose -f $COMPOSE_FILE restart api worker"
