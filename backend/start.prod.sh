#!/bin/sh
set -e

echo "Waiting for PostgreSQL..."
until python -c "import socket; s = socket.create_connection(('postgres', 5432), timeout=2); s.close()" 2>/dev/null; do
    sleep 2
done
echo "PostgreSQL is ready."

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting API (production)..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
