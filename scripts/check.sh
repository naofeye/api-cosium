#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

[ -f .env ] || cp .env.example .env

docker compose config >/dev/null

if [ -d "apps/web/node_modules" ]; then
  npm --prefix apps/web run typecheck
fi

if [ -d ".venv" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
  python -m compileall apps/api/app >/dev/null
fi

echo "Verification de configuration terminee."
