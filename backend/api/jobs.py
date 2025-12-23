# api/jobs.py
"""
Job management with PostgreSQL (primary) and Redis (fallback).
"""
import json
import uuid
import logging
from typing import Optional
from uuid import UUID
from datetime import datetime

from core.settings import JOB_TTL_SECONDS
from core.redis_pool import get_sync_client, is_sync_available
from db.database import get_async_session
from db.repositories import create_job as create_job_db, get_job_by_id, update_job as update_job_db

logger = logging.getLogger(__name__)

# Redis client for fallback
redis_client = get_sync_client()
redis_available = is_sync_available()


def _job_key(job_id: str) -> str:
    return f"job:{job_id}"


async def create_job_async(rq_job_id: Optional[str] = None) -> str:
    """Create a new job in PostgreSQL (async)."""
    try:
        async with get_async_session() as session:
            job = await create_job_db(session, rq_job_id=rq_job_id)
            await session.commit()
            return str(job.id)
    except Exception as e:
        logger.error(f"Failed to create job in PostgreSQL: {e}", exc_info=True)
        # Fallback to Redis
        return create_job_redis()


def create_job() -> str:
    """
    Create a new job (sync wrapper).
    
    Since this is called from FastAPI sync routes (which run in thread pools)
    and the database engine is tied to FastAPI's event loop, we use Redis
    directly to avoid event loop conflicts. RQ workers also use Redis.
    
    For async endpoints, use create_job_async() directly.
    """
    # Always use Redis for sync function calls to avoid event loop conflicts
    # The database engine created in FastAPI's event loop cannot be safely
    # used from a new event loop in a sync function
    return create_job_redis()


def create_job_redis() -> str:
    """Create a new job in Redis (fallback)."""
    import redis
    
    if not redis_client or not redis_available:
        logger.error("Redis not available, cannot create job")
        raise RuntimeError("Neither PostgreSQL nor Redis available for job creation")
    
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
        logger.info(f"Job created in Redis: {job_id}")
        return job_id
    except (redis.RedisError, json.JSONEncodeError) as e:
        logger.error(f"Failed to create job in Redis: {e}")
        raise RuntimeError(f"Failed to create job: {e}")


async def update_job_async(job_id: str, result: dict):
    """Update job with result in PostgreSQL (async)."""
    try:
        job_uuid = UUID(job_id)
        async with get_async_session() as session:
            job = await update_job_db(
                session,
                job_uuid,
                status="completed",
                result=result,
                completed_at=datetime.utcnow()
            )
            if job:
                await session.commit()
                logger.info(f"Job completed in PostgreSQL: {job_id}")
                return
    except (ValueError, Exception) as e:
        logger.warning(f"Failed to update job in PostgreSQL: {e}, falling back to Redis")
    
    # Fallback to Redis
    update_job_redis(job_id, result)


def update_job(job_id: str, result: dict):
    """
    Update job with result (sync wrapper).
    
    Uses Redis to avoid event loop conflicts. For async endpoints,
    use update_job_async() directly.
    """
    update_job_redis(job_id, result)


def update_job_redis(job_id: str, result: dict):
    """Update job in Redis (fallback)."""
    import redis
    
    if not redis_client or not redis_available:
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
        logger.info(f"Job completed in Redis: {job_id}")
    except (redis.RedisError, json.JSONEncodeError) as e:
        logger.error(f"Failed to update job {job_id} in Redis: {e}")


async def fail_job_async(job_id: str, error: str):
    """Mark job as failed in PostgreSQL (async)."""
    try:
        job_uuid = UUID(job_id)
        async with get_async_session() as session:
            job = await update_job_db(
                session,
                job_uuid,
                status="failed",
                error=error,
                completed_at=datetime.utcnow()
            )
            if job:
                await session.commit()
                logger.error(f"Job failed in PostgreSQL: {job_id} | error={error}")
                return
    except (ValueError, Exception) as e:
        logger.warning(f"Failed to fail job in PostgreSQL: {e}, falling back to Redis")
    
    # Fallback to Redis
    fail_job_redis(job_id, error)


def fail_job(job_id: str, error: str):
    """
    Mark job as failed (sync wrapper).
    
    Uses Redis to avoid event loop conflicts. For async endpoints,
    use fail_job_async() directly.
    """
    fail_job_redis(job_id, error)


def fail_job_redis(job_id: str, error: str):
    """Mark job as failed in Redis (fallback)."""
    import redis
    
    if not redis_client or not redis_available:
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
        logger.error(f"Job failed in Redis: {job_id} | error={error}")
    except (redis.RedisError, json.JSONEncodeError) as e:
        logger.error(f"Failed to mark job {job_id} as failed in Redis: {e}")


async def get_job_async(job_id: str) -> Optional[dict]:
    """Get job by ID from PostgreSQL (async)."""
    try:
        job_uuid = UUID(job_id)
        async with get_async_session() as session:
            job = await get_job_by_id(session, job_uuid)
            if job:
                return {
                    "status": job.status,
                    "result": job.result,
                    "error": job.error,
                    "created_at": job.created_at.isoformat() if job.created_at else None,
                    "started_at": job.started_at.isoformat() if job.started_at else None,
                    "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                }
    except (ValueError, Exception) as e:
        logger.warning(f"Failed to get job from PostgreSQL: {e}, falling back to Redis")
    
    # Fallback to Redis
    return get_job_redis(job_id)


def get_job(job_id: str) -> Optional[dict]:
    """
    Get job by ID (sync wrapper).
    
    Uses Redis to avoid event loop conflicts. For async endpoints,
    use get_job_async() directly.
    """
    return get_job_redis(job_id)


def get_job_redis(job_id: str) -> Optional[dict]:
    """Get job from Redis (fallback)."""
    import redis
    
    if not redis_client or not redis_available:
        logger.error("Redis not available, cannot get job")
        return None
    
    try:
        raw = redis_client.get(_job_key(job_id))
        if not raw:
            return None
        return json.loads(raw)
    except (redis.RedisError, json.JSONDecodeError) as e:
        logger.error(f"Failed to get job {job_id} from Redis: {e}")
        return None
