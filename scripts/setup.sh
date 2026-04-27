#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

command -v npm >/dev/null 2>&1 || { echo "npm est requis."; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "python3 est requis."; exit 1; }

npm install
npm --prefix apps/web install

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r apps/api/requirements.txt

if [ ! -f ".env" ]; then
  cp .env.example .env
fi

# Reseau Docker externe requis par docker-compose.yml (service web).
# Idempotent : ne casse rien si le reseau existe deja.
if command -v docker >/dev/null 2>&1; then
  docker network create interface-ia-net >/dev/null 2>&1 || true
fi

echo "Environnement local initialise."
