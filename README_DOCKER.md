# Docker Deployment Quick Start

This guide provides quick instructions for deploying the Resume Tailor Agent using Docker.

## 🚀 Quick Start

### 1. Prerequisites
- Docker and Docker Compose installed
- OpenAI API key

### 2. Setup Environment

Create a `.env` file in the project root:

```bash
OPENAI_API_KEY=your_openai_api_key_here
POSTGRES_PASSWORD=postgres
```

### 3. Build and Run

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### 4. Run Migrations

```bash
docker-compose exec app alembic upgrade head
```

### 5. Access Application

- **Application**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 📋 Services

The `docker-compose.yml` includes:

1. **app**: Frontend + Backend (single container)
2. **worker**: RQ worker for background jobs
3. **postgres**: PostgreSQL database
4. **redis**: Redis cache and job queue

## 🔧 Common Commands

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f app

# Execute commands in container
docker-compose exec app bash

# Run migrations
docker-compose exec app alembic upgrade head

# Restart a service
docker-compose restart app
```

## 🌐 Production Deployment

For production deployment to Google Cloud, see [DEPLOYMENT.md](./DEPLOYMENT.md).

### Quick Deploy to Cloud Run

```bash
# Set your project
export GOOGLE_CLOUD_PROJECT=your-project-id
export OPENAI_API_KEY=your-key

# Deploy
./scripts/deploy.sh cloud-run
```

## 🐛 Troubleshooting

### Port already in use
```bash
# Stop existing containers
docker-compose down

# Or change ports in docker-compose.yml
```

### Database connection errors
```bash
# Check if postgres is running
docker-compose ps

# Check postgres logs
docker-compose logs postgres
```

### Frontend not loading
- Ensure static files are built: Check `backend/static/` directory exists
- Check browser console for errors
- Verify CORS settings in environment variables

## 📚 More Information

- Full deployment guide: [DEPLOYMENT.md](./DEPLOYMENT.md)
- Makefile commands: `make help` or see [Makefile](./Makefile)

