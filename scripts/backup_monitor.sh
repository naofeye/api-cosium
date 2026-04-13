#!/bin/bash
# OptiFlow — Monitor backup : alerte si le dernier backup date de plus de 25h.
# A executer via cron horaire : 0 * * * * /path/to/backup_monitor.sh
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="$ROOT_DIR/runtime/backups"
MAX_AGE_HOURS="${MAX_AGE_HOURS:-25}"
ALERT_WEBHOOK="${BACKUP_ALERT_WEBHOOK:-}"  # Slack/Discord webhook optionnel

if [ ! -d "$BACKUP_DIR" ]; then
    echo "ERREUR: repertoire backup $BACKUP_DIR inexistant"
    exit 1
fi

# Dernier backup modifie
LATEST=$(find "$BACKUP_DIR" -name "*.dump" -type f -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)

if [ -z "$LATEST" ]; then
    MSG="ALERT backup: aucun fichier .dump dans $BACKUP_DIR"
    echo "$MSG" >&2
    [ -n "$ALERT_WEBHOOK" ] && curl -sf -X POST -H 'Content-Type: application/json' \
        -d "{\"text\":\"$MSG\"}" "$ALERT_WEBHOOK" || true
    exit 2
fi

# Age en heures
AGE_SECONDS=$(($(date +%s) - $(stat -c %Y "$LATEST")))
AGE_HOURS=$((AGE_SECONDS / 3600))

if [ "$AGE_HOURS" -gt "$MAX_AGE_HOURS" ]; then
    MSG="ALERT backup: dernier backup a ${AGE_HOURS}h (seuil ${MAX_AGE_HOURS}h) — $LATEST"
    echo "$MSG" >&2
    [ -n "$ALERT_WEBHOOK" ] && curl -sf -X POST -H 'Content-Type: application/json' \
        -d "{\"text\":\"$MSG\"}" "$ALERT_WEBHOOK" || true
    exit 2
fi

echo "OK: dernier backup il y a ${AGE_HOURS}h — $LATEST"
