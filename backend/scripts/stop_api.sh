#!/bin/bash
# stop_api.sh - Stop the API server and any processes using port 8000

echo "=========================================="
echo "Stopping Resume Tailor API Server"
echo "=========================================="

# Find processes using port 8000
PIDS=$(lsof -ti:8000 2>/dev/null)

if [ -z "$PIDS" ]; then
    echo "✅ No processes found on port 8000"
    exit 0
fi

echo "Found processes on port 8000: $PIDS"
echo "Stopping processes..."

# Kill the processes
for PID in $PIDS; do
    echo "  Killing process $PID..."
    kill -9 "$PID" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "  ✅ Process $PID stopped"
    else
        echo "  ⚠️  Failed to stop process $PID (may require sudo)"
    fi
done

# Wait a moment for ports to be released
sleep 1

# Verify port is free
if lsof -ti:8000 >/dev/null 2>&1; then
    echo "⚠️  Port 8000 is still in use. You may need to run:"
    echo "   sudo lsof -ti:8000 | xargs sudo kill -9"
else
    echo "✅ Port 8000 is now free"
fi

