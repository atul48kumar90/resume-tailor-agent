# Deployment Guide - Resume Tailor Agent

This guide covers deploying the Resume Tailor Agent application using Docker.

## Architecture

The application consists of:
- **Frontend**: React + TypeScript + Vite (served as static files)
- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL
- **Cache/Queue**: Redis
- **Worker**: RQ worker for background jobs

## Quick Start (Local Development)

### Prerequisites
- Docker and Docker Compose installed
- OpenAI API key

### 1. Set Environment Variables

Create a `.env` file in the project root:

```bash
# Required
OPENAI_API_KEY=your_openai_api_key_here

# Optional (defaults provided)
POSTGRES_PASSWORD=postgres
REDIS_HOST=redis
REDIS_PORT=6379
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/resume_tailor
```

### 2. Build and Run

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### 3. Run Database Migrations

```bash
# Execute migrations inside the app container
docker-compose exec app alembic upgrade head
```

### 4. Access Application

- **Frontend + API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Production Deployment

### Option 1: Google Cloud Run (Recommended)

#### Prerequisites
- Google Cloud SDK installed (`gcloud`)
- Docker installed
- Google Cloud project created

#### Steps

1. **Build and push to Google Container Registry**

```bash
# Set your project ID
export PROJECT_ID=your-project-id
export REGION=us-central1

# Build the image
docker build -t gcr.io/${PROJECT_ID}/resume-tailor:latest .

# Push to GCR
docker push gcr.io/${PROJECT_ID}/resume-tailor:latest
```

2. **Deploy to Cloud Run**

```bash
gcloud run deploy resume-tailor \
  --image gcr.io/${PROJECT_ID}/resume-tailor:latest \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --set-env-vars OPENAI_API_KEY=${OPENAI_API_KEY} \
  --set-env-vars DATABASE_URL=${DATABASE_URL} \
  --set-env-vars REDIS_HOST=${REDIS_HOST} \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 10
```

**Note**: For Cloud Run, you'll need:
- **Cloud SQL** for PostgreSQL (managed database)
- **Memorystore** for Redis (managed Redis)
- **Cloud Tasks** or separate Cloud Run service for RQ workers

### Option 2: Google Compute Engine (Single VM)

#### Prerequisites
- Google Cloud SDK installed
- SSH access to GCE instance

#### Steps

1. **Create a VM instance**

```bash
gcloud compute instances create resume-tailor-vm \
  --image-family=cos-stable \
  --image-project=cos-cloud \
  --machine-type=e2-medium \
  --boot-disk-size=20GB \
  --tags=http-server,https-server
```

2. **Install Docker on the VM**

```bash
# SSH into the VM
gcloud compute ssh resume-tailor-vm

# Install Docker (on COS)
sudo systemctl start docker
```

3. **Deploy using Docker Compose**

```bash
# Copy files to VM (using gcloud compute scp or git)
# Then on the VM:
docker-compose up -d
```

### Option 3: Google Kubernetes Engine (GKE)

For production at scale, use GKE with separate deployments for:
- Frontend + Backend (single container)
- RQ Worker
- PostgreSQL (Cloud SQL)
- Redis (Memorystore)

See `k8s/` directory for Kubernetes manifests (if available).

## Environment Variables

### Required
- `OPENAI_API_KEY`: Your OpenAI API key

### Database
- `DATABASE_URL`: PostgreSQL connection string (async)
- `DATABASE_URL_SYNC`: PostgreSQL connection string (sync, for migrations)
- `POSTGRES_PASSWORD`: PostgreSQL password

### Redis
- `REDIS_HOST`: Redis host (default: localhost)
- `REDIS_PORT`: Redis port (default: 6379)
- `REDIS_DB`: Redis database number (default: 0)

### Optional
- `CORS_ORIGINS`: Comma-separated list of allowed origins (default: localhost)
- `MAX_FILE_SIZE_MB`: Maximum file upload size (default: 10)
- `RATE_LIMIT_REQUESTS`: Rate limit requests per window (default: 100)
- `RATE_LIMIT_WINDOW`: Rate limit window in seconds (default: 3600)

## Database Setup

### Initial Migration

```bash
# Run migrations
docker-compose exec app alembic upgrade head

# Or manually
docker-compose exec app python -m alembic upgrade head
```

### Create Migration

```bash
docker-compose exec app alembic revision --autogenerate -m "description"
docker-compose exec app alembic upgrade head
```

## Monitoring & Logs

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f app
docker-compose logs -f worker
docker-compose logs -f postgres
docker-compose logs -f redis
```

### Health Checks

- Application: `http://localhost:8000/health`
- Database: Check via `docker-compose exec postgres pg_isready`
- Redis: Check via `docker-compose exec redis redis-cli ping`

## Scaling

### Horizontal Scaling (Multiple Instances)

For production, consider:
1. **Load Balancer**: Use Google Cloud Load Balancer
2. **Multiple App Instances**: Deploy multiple containers
3. **Shared Redis**: Use managed Redis (Memorystore)
4. **Shared Database**: Use managed PostgreSQL (Cloud SQL)
5. **Worker Scaling**: Deploy multiple RQ worker instances

### Vertical Scaling

Increase resources:
- **Memory**: Increase `--memory` flag in Cloud Run
- **CPU**: Increase `--cpu` flag in Cloud Run
- **VM Size**: Use larger machine types in GCE/GKE

## Security Considerations

1. **Environment Variables**: Never commit `.env` files
2. **API Keys**: Use Google Secret Manager for production
3. **Database**: Use strong passwords, enable SSL
4. **CORS**: Restrict origins in production
5. **HTTPS**: Always use HTTPS in production
6. **Firewall**: Restrict database/Redis access to app only

## Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs app

# Check if ports are available
netstat -an | grep 8000
```

### Database connection issues
```bash
# Test database connection
docker-compose exec app python -c "from db.database import test_connection; test_connection()"
```

### Redis connection issues
```bash
# Test Redis connection
docker-compose exec redis redis-cli ping
```

### Frontend not loading
- Check if static files are built: `ls -la backend/static/`
- Check browser console for errors
- Verify CORS settings

## Backup & Recovery

### Database Backup
```bash
# Backup
docker-compose exec postgres pg_dump -U postgres resume_tailor > backup.sql

# Restore
docker-compose exec -T postgres psql -U postgres resume_tailor < backup.sql
```

### Redis Backup
```bash
# Redis data is persisted in volume, but you can also:
docker-compose exec redis redis-cli SAVE
```

## Cost Optimization

1. **Use Cloud SQL**: Managed PostgreSQL (pay per use)
2. **Use Memorystore**: Managed Redis (pay per use)
3. **Cloud Run**: Pay per request (good for variable traffic)
4. **GCE**: Fixed cost, good for consistent traffic
5. **Auto-scaling**: Configure based on traffic patterns

## Next Steps

1. Set up monitoring (Cloud Monitoring, Prometheus)
2. Configure alerts for errors/high latency
3. Set up CI/CD pipeline
4. Configure auto-scaling
5. Set up backup strategy
6. Configure SSL/TLS certificates

