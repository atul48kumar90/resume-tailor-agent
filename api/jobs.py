# api/jobs.py
import json
import uuid
import logging
import redis
from typing import Optional
from core.settings import (
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
    JOB_TTL_SECONDS,
)

logger = logging.getLogger(__name__)

# Redis client with connection pooling and error handling
try:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True,
        health_check_interval=30,
    )
    # Test connection
    redis_client.ping()
    logger.info("Redis connection established")
except (redis.ConnectionError, redis.TimeoutError) as e:
    logger.error(f"Failed to connect to Redis: {e}")
    redis_client = None


def _job_key(job_id: str) -> str:
    return f"job:{job_id}"


def create_job() -> str:
    """Create a new job with error handling."""
    if not redis_client:
        logger.error("Redis not available, cannot create job")
        raise RuntimeError("Redis connection not available")
    
    job_id = str(uuid.uuid4())
    data = {
        "status": "pending",
        "result": None,
        "error": None,
    }
    try:
        redis_client.setex(
            _job_key(job_id),
            JOB_TTL_SECONDS,
            json.dumps(data),
        )
        logger.info(f"Job created: {job_id}")
        return job_id
    except (redis.RedisError, json.JSONEncodeError) as e:
        logger.error(f"Failed to create job: {e}")
        raise RuntimeError(f"Failed to create job: {e}")


def update_job(job_id: str, result: dict):
    """Update job with result, with error handling."""
    if not redis_client:
        logger.error("Redis not available, cannot update job")
        return
    
    data = {
        "status": "completed",
        "result": result,
        "error": None,
    }
    try:
        redis_client.setex(
            _job_key(job_id),
            JOB_TTL_SECONDS,
            json.dumps(data),
        )
        logger.info(f"Job completed: {job_id}")
    except (redis.RedisError, json.JSONEncodeError) as e:
        logger.error(f"Failed to update job {job_id}: {e}")


def fail_job(job_id: str, error: str):
    """Mark job as failed with error message."""
    if not redis_client:
        logger.error("Redis not available, cannot fail job")
        return
    
    data = {
        "status": "failed",
        "result": None,
        "error": error,
    }
    try:
        redis_client.setex(
            _job_key(job_id),
            JOB_TTL_SECONDS,
            json.dumps(data),
        )
        logger.error(f"Job failed: {job_id} | error={error}")
    except (redis.RedisError, json.JSONEncodeError) as e:
        logger.error(f"Failed to mark job {job_id} as failed: {e}")


def get_job(job_id: str) -> Optional[dict]:
    """Get job by ID with error handling."""
    if not redis_client:
        logger.error("Redis not available, cannot get job")
        return None
    
    try:
        raw = redis_client.get(_job_key(job_id))
        if not raw:
            return None
        return json.loads(raw)
    except (redis.RedisError, json.JSONDecodeError) as e:
        logger.error(f"Failed to get job {job_id}: {e}")
        return None
