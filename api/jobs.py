# api/jobs.py
import uuid
import logging
from typing import Dict

logger = logging.getLogger(__name__)

JOB_STORE: Dict[str, dict] = {}


def create_job() -> str:
    job_id = str(uuid.uuid4())
    JOB_STORE[job_id] = {
        "status": "pending",
        "result": None,
        "error": None,
    }
    logger.info(f"Job created: {job_id}")
    return job_id


def update_job(job_id: str, result: dict):
    JOB_STORE[job_id]["status"] = "completed"
    JOB_STORE[job_id]["result"] = result
    logger.info(f"Job completed: {job_id}")


def fail_job(job_id: str, error: str):
    JOB_STORE[job_id]["status"] = "failed"
    JOB_STORE[job_id]["error"] = error
    logger.error(f"Job failed: {job_id} | error={error}")


def get_job(job_id: str) -> dict | None:
    return JOB_STORE.get(job_id)
