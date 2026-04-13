#!/bin/bash
# OptiFlow — Script de rollback production
# Orchestre : stop services -> restore backup BDD -> git reset -> restart
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "========================================="
echo "  OptiFlow — Rollback Production"
echo "========================================="

# Args
COMMIT="${1:-}"
BACKUP="${2:-}"

if [ -z "$COMMIT" ]; then
    echo "Usage: $0 <git-commit-sha> [backup-file]"
    echo ""
    echo "Derniers commits :"
    git log --oneline -10
    echo ""
    echo "Backups disponibles :"
    ls -lh runtime/backups/*.dump 2>/dev/null | tail -10 || echo "  Aucun backup."
    exit 1
fi

# Confirmation
echo "ATTENTION : Rollback vers commit $COMMIT"
echo "  Code : sera reset hard sur $COMMIT"
[ -n "$BACKUP" ] && echo "  BDD  : sera restauree depuis $BACKUP"
[ -z "$BACKUP" ] && echo "  BDD  : NON restauree (code only)"
echo ""
read -p "Confirmer le rollback ? (oui/non) " confirm
if [ "$confirm" != "oui" ]; then
    echo "Rollback annule."
    exit 0
fi

COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml"

# 1. Backup pre-rollback (au cas ou le rollback se passe mal)
PRE_FILE="runtime/backups/pre-rollback_$(date +%Y%m%d_%H%M%S).dump"
echo "[1/5] Backup pre-rollback : $PRE_FILE"
mkdir -p runtime/backups
docker compose $COMPOSE_FILES exec -T postgres \
    pg_dump -U "${POSTGRES_USER:-optiflow}" -Fc "${POSTGRES_DB:-optiflow}" > "$PRE_FILE" \
    || echo "  WARN: backup pre-rollback echoue (continuons)"

# 2. Stop services applicatifs (pas postgres/redis/minio)
echo "[2/5] Stop services (api + worker + beat + web)..."
docker compose $COMPOSE_FILES stop api worker beat web

# 3. Restore BDD si demande
if [ -n "$BACKUP" ]; then
    if [ ! -f "$BACKUP" ]; then
        echo "ERREUR: backup introuvable: $BACKUP"
        exit 1
    fi
    echo "[3/5] Restore BDD depuis $BACKUP..."
    docker compose $COMPOSE_FILES exec -T postgres \
        pg_restore -U "${POSTGRES_USER:-optiflow}" \
                   -d "${POSTGRES_DB:-optiflow}" \
                   --clean --if-exists --no-owner < "$BACKUP"
else
    echo "[3/5] Restore BDD ignore (code only)"
fi

# 4. Reset code
echo "[4/5] Reset code vers $COMMIT..."
git fetch
git reset --hard "$COMMIT"

# 5. Rebuild + restart
echo "[5/5] Rebuild + restart..."
docker compose $COMPOSE_FILES build api worker beat web
docker compose $COMPOSE_FILES up -d

# Wait for API healthy
echo "Waiting for API..."
for i in $(seq 1 30); do
    if docker compose $COMPOSE_FILES exec -T api curl -sf http://localhost:8000/health >/dev/null 2>&1; then
        echo "  API healthy."
        break
    fi
    [ "$i" -eq 30 ] && { echo "ERREUR: API non disponible apres rollback"; exit 1; }
    sleep 2
done

echo ""
echo "========================================="
echo "  Rollback termine avec succes"
echo "========================================="
echo "  Commit actuel : $(git log --oneline -1)"
echo "  Backup pre-rollback : $PRE_FILE"
echo "  Pour annuler ce rollback : $0 <previous-commit> $PRE_FILE"
