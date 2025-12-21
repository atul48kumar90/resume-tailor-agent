# -------------------------
# Base Image
# -------------------------
    FROM python:3.14-slim

    # -------------------------
    # Environment
    # -------------------------
    ENV PYTHONDONTWRITEBYTECODE=1
    ENV PYTHONUNBUFFERED=1
    
    # -------------------------
    # System dependencies
    # -------------------------
    RUN apt-get update && apt-get install -y \
        build-essential \
        curl \
        && rm -rf /var/lib/apt/lists/*
    
    # -------------------------
    # Create app user
    # -------------------------
    RUN useradd -m appuser
    WORKDIR /app
    USER appuser
    
    # -------------------------
    # Install Python deps
    # -------------------------
    COPY --chown=appuser:appuser requirements.txt .
    RUN pip install --no-cache-dir --upgrade pip \
        && pip install --no-cache-dir -r requirements.txt
    
    # -------------------------
    # Copy application code
    # -------------------------
    COPY --chown=appuser:appuser . .
    
    # -------------------------
    # Expose port
    # -------------------------
    EXPOSE 8000
    
    # -------------------------
    # Start server
    # -------------------------
    CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

    