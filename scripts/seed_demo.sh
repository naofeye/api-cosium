#!/bin/bash
# OptiFlow — Reset BDD + seed donnees demo enrichies (pour presentations)
# Usage: ./scripts/seed_demo.sh
# DESTRUCTIF : drop toutes donnees existantes !
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "ATTENTION : Ceci va EFFACER toutes les donnees existantes."
read -p "Confirmer ? (oui/non) " confirm
if [ "$confirm" != "oui" ]; then
    echo "Annule."
    exit 0
fi

echo "[1/4] Reset BDD (drop + recreate schema)..."
docker compose exec -T postgres psql -U "${POSTGRES_USER:-optiflow}" \
    -d "${POSTGRES_DB:-optiflow}" \
    -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

echo "[2/4] Migrations Alembic..."
docker compose exec -T api alembic upgrade head

echo "[3/4] Seed minimal (org + tenant + admin)..."
docker compose exec -T api python -m app.seed

echo "[4/4] Seed demo enrichi (clients + dossiers + factures + paiements)..."
docker compose exec -T api python -c "
from app.db.session import SessionLocal
from tests.factories.seed import seed_demo_data
db = SessionLocal()
result = seed_demo_data(db)
db.close()
print('OK seeded:', result)
"

echo ""
echo "Donnees demo pretes."
echo "Login : admin@optiflow.local / admin123"
