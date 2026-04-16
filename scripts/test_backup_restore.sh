#!/bin/bash
# OptiFlow — Test backup → drop → restore → verify
# Exécute un cycle complet de sauvegarde/restauration PostgreSQL pour valider la procédure.
#
# Usage : ./scripts/test_backup_restore.sh
# Prérequis : docker compose up -d (services postgres + api démarrés)
set -euo pipefail

POSTGRES_USER="${POSTGRES_USER:-optiflow}"
POSTGRES_DB="${POSTGRES_DB:-optiflow}"
TEST_DB="${POSTGRES_DB}_restore_test"
BACKUP_DIR="${BACKUP_DIR:-./backups}"

log() { echo "[$(date -u +%FT%TZ)] $*"; }
fail() { log "FAIL: $*"; exit 1; }

# 1. Backup
log "Étape 1/5 : création du backup..."
./scripts/backup.sh >/dev/null
LATEST_DB_BACKUP=$(ls -t "$BACKUP_DIR"/db_*.sql.gz 2>/dev/null | head -1)
[ -n "$LATEST_DB_BACKUP" ] || fail "Aucun backup DB trouvé dans $BACKUP_DIR"
log "Backup trouvé: $LATEST_DB_BACKUP"

# 2. Count rows dans prod (référence)
log "Étape 2/5 : comptage lignes références..."
REF_USERS=$(docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT COUNT(*) FROM users;")
REF_CUSTOMERS=$(docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT COUNT(*) FROM customers;")
log "Prod: users=$REF_USERS customers=$REF_CUSTOMERS"

# 3. Drop & recreate test DB
log "Étape 3/5 : DROP + CREATE DATABASE $TEST_DB..."
docker compose exec -T postgres psql -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS $TEST_DB;" >/dev/null
docker compose exec -T postgres psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE $TEST_DB;" >/dev/null

# 4. Restore
log "Étape 4/5 : restauration du backup dans $TEST_DB..."
gunzip -c "$LATEST_DB_BACKUP" | docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$TEST_DB" >/dev/null

# 5. Verify
log "Étape 5/5 : vérification des comptages..."
RESTORE_USERS=$(docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$TEST_DB" -tAc "SELECT COUNT(*) FROM users;")
RESTORE_CUSTOMERS=$(docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$TEST_DB" -tAc "SELECT COUNT(*) FROM customers;")

if [ "$REF_USERS" = "$RESTORE_USERS" ] && [ "$REF_CUSTOMERS" = "$RESTORE_CUSTOMERS" ]; then
    log "OK : users=$RESTORE_USERS customers=$RESTORE_CUSTOMERS correspondent au source."
else
    fail "Divergence : prod users=$REF_USERS restore=$RESTORE_USERS ; prod customers=$REF_CUSTOMERS restore=$RESTORE_CUSTOMERS"
fi

# Cleanup
docker compose exec -T postgres psql -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE $TEST_DB;" >/dev/null
log "SUCCESS : cycle backup → drop → restore → verify validé."
