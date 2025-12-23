#!/bin/bash
# start.sh - Startup script that runs migrations before starting the server

set -e

echo "=========================================="
echo "Resume Tailor Agent - Starting..."
echo "=========================================="

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until python -c "
import sys
import os
sys.path.insert(0, '/app')
from core.settings import DATABASE_URL_SYNC
from sqlalchemy import create_engine, text
try:
    engine = create_engine(DATABASE_URL_SYNC)
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))
    print('✅ PostgreSQL is ready')
except Exception as e:
    print(f'⏳ Waiting for PostgreSQL... ({e})')
    sys.exit(1)
" 2>/dev/null; do
    sleep 2
done

# Run database migrations
echo ""
echo "=========================================="
echo "Running database migrations..."
echo "=========================================="

cd /app
alembic upgrade head

if [ $? -eq 0 ]; then
    echo "✅ Database migrations completed"
else
    echo "⚠️  Database migration failed, but continuing..."
    echo "   You may need to run migrations manually:"
    echo "   docker-compose exec app alembic upgrade head"
fi

# Start the FastAPI server
echo ""
echo "=========================================="
echo "Starting FastAPI server..."
echo "=========================================="

exec python -m uvicorn api.main:app --host 0.0.0.0 --port 8000

