# core/settings.py
import os

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

JOB_TTL_SECONDS = int(os.getenv("JOB_TTL_SECONDS", "3600"))
VERSION_TTL_SECONDS = int(os.getenv("VERSION_TTL_SECONDS", "86400"))  # 24 hours

# File upload limits
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# File security settings
ENABLE_VIRUS_SCAN = os.getenv("ENABLE_VIRUS_SCAN", "true").lower() == "true"
CLAMAV_SOCKET = os.getenv("CLAMAV_SOCKET", "/var/run/clamav/clamd.ctl")
ENABLE_HEURISTIC_SCAN = os.getenv("ENABLE_HEURISTIC_SCAN", "true").lower() == "true"

# Rate limiting
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "3600"))  # 1 hour

# Caching TTLs (in seconds)
CACHE_JD_TTL = int(os.getenv("CACHE_JD_TTL", "3600"))  # 1 hour
CACHE_REWRITE_TTL = int(os.getenv("CACHE_REWRITE_TTL", "7200"))  # 2 hours
CACHE_ATS_TTL = int(os.getenv("CACHE_ATS_TTL", "7200"))  # 2 hours
CACHE_NORMALIZED_TTL = int(os.getenv("CACHE_NORMALIZED_TTL", "86400"))  # 24 hours

# Redis connection pool settings
REDIS_MAX_CONNECTIONS = int(os.getenv("REDIS_MAX_CONNECTIONS", "50"))
REDIS_CONNECTION_TIMEOUT = int(os.getenv("REDIS_CONNECTION_TIMEOUT", "5"))
REDIS_SOCKET_TIMEOUT = int(os.getenv("REDIS_SOCKET_TIMEOUT", "5"))
REDIS_HEALTH_CHECK_INTERVAL = int(os.getenv("REDIS_HEALTH_CHECK_INTERVAL", "30"))

# PostgreSQL settings
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/resume_tailor"
)
# Sync database URL for Alembic migrations
DATABASE_URL_SYNC = os.getenv(
    "DATABASE_URL_SYNC",
    "postgresql://postgres:postgres@localhost:5432/resume_tailor"
)
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
DB_ECHO = os.getenv("DB_ECHO", "false").lower() == "true"
