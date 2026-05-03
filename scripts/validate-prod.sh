#!/usr/bin/env bash
# Pre-prod validation : verifie que les 6 prerequis production sont en place
# avant `docker compose -f docker-compose.prod.yml up`.
#
# Usage :
#   ./scripts/validate-prod.sh           # check uniquement, exit code != 0 si fail
#   ENV_FILE=/path/to/.env.prod ./scripts/validate-prod.sh
#
# Items verifies :
# 1. JWT_SECRET >= 64 bytes hex
# 2. ENCRYPTION_KEY base64 valide 32 bytes
# 3. POSTGRES_PASSWORD != "optiflow" (default insecure)
# 4. MINIO_ROOT_PASSWORD != "minioadmin" (default insecure)
# 5. GF_SECURITY_ADMIN_PASSWORD != "admin" (default insecure)
# 6. SENTRY_DSN configured (non-placeholder)
# Optionnel : TLS verifiable seulement sur instance live.

set -euo pipefail

ENV_FILE="${ENV_FILE:-.env.prod}"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'  # No Color

errors=0
warnings=0

if [ ! -f "$ENV_FILE" ]; then
    printf "${RED}[FAIL]${NC} $ENV_FILE introuvable. Specifier via ENV_FILE=/path.\n"
    exit 1
fi

# shellcheck disable=SC2046
export $(grep -v '^#' "$ENV_FILE" | grep -v '^$' | xargs -d '\n')

check_pass() { printf "${GREEN}[ OK ]${NC} %s\n" "$1"; }
check_fail() { printf "${RED}[FAIL]${NC} %s\n" "$1"; errors=$((errors + 1)); }
check_warn() { printf "${YELLOW}[WARN]${NC} %s\n" "$1"; warnings=$((warnings + 1)); }

printf "==> Pre-prod validation (env: %s)\n\n" "$ENV_FILE"

# 1. JWT_SECRET
if [ -z "${JWT_SECRET:-}" ]; then
    check_fail "JWT_SECRET vide"
elif [ "${#JWT_SECRET}" -lt 64 ]; then
    check_fail "JWT_SECRET trop court (${#JWT_SECRET} chars, min 64). Generer : python -c 'import secrets; print(secrets.token_hex(32))'"
else
    check_pass "JWT_SECRET (${#JWT_SECRET} chars)"
fi

# 2. ENCRYPTION_KEY (base64 32 bytes = 44 chars avec '=' padding)
if [ -z "${ENCRYPTION_KEY:-}" ]; then
    check_fail "ENCRYPTION_KEY vide. Generer : python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
elif ! echo "$ENCRYPTION_KEY" | base64 -d >/dev/null 2>&1; then
    check_fail "ENCRYPTION_KEY n'est pas du base64 valide"
else
    decoded_len=$(echo "$ENCRYPTION_KEY" | base64 -d 2>/dev/null | wc -c)
    if [ "$decoded_len" -ne 32 ]; then
        check_fail "ENCRYPTION_KEY decode = $decoded_len bytes (attendu 32)"
    else
        check_pass "ENCRYPTION_KEY (Fernet 32 bytes)"
    fi
fi

# 3. POSTGRES_PASSWORD
if [ -z "${POSTGRES_PASSWORD:-}" ] || [ "${POSTGRES_PASSWORD}" = "optiflow" ]; then
    check_fail "POSTGRES_PASSWORD vide ou == 'optiflow' (defaut compose)"
elif [ "${#POSTGRES_PASSWORD}" -lt 16 ]; then
    check_warn "POSTGRES_PASSWORD court (${#POSTGRES_PASSWORD} chars, recommande >= 16)"
else
    check_pass "POSTGRES_PASSWORD configure (${#POSTGRES_PASSWORD} chars)"
fi

# 4. MINIO_ROOT_PASSWORD
mp="${MINIO_ROOT_PASSWORD:-${S3_SECRET_KEY:-}}"
if [ -z "$mp" ] || [ "$mp" = "minioadmin" ]; then
    check_fail "MINIO_ROOT_PASSWORD/S3_SECRET_KEY vide ou == 'minioadmin' (defaut)"
elif [ "${#mp}" -lt 16 ]; then
    check_warn "MinIO password court (${#mp} chars, recommande >= 16)"
else
    check_pass "MinIO root password configure"
fi

# 5. Grafana
gp="${GF_SECURITY_ADMIN_PASSWORD:-}"
if [ -z "$gp" ] || [ "$gp" = "admin" ]; then
    check_fail "GF_SECURITY_ADMIN_PASSWORD vide ou == 'admin' (defaut)"
else
    check_pass "Grafana admin password configure"
fi

# 6. Sentry DSN
sd="${SENTRY_DSN:-}"
if [ -z "$sd" ] || [[ "$sd" == __CHANGE_ME__* ]]; then
    check_warn "SENTRY_DSN vide ou placeholder. Sans Sentry, pas d'alerting erreurs en prod."
else
    if [[ "$sd" =~ ^https://.+@.+\.ingest\.(.+)sentry\.io/[0-9]+$ ]]; then
        check_pass "SENTRY_DSN format valide"
    else
        check_warn "SENTRY_DSN forme inhabituelle, verifier le copy-paste"
    fi
fi

# 7. CORS_ORIGINS doit etre HTTPS only en prod
co="${CORS_ORIGINS:-}"
if [[ "$co" == *"http://"* ]] && [[ "$co" != *localhost* ]]; then
    check_warn "CORS_ORIGINS contient un http:// non-localhost. Prefer https://."
fi

# 8. APP_ENV doit etre 'production' ou 'staging'
ae="${APP_ENV:-development}"
if [ "$ae" != "production" ] && [ "$ae" != "staging" ]; then
    check_warn "APP_ENV='$ae' (attendu 'production' ou 'staging')"
fi

printf "\n==> Resultat\n"
printf "  Errors  : %d\n" "$errors"
printf "  Warnings: %d\n" "$warnings"

if [ "$errors" -gt 0 ]; then
    printf "\n${RED}Validation echouee. Corriger les erreurs avant deploy prod.${NC}\n"
    exit 1
fi

if [ "$warnings" -gt 0 ]; then
    printf "\n${YELLOW}Validation passee avec %d warnings (non bloquants).${NC}\n" "$warnings"
else
    printf "\n${GREEN}Tous les prerequis prod sont en place.${NC}\n"
fi
