#!/bin/bash
# start_api.sh - Start the API server with proper configuration

echo "=========================================="
echo "Starting Resume Tailor API Server"
echo "=========================================="

# Get the project root directory (parent of backend)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$(cd "$BACKEND_ROOT/.." && pwd)"

cd "$BACKEND_ROOT"

# Check if virtual environment exists (at project root)
if [ -d "$PROJECT_ROOT/.venv" ]; then
    echo "✅ Found virtual environment (.venv)"
    source "$PROJECT_ROOT/.venv/bin/activate"
elif [ -d "$PROJECT_ROOT/venv" ]; then
    echo "✅ Found virtual environment (venv)"
    source "$PROJECT_ROOT/venv/bin/activate"
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
    if [ -f "$PROJECT_ROOT/.env" ]; then
        echo "📝 Loading .env file..."
        export $(cat "$PROJECT_ROOT/.env" | grep -v '^#' | xargs)
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

# Check if required dependencies are installed
echo ""
echo "Checking dependencies..."
MISSING_DEPS=0

if ! python -c "import uvicorn" 2>/dev/null; then
    echo "❌ uvicorn is not installed"
    MISSING_DEPS=1
else
    echo "✅ uvicorn is installed"
fi

if ! python -c "import sqlalchemy" 2>/dev/null; then
    echo "❌ sqlalchemy is not installed"
    MISSING_DEPS=1
else
    echo "✅ sqlalchemy is installed"
fi

if ! python -c "import asyncpg" 2>/dev/null; then
    echo "⚠️  asyncpg is not installed (needed for PostgreSQL)"
    MISSING_DEPS=1
else
    echo "✅ asyncpg is installed"
fi

if [ $MISSING_DEPS -eq 1 ]; then
    echo ""
    echo "Installing missing dependencies..."
    pip install --upgrade pip
    
    # Install requirements, ignoring errors for optional packages
    if pip install -r "$BACKEND_ROOT/requirements.txt" 2>&1 | tee /tmp/pip_install.log; then
        echo "✅ Dependencies installed successfully"
    else
        # Check if critical dependencies were installed despite errors
        if python -c "import sqlalchemy" 2>/dev/null; then
            echo "⚠️  Some optional dependencies failed to install, but critical ones are available"
            echo "   Check /tmp/pip_install.log for details"
        else
            echo "❌ Failed to install critical dependencies"
            echo "   Please run: pip install -r requirements.txt manually"
            exit 1
        fi
    fi
    
    # Verify critical dependencies
    echo ""
    echo "Verifying critical dependencies..."
    if python -c "import sqlalchemy" 2>/dev/null; then
        echo "✅ sqlalchemy verified"
    else
        echo "❌ sqlalchemy still not available - installation may have failed"
        echo "   Try: pip install sqlalchemy asyncpg alembic"
        exit 1
    fi
    
    if python -c "import asyncpg" 2>/dev/null; then
        echo "✅ asyncpg verified"
    else
        echo "⚠️  asyncpg not available (PostgreSQL features will be limited)"
    fi
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

# Start uvicorn (from backend directory)
cd "$BACKEND_ROOT"
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

