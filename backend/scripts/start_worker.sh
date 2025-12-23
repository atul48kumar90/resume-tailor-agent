#!/bin/bash
# start_worker.sh - Start RQ worker for background job processing

echo "=========================================="
echo "Starting RQ Worker for Background Jobs"
echo "=========================================="

# Get the project root directory
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
        echo "   Please start Redis: redis-server"
        exit 1
    fi
else
    echo "⚠️  redis-cli not found"
    echo "   Please install Redis: brew install redis (macOS) or apt-get install redis (Linux)"
    exit 1
fi

# Check if rq is installed
echo ""
echo "Checking dependencies..."
if python -c "import rq" 2>/dev/null; then
    echo "✅ rq is installed"
else
    echo "❌ rq is not installed"
    echo "   Installing dependencies..."
    pip install -r requirements.txt
fi

# Start the worker
echo ""
echo "=========================================="
echo "Starting RQ Worker"
echo "=========================================="
echo ""
echo "Worker will process jobs from the 'default' queue"
echo "Press Ctrl+C to stop the worker"
echo ""
echo "Current directory: $(pwd)"
echo "Python path will include: $PROJECT_ROOT"
echo ""

# Ensure we're in the backend directory for proper imports
cd "$PROJECT_ROOT"

# Fix macOS fork() issue with langchain/pydantic
# This must be set before starting the worker
if [[ "$OSTYPE" == "darwin"* ]]; then
    export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
    echo "⚠️  macOS detected: Set OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES to prevent fork() crashes"
fi

# Start worker using our custom worker script
# Run as module to ensure proper Python path resolution
python -m workers.job_worker

