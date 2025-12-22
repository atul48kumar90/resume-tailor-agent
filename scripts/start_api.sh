#!/bin/bash
# start_api.sh - Start the API server with proper configuration

echo "=========================================="
echo "Starting Resume Tailor API Server"
echo "=========================================="

# Get the project root directory (parent of scripts)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Check if virtual environment exists
if [ -d ".venv" ]; then
    echo "✅ Found virtual environment (.venv)"
    source .venv/bin/activate
elif [ -d "venv" ]; then
    echo "✅ Found virtual environment (venv)"
    source venv/bin/activate
else
    echo "⚠️  No virtual environment found"
    echo "   Creating one is recommended: python -m venv .venv"
    read -p "Continue without virtual environment? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check for required environment variables
echo ""
echo "Checking environment variables..."

if [ -z "$OPENAI_API_KEY" ]; then
    if [ -f ".env" ]; then
        echo "📝 Loading .env file..."
        export $(cat .env | grep -v '^#' | xargs)
    fi
    
    if [ -z "$OPENAI_API_KEY" ]; then
        echo "⚠️  OPENAI_API_KEY not set"
        echo "   Set it with: export OPENAI_API_KEY=your_key_here"
        echo "   Or create a .env file with: OPENAI_API_KEY=your_key_here"
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        echo "✅ OPENAI_API_KEY found in .env"
    fi
else
    echo "✅ OPENAI_API_KEY is set"
fi

# Check Redis
echo ""
echo "Checking Redis..."
if command -v redis-cli &> /dev/null; then
    if redis-cli ping > /dev/null 2>&1; then
        echo "✅ Redis is running"
    else
        echo "⚠️  Redis is not running"
        echo "   Starting Redis..."
        if command -v redis-server &> /dev/null; then
            # Try to start Redis in background
            redis-server --daemonize yes 2>/dev/null || echo "   Please start Redis manually: redis-server"
        else
            echo "   Please install and start Redis: brew install redis && redis-server"
        fi
    fi
else
    echo "⚠️  redis-cli not found"
    echo "   Some features may not work without Redis"
    echo "   Install: brew install redis (macOS) or apt-get install redis (Linux)"
fi

# Check if uvicorn is installed
echo ""
echo "Checking dependencies..."
if python -c "import uvicorn" 2>/dev/null; then
    echo "✅ uvicorn is installed"
else
    echo "❌ uvicorn is not installed"
    echo "   Installing dependencies..."
    pip install -r requirements.txt
fi

# Start the server
echo ""
echo "=========================================="
echo "Starting API server on http://localhost:8000"
echo "=========================================="
echo ""
echo "API will be available at:"
echo "  - API: http://localhost:8000"
echo "  - Docs: http://localhost:8000/docs"
echo "  - Health: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start uvicorn
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

