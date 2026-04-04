#!/bin/bash
# OptiFlow — Script de deploiement production
set -e

echo "========================================="
echo "  OptiFlow AI — Deploiement Production"
echo "========================================="

cd "$(dirname "$0")/.."

# 0. Backup database before deployment
echo "[0/6] Backup de la base de donnees..."
if docker compose -f docker-compose.prod.yml ps postgres | grep -q "running"; then
    ./scripts/backup_db.sh
    echo "  Backup termine."
else
    echo "  PostgreSQL non demarre, backup ignore."
fi

# 1. Pull latest code
echo "[1/6] Pull du code..."
git pull origin main

# 2. Build images
echo "[2/6] Build des images Docker..."
docker compose -f docker-compose.prod.yml build

# 3. Run migrations BEFORE switching (blue-green)
echo "[3/6] Demarrage des services..."
docker compose -f docker-compose.prod.yml up -d

# 4. Wait for API to be healthy
echo "[4/6] Attente de l'API..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo "  API is healthy!"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "  ERREUR: API non disponible apres 60 secondes."
        echo "  Consultez les logs: docker compose -f docker-compose.prod.yml logs api"
        exit 1
    fi
    echo "  Waiting... ($i/30)"
    sleep 2
done

# 5. Run migrations
echo "[5/6] Migrations Alembic..."
docker compose -f docker-compose.prod.yml exec -T api alembic upgrade head

# 6. Verify
echo "[6/6] Verification..."
curl -sf http://localhost:8000/api/v1/admin/health | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  Status: {d[\"status\"]}')" 2>/dev/null || echo "  Health check non disponible"

echo ""
echo "========================================="
echo "  Deploiement termine avec succes !"
echo "========================================="
docker compose -f docker-compose.prod.yml ps
