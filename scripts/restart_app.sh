#!/bin/bash

# Script to restart the app container and check logs

echo "🔄 Restarting app container..."
docker-compose restart app

echo "⏳ Waiting 5 seconds for app to start..."
sleep 5

echo "📋 App Container Logs (last 20 lines):"
echo "----------------------------------------"
docker logs resume-tailor-app --tail 20

echo ""
echo "🏥 Testing Health Endpoint:"
curl -s http://localhost:8000/health | head -20 || echo "❌ Health endpoint unreachable"

echo ""
echo "✅ Restart complete!"

