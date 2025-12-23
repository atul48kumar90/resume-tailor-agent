#!/bin/bash
# install_dependencies.sh - Install all Python dependencies

# Don't exit on error - we'll handle failures manually
set +e

echo "=========================================="
echo "Installing Python Dependencies"
echo "=========================================="

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Creating virtual environment..."
    python3 -m venv .venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo ""
echo "Installing dependencies from requirements.txt..."
if pip install -r requirements.txt; then
    INSTALL_SUCCESS=true
else
    INSTALL_SUCCESS=false
    echo "⚠️  Some packages failed to install (may be optional)"
fi

# Verify critical dependencies
echo ""
echo "Verifying critical dependencies..."
CRITICAL_MISSING=0

if python -c "import sqlalchemy" 2>/dev/null; then
    echo "✅ sqlalchemy installed"
else
    echo "❌ sqlalchemy NOT installed - installing separately..."
    pip install sqlalchemy
    CRITICAL_MISSING=1
fi

if python -c "import asyncpg" 2>/dev/null; then
    echo "✅ asyncpg installed"
else
    echo "⚠️  asyncpg NOT installed - installing separately..."
    pip install asyncpg
fi

if python -c "import alembic" 2>/dev/null; then
    echo "✅ alembic installed"
else
    echo "⚠️  alembic NOT installed - installing separately..."
    pip install alembic
fi

if python -c "import uvicorn" 2>/dev/null; then
    echo "✅ uvicorn installed"
else
    echo "❌ uvicorn NOT installed - installing separately..."
    pip install uvicorn
    CRITICAL_MISSING=1
fi

echo ""
echo "=========================================="
if [ $CRITICAL_MISSING -eq 0 ]; then
    echo "✅ Dependencies installed successfully!"
else
    echo "⚠️  Some dependencies installed with warnings"
fi
echo "=========================================="
echo ""
echo "To activate the virtual environment:"
echo "  source .venv/bin/activate"
echo ""
echo "To verify installation:"
echo "  python -c 'import sqlalchemy; print(\"SQLAlchemy:\", sqlalchemy.__version__)'"
echo "  python -c 'import asyncpg; print(\"asyncpg installed\")'"
echo "  python -c 'import alembic; print(\"Alembic installed\")'"

