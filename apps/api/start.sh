#!/bin/sh
set -e

# Extraire hostname et port depuis DATABASE_URL pour le wait loop.
DB_HOST=$(python -c "
import os, re
url = os.environ.get('DATABASE_URL', '')
m = re.search(r'@([^/:]+)(?::(\d+))?/', url)
print(m.group(1) if m else 'postgres')
")
DB_PORT=$(python -c "
import os, re
url = os.environ.get('DATABASE_URL', '')
m = re.search(r'@[^/:]+:(\d+)/', url)
print(m.group(1) if m else '5432')
")

echo "Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT}..."
until python -c "import socket; s = socket.create_connection(('${DB_HOST}', ${DB_PORT}), timeout=2); s.close()" 2>/dev/null; do
    echo "  PostgreSQL not ready at ${DB_HOST}:${DB_PORT}, retrying in 2s..."
    sleep 2
done
echo "PostgreSQL is ready at ${DB_HOST}:${DB_PORT}."

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
