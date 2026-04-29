#!/usr/bin/env bash
# Health check pour OptiFlow stack — verifie que tous les services sont UP.
#
# Usage : ./scripts/health.sh
# Exit 0 si tout OK, 1 si un service est down.
#
# Utile pour :
# - Smoke test post-deploy
# - Cron de monitoring externe
# - Pre-commit hook avant `make test`

set -uo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

EXIT_CODE=0

check() {
  local name="$1"
  local cmd="$2"
  printf "  %-20s " "$name"
  if eval "$cmd" >/dev/null 2>&1; then
    printf "${GREEN}OK${NC}\n"
  else
    printf "${RED}FAIL${NC}\n"
    EXIT_CODE=1
  fi
}

echo "OptiFlow health check"
echo "===================="

# Conteneurs Docker
check "postgres"  'docker compose ps postgres --format json | grep -q "\"State\":\"running\""'
check "redis"     'docker compose ps redis --format json | grep -q "\"State\":\"running\""'
check "minio"     'docker compose ps minio --format json | grep -q "\"State\":\"running\""'
check "api"       'docker compose ps api --format json | grep -q "\"State\":\"running\""'
check "web"       'docker compose ps web --format json | grep -q "\"State\":\"running\""'
check "worker"    'docker compose ps worker --format json | grep -q "\"State\":\"running\""'
check "beat"      'docker compose ps beat --format json | grep -q "\"State\":\"running\""'

# Endpoints
check "API health"      'curl -fsS --max-time 5 http://localhost:8000/health'
check "Web frontend"    'curl -fsS --max-time 5 http://localhost:3000 -o /dev/null'
check "Postgres SQL"    'docker compose exec -T postgres pg_isready -U "${POSTGRES_USER:-optiflow}"'
check "Redis ping"      'docker compose exec -T redis redis-cli ping | grep -q PONG'
check "MinIO live"      'curl -fsS --max-time 5 http://localhost:9000/minio/health/live -o /dev/null'

if [ $EXIT_CODE -eq 0 ]; then
  printf "\n${GREEN}All checks passed.${NC}\n"
else
  printf "\n${RED}One or more checks failed.${NC}\n"
  printf "${YELLOW}Run 'docker compose logs <service>' for diagnosis.${NC}\n"
fi

exit $EXIT_CODE
