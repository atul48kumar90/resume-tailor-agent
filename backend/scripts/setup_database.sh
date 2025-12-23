#!/bin/bash
# setup_database.sh - Set up PostgreSQL database for Resume Tailor Agent

echo "=========================================="
echo "Setting up PostgreSQL Database"
echo "=========================================="

# Get the project root directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL is not installed"
    echo "   Please install PostgreSQL:"
    echo "   - macOS: brew install postgresql"
    echo "   - Ubuntu: sudo apt-get install postgresql"
    echo "   - Or download from: https://www.postgresql.org/download/"
    exit 1
fi

# Check if PostgreSQL is running
if ! pg_isready -q; then
    echo "⚠️  PostgreSQL is not running"
    echo "   Starting PostgreSQL..."
    
    # Try to start PostgreSQL (macOS)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew services start postgresql 2>/dev/null || pg_ctl -D /usr/local/var/postgres start 2>/dev/null
    fi
    
    # Wait a bit for PostgreSQL to start
    sleep 2
    
    if ! pg_isready -q; then
        echo "❌ Failed to start PostgreSQL"
        echo "   Please start PostgreSQL manually and run this script again"
        exit 1
    fi
fi

echo "✅ PostgreSQL is running"

# Create database if it doesn't exist
DB_NAME="resume_tailor"
DB_USER="${POSTGRES_USER:-postgres}"
DB_PASSWORD="${POSTGRES_PASSWORD:-postgres}"

echo ""
echo "Creating database '$DB_NAME' if it doesn't exist..."

# Set PGPASSWORD to avoid password prompt
export PGPASSWORD="$DB_PASSWORD"

psql -U "$DB_USER" -h localhost -c "CREATE DATABASE $DB_NAME;" 2>/dev/null || echo "Database already exists or error occurred"

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

# Check if dependencies are installed
echo ""
echo "Checking dependencies..."
if ! python -c "import sqlalchemy" 2>/dev/null; then
    echo "❌ SQLAlchemy is not installed"
    echo "   Installing dependencies..."
    pip install -r requirements.txt
fi

if ! python -c "import alembic" 2>/dev/null; then
    echo "❌ Alembic is not installed"
    echo "   Installing dependencies..."
    pip install -r requirements.txt
fi

echo "✅ Dependencies installed"

# Run migrations
echo ""
echo "=========================================="
echo "Running database migrations..."
echo "=========================================="

# Set DATABASE_URL for Alembic
export DATABASE_URL="postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME"
export DATABASE_URL_SYNC="postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME"

# Run migrations
python -m alembic upgrade head

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Database setup complete!"
    echo ""
    echo "Database connection details:"
    echo "  Host: localhost"
    echo "  Port: 5432"
    echo "  Database: $DB_NAME"
    echo "  User: $DB_USER"
    echo ""
    echo "You can now start the application with:"
    echo "  python -m uvicorn api.main:app --reload"
else
    echo ""
    echo "❌ Database migration failed"
    echo "   Please check the error messages above"
    exit 1
fi

