# api/jobs.py
import json
import uuid
import logging
import redis
from core.settings import (
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
    JOB_TTL_SECONDS,
)

logger = logging.getLogger(__name__)

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    decode_responses=True,
)


def _job_key(job_id: str) -> str:
    return f"job:{job_id}"


def create_job() -> str:
    job_id = str(uuid.uuid4())
    data = {
        "status": "pending",
        "result": None,
        "error": None,
    }
    redis_client.setex(
        _job_key(job_id),
        JOB_TTL_SECONDS,
        json.dumps(data),
    )
    logger.info(f"Job created: {job_id}")
    return job_id


def update_job(job_id: str, result: dict):
    data = {
        "status": "completed",
        "result": result,
        "error": None,
    }
    redis_client.setex(
        _job_key(job_id),
        JOB_TTL_SECONDS,
        json.dumps(data),
    )
    logger.info(f"Job completed: {job_id}")


def fail_job(job_id: str, error: str):
    data = {
        "status": "failed",
        "result": None,
        "error": error,
    }
    redis_client.setex(
        _job_key(job_id),
        JOB_TTL_SECONDS,
        json.dumps(data),
    )
    logger.error(f"Job failed: {job_id} | error={error}")


def get_job(job_id: str) -> dict | None:
    raw = redis_client.get(_job_key(job_id))
    if not raw:
        return None
    return json.loads(raw)
