#!/bin/bash

# Script to check container status and diagnose issues

echo "🔍 Checking Docker containers..."
echo ""

# Check if containers are running
echo "📦 Container Status:"
docker ps --filter "name=resume-tailor" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

# Check app container logs
echo "📋 App Container Logs (last 30 lines):"
echo "----------------------------------------"
docker logs resume-tailor-app --tail 30
echo ""

# Check if port 8000 is listening
echo "🌐 Port 8000 Status:"
if lsof -i :8000 > /dev/null 2>&1; then
  echo "✅ Port 8000 is in use:"
  lsof -i :8000
else
  echo "❌ Port 8000 is not in use"
fi
echo ""

# Test health endpoint
echo "🏥 Testing Health Endpoint:"
curl -s http://localhost:8000/health || echo "❌ Health endpoint unreachable"
echo ""

# Check static files
echo "📁 Checking static files in container:"
docker exec resume-tailor-app ls -la /app/static/ 2>/dev/null || echo "❌ Cannot access container or static directory missing"
echo ""

# Check if app process is running
echo "🔄 Checking app process:"
docker exec resume-tailor-app ps aux | grep -E "uvicorn|python" | grep -v grep || echo "❌ App process not found"
echo ""

echo "✅ Diagnostic complete!"

