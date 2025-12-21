# core/settings.py
import os

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

JOB_TTL_SECONDS = int(os.getenv("JOB_TTL_SECONDS", "3600"))
