.PHONY: build up down logs restart clean migrate test

# Docker Compose commands
build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

restart:
	docker-compose restart

# Database commands
migrate:
	docker-compose exec app alembic upgrade head

migrate-create:
	docker-compose exec app alembic revision --autogenerate -m "$(msg)"

# Development commands
dev-backend:
	cd backend && python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev

# Testing
test:
	docker-compose exec app python -m pytest

# Cleanup
clean:
	docker-compose down -v
	docker system prune -f

# Production build
build-prod:
	docker build -t resume-tailor:latest .

# Health check
health:
	curl http://localhost:8000/health

