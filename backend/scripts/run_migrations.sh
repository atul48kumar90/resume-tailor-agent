#!/bin/bash
# run_migrations.sh - Create and run database migrations

echo "=========================================="
echo "Database Migration Setup"
echo "=========================================="

# Get the project root directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Check if virtual environment exists
if [ -d ".venv" ]; then
    echo "✅ Activating virtual environment (.venv)"
    source .venv/bin/activate
elif [ -d "venv" ]; then
    echo "✅ Activating virtual environment (venv)"
    source venv/bin/activate
else
    echo "❌ No virtual environment found"
    echo "   Please create one: python3 -m venv .venv"
    exit 1
fi

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "❌ DATABASE_URL is not set"
    echo ""
    echo "Please set DATABASE_URL first:"
    echo "  export DATABASE_URL=\"postgresql+asyncpg://resume_user:resume_password@localhost:5432/resume_db\""
    echo ""
    echo "Or if using default postgres user:"
    echo "  export DATABASE_URL=\"postgresql+asyncpg://postgres:yourpassword@localhost:5432/postgres\""
    exit 1
fi

echo "✅ DATABASE_URL is set"

# Extract sync URL from async URL
# Convert postgresql+asyncpg:// to postgresql://
SYNC_URL=$(echo "$DATABASE_URL" | sed 's/postgresql+asyncpg:\/\//postgresql:\/\//')
export DATABASE_URL_SYNC="$SYNC_URL"

echo "✅ DATABASE_URL_SYNC: $DATABASE_URL_SYNC"

# Check if required packages are installed
MISSING_PACKAGES=()

if ! python -c "import alembic" 2>/dev/null; then
    MISSING_PACKAGES+=("alembic")
fi

if ! python -c "import psycopg2" 2>/dev/null; then
    MISSING_PACKAGES+=("psycopg2-binary")
fi

if ! python -c "import sqlalchemy" 2>/dev/null; then
    MISSING_PACKAGES+=("sqlalchemy")
fi

if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    echo "❌ Missing required packages: ${MISSING_PACKAGES[*]}"
    echo "   Installing dependencies..."
    pip install "${MISSING_PACKAGES[@]}"
fi

# Check if migration files exist
MIGRATION_COUNT=$(find alembic/versions -name "*.py" 2>/dev/null | wc -l | tr -d ' ')

if [ "$MIGRATION_COUNT" -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "Creating initial migration..."
    echo "=========================================="
    
    # Create initial migration
    alembic revision --autogenerate -m "Initial migration"
    
    if [ $? -ne 0 ]; then
        echo "❌ Failed to create migration"
        exit 1
    fi
    
    echo "✅ Initial migration created"
else
    echo "✅ Found $MIGRATION_COUNT migration file(s)"
fi

# Run migrations
echo ""
echo "=========================================="
echo "Running database migrations..."
echo "=========================================="

alembic upgrade head

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Database migrations completed successfully!"
    echo ""
    echo "You can now start the API server:"
    echo "  ./scripts/start_api.sh"
else
    echo ""
    echo "❌ Database migration failed"
    echo "   Please check the error messages above"
    exit 1
fi

