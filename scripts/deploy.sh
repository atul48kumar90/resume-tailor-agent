#!/bin/bash

# Deployment script for Resume Tailor Agent
# Usage: ./scripts/deploy.sh [environment]
# Environment: local, gce, cloud-run, gke

set -e

ENVIRONMENT=${1:-local}
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-""}
REGION=${GOOGLE_CLOUD_REGION:-"us-central1"}

echo "🚀 Deploying Resume Tailor Agent to: $ENVIRONMENT"

case $ENVIRONMENT in
  local)
    echo "📦 Building and starting local Docker Compose..."
    docker-compose build
    docker-compose up -d
    
    echo "⏳ Waiting for services to be ready..."
    sleep 10
    
    echo "🔄 Running database migrations..."
    docker-compose exec -T app alembic upgrade head || echo "⚠️  Migration failed, but continuing..."
    
    echo "✅ Deployment complete!"
    echo "🌐 Application: http://localhost:8000"
    echo "📚 API Docs: http://localhost:8000/docs"
    ;;
    
  gce)
    if [ -z "$PROJECT_ID" ]; then
      echo "❌ Error: GOOGLE_CLOUD_PROJECT must be set"
      exit 1
    fi
    
    echo "📦 Building Docker image..."
    docker build -t gcr.io/${PROJECT_ID}/resume-tailor:latest .
    
    echo "📤 Pushing to Google Container Registry..."
    docker push gcr.io/${PROJECT_ID}/resume-tailor:latest
    
    echo "✅ Image pushed. Deploy to GCE instance manually or use:"
    echo "   gcloud compute instances create-with-container resume-tailor-vm \\"
    echo "     --container-image=gcr.io/${PROJECT_ID}/resume-tailor:latest"
    ;;
    
  cloud-run)
    if [ -z "$PROJECT_ID" ]; then
      echo "❌ Error: GOOGLE_CLOUD_PROJECT must be set"
      exit 1
    fi
    
    if [ -z "$OPENAI_API_KEY" ]; then
      echo "❌ Error: OPENAI_API_KEY must be set"
      exit 1
    fi
    
    echo "📦 Building Docker image..."
    docker build -t gcr.io/${PROJECT_ID}/resume-tailor:latest .
    
    echo "📤 Pushing to Google Container Registry..."
    docker push gcr.io/${PROJECT_ID}/resume-tailor:latest
    
    echo "🚀 Deploying to Cloud Run..."
    gcloud run deploy resume-tailor \
      --image gcr.io/${PROJECT_ID}/resume-tailor:latest \
      --platform managed \
      --region ${REGION} \
      --allow-unauthenticated \
      --set-env-vars OPENAI_API_KEY=${OPENAI_API_KEY} \
      --memory 2Gi \
      --cpu 2 \
      --timeout 300 \
      --max-instances 10 \
      --port 8000
    
    echo "✅ Deployment complete!"
    ;;
    
  gke)
    echo "📦 Building and pushing Docker image..."
    if [ -z "$PROJECT_ID" ]; then
      echo "❌ Error: GOOGLE_CLOUD_PROJECT must be set"
      exit 1
    fi
    
    docker build -t gcr.io/${PROJECT_ID}/resume-tailor:latest .
    docker push gcr.io/${PROJECT_ID}/resume-tailor:latest
    
    echo "✅ Image pushed. Apply Kubernetes manifests:"
    echo "   kubectl apply -f k8s/"
    ;;
    
  *)
    echo "❌ Unknown environment: $ENVIRONMENT"
    echo "Usage: $0 [local|gce|cloud-run|gke]"
    exit 1
    ;;
esac

echo "🎉 Done!"

