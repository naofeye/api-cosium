#!/bin/bash
# OptiFlow — Script de deploiement production
set -e

echo "========================================="
echo "  OptiFlow AI — Deploiement Production"
echo "========================================="

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml"
COMPOSE_FILE="docker-compose.yml"  # retro-compat backup step
BACKUP_DIR="runtime/backups"
DEPLOY_BRANCH="${DEPLOY_BRANCH:-main}"

# Pre-flight: verify required env vars
if [ ! -f .env ]; then
    echo "ERREUR: Fichier .env introuvable."
    exit 1
fi

MISSING=""
grep -q "^JWT_SECRET=" .env || MISSING="$MISSING JWT_SECRET"
grep -q "^ENCRYPTION_KEY=" .env || MISSING="$MISSING ENCRYPTION_KEY"

if [ -n "$MISSING" ]; then
    echo "ERREUR: Variables d'environnement manquantes dans .env:$MISSING"
    exit 1
fi

# 0. Backup database before deployment
echo "[0/6] Backup de la base de donnees..."
mkdir -p "$BACKUP_DIR"
if docker compose $COMPOSE_FILES ps postgres 2>/dev/null | grep -q "running"; then
    echo "  Backup en cours..."
    docker compose -f "$COMPOSE_FILE" exec -T postgres \
        pg_dump -U "${POSTGRES_USER:-optiflow}" -Fc "${POSTGRES_DB:-optiflow}" > "${BACKUP_DIR}/optiflow_$(date +%Y%m%d_%H%M%S).dump" 2>/dev/null \
        && echo "  Backup termine." \
        || echo "  WARN: Backup echoue (non bloquant)."
else
    echo "  PostgreSQL non demarre, backup ignore."
fi

# 1. Pull latest code (idempotent : fetch + reset au lieu de pull, evite les conflits merge)
echo "[1/6] Fetch + reset sur $DEPLOY_BRANCH..."
git fetch origin "$DEPLOY_BRANCH"
git reset --hard "origin/$DEPLOY_BRANCH"

# 2. Build images
echo "[2/6] Build des images Docker..."
docker compose $COMPOSE_FILES build

# 3. Run migrations BEFORE switching
echo "[3/6] Demarrage des services..."
docker compose $COMPOSE_FILES up -d

# 4. Wait for API to be healthy (via nginx or direct container check)
echo "[4/6] Attente de l'API..."
for i in $(seq 1 30); do
    # Utiliser docker exec pour tester le healthcheck en interne (pas localhost:8000)
    if docker compose $COMPOSE_FILES exec -T api curl -sf http://localhost:8000/health >/dev/null 2>&1; then
        echo "  API is healthy!"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "  ERREUR: API non disponible apres 60 secondes."
        echo "  Consultez les logs: docker compose $COMPOSE_FILES logs api"
        exit 1
    fi
    echo "  Waiting... ($i/30)"
    sleep 2
done

# 5. Run migrations
echo "[5/6] Migrations Alembic..."
docker compose $COMPOSE_FILES exec -T api alembic upgrade head

# 6. Verify via nginx (port 80)
echo "[6/6] Verification finale..."
if curl -sf http://localhost/health > /dev/null 2>&1; then
    echo "  Health check OK via nginx."
else
    echo "  WARN: Health check via nginx non disponible (verifier nginx)."
fi

echo ""
echo "========================================="
echo "  Deploiement termine avec succes !"
echo "========================================="
docker compose $COMPOSE_FILES ps
