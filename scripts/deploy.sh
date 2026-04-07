#!/bin/bash
# OptiFlow — Script de deploiement production
set -e

echo "========================================="
echo "  OptiFlow AI — Deploiement Production"
echo "========================================="

cd "$(dirname "$0")/.."

COMPOSE_FILE="docker-compose.prod.yml"

# 0. Backup database before deployment
echo "[0/6] Backup de la base de donnees..."
if docker compose -f "$COMPOSE_FILE" ps postgres 2>/dev/null | grep -q "running"; then
    echo "  Backup en cours..."
    docker compose -f "$COMPOSE_FILE" exec -T postgres \
        pg_dump -U optiflow -Fc optiflow > "backups/optiflow_$(date +%Y%m%d_%H%M%S).dump" 2>/dev/null \
        && echo "  Backup termine." \
        || echo "  WARN: Backup echoue (non bloquant)."
else
    echo "  PostgreSQL non demarre, backup ignore."
fi

# 1. Pull latest code
echo "[1/6] Pull du code..."
git pull origin main

# 2. Build images
echo "[2/6] Build des images Docker..."
docker compose -f "$COMPOSE_FILE" build

# 3. Run migrations BEFORE switching
echo "[3/6] Demarrage des services..."
docker compose -f "$COMPOSE_FILE" up -d

# 4. Wait for API to be healthy (via nginx or direct container check)
echo "[4/6] Attente de l'API..."
for i in $(seq 1 30); do
    # Utiliser docker exec pour tester le healthcheck en interne (pas localhost:8000)
    if docker compose -f "$COMPOSE_FILE" exec -T api python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" 2>/dev/null; then
        echo "  API is healthy!"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "  ERREUR: API non disponible apres 60 secondes."
        echo "  Consultez les logs: docker compose -f $COMPOSE_FILE logs api"
        exit 1
    fi
    echo "  Waiting... ($i/30)"
    sleep 2
done

# 5. Run migrations
echo "[5/6] Migrations Alembic..."
docker compose -f "$COMPOSE_FILE" exec -T api alembic upgrade head

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
docker compose -f "$COMPOSE_FILE" ps
