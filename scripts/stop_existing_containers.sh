#!/bin/bash

# Script to stop existing containers that might be using ports

echo "🛑 Stopping existing containers..."

# Stop any existing resume-tailor containers
docker ps -a --filter "name=resume-tailor" --format "{{.Names}}" | xargs -r docker stop
docker ps -a --filter "name=resume-tailor" --format "{{.Names}}" | xargs -r docker rm

# Check for containers using port 5432
echo "🔍 Checking for containers using port 5432..."
PORTS_5432=$(docker ps --format "{{.Names}}" | xargs -I {} docker port {} 2>/dev/null | grep ":5432" || true)
if [ -n "$PORTS_5432" ]; then
  echo "⚠️  Found containers using port 5432:"
  echo "$PORTS_5432"
  echo "💡 You may need to stop them manually or use a different port"
fi

echo "✅ Done!"

