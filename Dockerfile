# Multi-stage Dockerfile for Resume Tailor Agent
# Combines frontend (React) and backend (FastAPI) in a single container

# ============================================
# Stage 1: Build Frontend
# ============================================
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy package files
COPY frontend/package*.json ./

# Install all dependencies (including devDependencies for build)
RUN npm ci

# Copy frontend source
COPY frontend/ .

# Build frontend (outputs to frontend/dist)
# Set API URL to relative path for production (served from same domain)
ENV VITE_API_URL=""
RUN npm run build

# ============================================
# Stage 2: Backend with Frontend Static Files
# ============================================
FROM python:3.11-slim AS backend

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install system dependencies
# pdfplumber requires additional system libraries
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libmagic1 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Create app user (non-root for security)
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/static && \
    chown -R appuser:appuser /app

WORKDIR /app

# Copy requirements and install Python dependencies
COPY --chown=appuser:appuser backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY --chown=appuser:appuser backend/ .

# Copy frontend build from previous stage to static directory
COPY --from=frontend-builder --chown=appuser:appuser /app/frontend/dist ./static

# Make startup script executable
RUN chmod +x scripts/start.sh

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start using startup script (runs migrations first)
CMD ["/app/scripts/start.sh"]

