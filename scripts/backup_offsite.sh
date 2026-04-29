#!/bin/bash
# OptiFlow — Off-site backup sync (MinIO + DB dumps)
# Synchronise les backups locaux vers un endpoint S3 distant (AWS S3, Scaleway, OVH, Wasabi, ...).
#
# Pré-requis :
#   - Les backups locaux doivent exister (cf. scripts/backup.sh — planifié via cron).
#   - Le binaire `mc` (MinIO client) doit être installé sur la machine (ou utiliser Docker image minio/mc).
#   - Variables d'environnement requises :
#       OFFSITE_ENDPOINT    URL du bucket distant (ex: https://s3.fr-par.scw.cloud)
#       OFFSITE_ACCESS_KEY  Clé d'accès
#       OFFSITE_SECRET_KEY  Clé secrète
#       OFFSITE_BUCKET      Nom du bucket distant (ex: optiflow-backups-prod)
#
# Usage : ./scripts/backup_offsite.sh
# Crontab suggéré : 0 3 * * * cd /srv/optiflow && ./scripts/backup_offsite.sh >> /var/log/optiflow_backup.log 2>&1
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
OFFSITE_ENDPOINT="${OFFSITE_ENDPOINT:-}"
OFFSITE_ACCESS_KEY="${OFFSITE_ACCESS_KEY:-}"
OFFSITE_SECRET_KEY="${OFFSITE_SECRET_KEY:-}"
OFFSITE_BUCKET="${OFFSITE_BUCKET:-}"

log() { echo "[$(date -u +%FT%TZ)] $*"; }

if [ -z "$OFFSITE_ENDPOINT" ] || [ -z "$OFFSITE_ACCESS_KEY" ] || [ -z "$OFFSITE_SECRET_KEY" ] || [ -z "$OFFSITE_BUCKET" ]; then
    log "ERROR: variables OFFSITE_ENDPOINT/OFFSITE_ACCESS_KEY/OFFSITE_SECRET_KEY/OFFSITE_BUCKET requises."
    exit 2
fi

if [ ! -d "$BACKUP_DIR" ]; then
    log "ERROR: répertoire backup introuvable: $BACKUP_DIR"
    exit 3
fi

# Utilise `mc` via Docker si non installé localement — évite une dépendance durable.
# Important : on ne passe JAMAIS les credentials dans la URL (qui apparaitrait dans
# `ps`/`history`/logs). On les injecte via env-file a permissions strictes.
MC_ENV_FILE=""
cleanup_mc_env() {
    if [ -n "$MC_ENV_FILE" ] && [ -f "$MC_ENV_FILE" ]; then
        rm -f "$MC_ENV_FILE"
    fi
}
trap cleanup_mc_env EXIT

MC="mc"
if ! command -v mc >/dev/null 2>&1; then
    MC_ENV_FILE="$(mktemp)"
    chmod 600 "$MC_ENV_FILE"
    {
        printf 'MC_HOST_offsite=%s\n' "${OFFSITE_ENDPOINT/https:\/\//https://${OFFSITE_ACCESS_KEY}:${OFFSITE_SECRET_KEY}@}"
    } > "$MC_ENV_FILE"
    MC="docker run --rm --env-file ${MC_ENV_FILE} -v ${PWD}/${BACKUP_DIR}:/data minio/mc"
fi

# Enregistre l'alias offsite (idempotent).
log "Configuration alias MinIO client..."
$MC alias set offsite "$OFFSITE_ENDPOINT" "$OFFSITE_ACCESS_KEY" "$OFFSITE_SECRET_KEY" >/dev/null

# Miroir local → remote. --remove (option) retirée pour éviter toute perte accidentelle.
log "Synchronisation $BACKUP_DIR → offsite/$OFFSITE_BUCKET..."
$MC mirror --overwrite --preserve "$BACKUP_DIR" "offsite/$OFFSITE_BUCKET"

# Compte et taille
REMOTE_COUNT=$($MC ls --recursive "offsite/$OFFSITE_BUCKET" | wc -l)
log "Off-site backup synchronisé. Objets distants: $REMOTE_COUNT"
