#!/bin/bash
# check_dependencies.sh - Check if all required dependencies are installed

echo "=========================================="
echo "Checking Test Dependencies"
echo "=========================================="

MISSING=0

# Check for curl
if command -v curl &> /dev/null; then
    echo "✅ curl is installed ($(curl --version | head -n1))"
else
    echo "❌ curl is NOT installed"
    echo "   Install: brew install curl (macOS) or apt-get install curl (Linux)"
    ((MISSING++))
fi

# Check for jq
if command -v jq &> /dev/null; then
    echo "✅ jq is installed ($(jq --version))"
else
    echo "⚠️  jq is NOT installed (optional but recommended)"
    echo "   Install: brew install jq (macOS) or apt-get install jq (Linux)"
    echo "   Tests will run but JSON validation will be limited"
fi

# Check for bash
if command -v bash &> /dev/null; then
    BASH_VERSION=$(bash --version | head -n1)
    echo "✅ bash is installed ($BASH_VERSION)"
else
    echo "❌ bash is NOT installed"
    ((MISSING++))
fi

# Check if API is running
echo ""
echo "Checking API connectivity..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ API is running on http://localhost:8000"
else
    echo "⚠️  API is NOT running on http://localhost:8000"
    echo "   Start with: uvicorn api.main:app --reload"
fi

# Check if Redis is running
echo ""
echo "Checking Redis connectivity..."
if command -v redis-cli &> /dev/null; then
    if redis-cli ping > /dev/null 2>&1; then
        echo "✅ Redis is running"
    else
        echo "⚠️  Redis is NOT running"
        echo "   Start with: redis-server"
    fi
else
    echo "⚠️  redis-cli not found (Redis may not be installed)"
fi

echo ""
if [ $MISSING -eq 0 ]; then
    echo "✅ All required dependencies are installed!"
    exit 0
else
    echo "❌ Some required dependencies are missing"
    exit 1
fi

