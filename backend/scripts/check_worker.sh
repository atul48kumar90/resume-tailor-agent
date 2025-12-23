#!/bin/bash
# check_worker.sh - Check if RQ worker is running and diagnose job queue issues

echo "=========================================="
echo "RQ Worker & Job Queue Diagnostics"
echo "=========================================="

# Get the project root directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Check if virtual environment exists and activate it
if [ -d ".venv" ]; then
    echo "✅ Found virtual environment (.venv)"
    source .venv/bin/activate
elif [ -d "venv" ]; then
    echo "✅ Found virtual environment (venv)"
    source venv/bin/activate
else
    echo "⚠️  No virtual environment found"
    exit 1
fi

# Check Redis
echo ""
echo "Checking Redis..."
if command -v redis-cli &> /dev/null; then
    if redis-cli ping > /dev/null 2>&1; then
        echo "✅ Redis is running"
    else
        echo "❌ Redis is not running"
        echo "   Start Redis: redis-server"
        exit 1
    fi
else
    echo "⚠️  redis-cli not found"
fi

# Check if RQ worker process is running
echo ""
echo "Checking RQ Worker Process..."
if pgrep -f "workers.job_worker" > /dev/null 2>&1 || pgrep -f "rq worker" > /dev/null 2>&1; then
    echo "✅ RQ worker process is running"
    echo "   Process details:"
    pgrep -fl "workers.job_worker\|rq worker" | head -3
else
    echo "❌ RQ worker is NOT running"
    echo ""
    echo "   Jobs are being queued but not processed!"
    echo "   Start the worker with:"
    echo "   cd backend && ./scripts/start_worker.sh"
    echo "   OR"
    echo "   cd backend && python -m workers.job_worker"
fi

# Check queue status via API (if server is running)
echo ""
echo "Checking Queue Status..."
if curl -s http://localhost:8000/queue/stats > /dev/null 2>&1; then
    echo "✅ API server is running"
    echo ""
    echo "Queue Statistics:"
    curl -s http://localhost:8000/queue/stats | python -m json.tool 2>/dev/null || curl -s http://localhost:8000/queue/stats
    echo ""
else
    echo "⚠️  API server is not running (or not accessible)"
    echo "   Start with: cd backend && ./scripts/start_api.sh"
fi

# Check for stuck jobs
echo ""
echo "Checking for stuck jobs..."
if command -v redis-cli &> /dev/null; then
    QUEUED=$(redis-cli LLEN rq:queue:default 2>/dev/null || echo "0")
    if [ "$QUEUED" != "0" ] && [ "$QUEUED" != "" ]; then
        echo "⚠️  Found $QUEUED job(s) in queue"
        if ! pgrep -f "workers.job_worker\|rq worker" > /dev/null 2>&1; then
            echo "   ⚠️  WARNING: Worker is not running! Jobs will not be processed."
            echo "   Start worker: cd backend && ./scripts/start_worker.sh"
        fi
    else
        echo "✅ No jobs in queue"
    fi
fi

echo ""
echo "=========================================="
echo "Diagnostics complete"
echo "=========================================="

