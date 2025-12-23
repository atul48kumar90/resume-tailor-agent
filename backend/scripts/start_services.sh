#!/bin/bash
# start_services.sh - Start all required services (Redis, API)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "=========================================="
echo "Starting Resume Tailor Services"
echo "=========================================="

# Function to check if a process is running on a port
check_port() {
    lsof -i :$1 > /dev/null 2>&1
}

# Start Redis
echo ""
echo "1. Starting Redis..."
if check_port 6379; then
    echo "✅ Redis is already running on port 6379"
else
    if command -v redis-server &> /dev/null; then
        echo "   Starting Redis server..."
        redis-server --daemonize yes
        sleep 2
        if redis-cli ping > /dev/null 2>&1; then
            echo "✅ Redis started successfully"
        else
            echo "❌ Failed to start Redis"
            exit 1
        fi
    else
        echo "❌ redis-server not found"
        echo "   Install: brew install redis (macOS) or apt-get install redis-server (Linux)"
        exit 1
    fi
fi

# Start API
echo ""
echo "2. Starting API server..."
if check_port 8000; then
    echo "⚠️  Port 8000 is already in use"
    echo "   API may already be running, or another service is using the port"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check for virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

# Load .env if exists
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

echo "   Starting API on http://localhost:8000"
echo "   Press Ctrl+C to stop"
echo ""

# Start API in foreground
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

