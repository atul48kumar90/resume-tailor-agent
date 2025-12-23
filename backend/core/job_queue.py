# core/job_queue.py
"""
Background job queue using RQ (Redis Queue).

Provides better job tracking, retries, and monitoring compared to FastAPI BackgroundTasks.
"""
import logging
from typing import Optional, Dict, Any
from rq import Queue, Retry
from rq.job import Job
from core.redis_pool import get_sync_client, is_sync_available

logger = logging.getLogger(__name__)

# Job queues - different queues for different priorities
_queues: Dict[str, Queue] = {}
_default_queue: Optional[Queue] = None
_rq_redis_client: Optional[object] = None


def get_rq_redis_client():
    """
    Get Redis client for RQ (with decode_responses=False).
    RQ requires binary mode because it stores pickled Python objects.
    """
    global _rq_redis_client
    
    if _rq_redis_client is not None:
        return _rq_redis_client
    
    from core.settings import REDIS_HOST, REDIS_PORT, REDIS_DB
    import redis
    
    try:
        _rq_redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            decode_responses=False,  # RQ needs binary mode for pickled data
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        # Test connection
        _rq_redis_client.ping()
        return _rq_redis_client
    except Exception as e:
        logger.error(f"Failed to create RQ Redis client: {e}")
        return None


def get_queue(queue_name: str = "default") -> Optional[Queue]:
    """
    Get or create RQ queue.
    
    Args:
        queue_name: Queue name (default, high_priority, low_priority)
    
    Returns:
        RQ Queue instance or None if Redis unavailable
    """
    global _queues, _default_queue
    
    if queue_name in _queues:
        return _queues[queue_name]
    
    # RQ requires decode_responses=False because it stores pickled Python objects
    rq_redis_client = get_rq_redis_client()
    if not rq_redis_client:
        logger.error("Redis not available, cannot create job queue")
        return None
    
    try:
        queue = Queue(queue_name, connection=rq_redis_client)
        _queues[queue_name] = queue
        
        if queue_name == "default":
            _default_queue = queue
        
        logger.info(f"Job queue '{queue_name}' created")
        return queue
    except Exception as e:
        logger.error(f"Failed to create job queue '{queue_name}': {e}")
        return None


def enqueue_job(
    func,
    *args,
    queue_name: str = "default",
    job_id: Optional[str] = None,
    job_timeout: str = "10m",
    retry: Optional[Retry] = None,
    **kwargs
) -> Optional[Job]:
    """
    Enqueue a job for background processing.
    
    Args:
        func: Function to execute
        *args: Positional arguments for function
        queue_name: Queue name (default, high_priority, low_priority)
        job_id: Optional job ID (for tracking)
        job_timeout: Job timeout (default: 10 minutes)
        retry: Retry configuration
        **kwargs: Keyword arguments for function
    
    Returns:
        RQ Job instance or None if enqueue failed
    """
    queue = get_queue(queue_name)
    if not queue:
        logger.error(f"Cannot enqueue job: queue '{queue_name}' not available")
        return None
    
    try:
        # Default retry: 3 attempts with exponential backoff
        if retry is None:
            retry = Retry(max=3, interval=[10, 30, 60])
        
        job = queue.enqueue(
            func,
            *args,
            job_id=job_id,
            job_timeout=job_timeout,
            retry=retry,
            **kwargs
        )
        
        if job:
            logger.info(f"Job enqueued: {job.id} in queue '{queue_name}' (requested job_id: {job_id})")
            if job.id != job_id:
                logger.warning(f"Job ID mismatch: requested {job_id}, got {job.id}")
        else:
            logger.error(f"Failed to enqueue job with ID {job_id}")
        
        return job
    except Exception as e:
        logger.error(f"Failed to enqueue job: {e}")
        return None


def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Get job status and result.
    
    Args:
        job_id: Job ID
    
    Returns:
        Dict with job status, result, error, or None if not found
    """
    # RQ requires decode_responses=False for proper pickling/unpickling
    rq_redis_client = get_rq_redis_client()
    if not rq_redis_client:
        return None
    
    try:
        job = Job.fetch(job_id, connection=rq_redis_client)
        
        # Get raw status from RQ
        raw_status = job.get_status()
        
        status = {
            "job_id": job.id,
            "status": raw_status,  # Will be normalized below
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "ended_at": job.ended_at.isoformat() if job.ended_at else None,
        }
        
        # Log status for debugging
        logger.debug(f"Job {job_id} raw RQ status: {raw_status}, is_finished: {job.is_finished}, is_started: {job.is_started}, is_queued: {job.is_queued}")
        
        if job.is_finished:
            # Safely get result - handle pickled/binary data
            try:
                result = job.result
                # Try to serialize result to JSON-compatible format
                if result is not None:
                    # If result is already a dict/list/primitive, use it directly
                    if isinstance(result, (dict, list, str, int, float, bool, type(None))):
                        status["result"] = result
                    else:
                        # For complex objects, try to convert to dict or string
                        try:
                            import json
                            # Try JSON serialization
                            json.dumps(result)
                            status["result"] = result
                        except (TypeError, ValueError):
                            # If not JSON serializable, convert to string representation
                            status["result"] = str(result)
                else:
                    status["result"] = None
                # Normalize: RQ uses "finished" but we use "completed" for consistency
                status["status"] = "completed"
            except (UnicodeDecodeError, ValueError, TypeError) as e:
                # Handle encoding/decoding errors
                logger.warning(f"Failed to decode job result for {job_id}: {e}")
                status["result"] = None
                status["status"] = "completed"
                status["error"] = "Result could not be decoded"
        elif job.is_failed:
            try:
                error_info = str(job.exc_info) if job.exc_info else "Unknown error"
                status["error"] = error_info
            except (UnicodeDecodeError, ValueError) as e:
                logger.warning(f"Failed to decode job error for {job_id}: {e}")
                status["error"] = "Error information could not be decoded"
            status["status"] = "failed"
        elif job.is_started:
            status["status"] = "processing"
        elif job.is_queued:
            status["status"] = "queued"
        else:
            status["status"] = "pending"
        
        return status
    except Job.DoesNotExist:
        logger.debug(f"RQ job {job_id} does not exist in RQ (may not be enqueued yet)")
        return None
    except Exception as e:
        logger.warning(f"Failed to get job status for {job_id}: {e}", exc_info=True)
        return None


def cancel_job(job_id: str) -> bool:
    """
    Cancel a queued job.
    
    Args:
        job_id: Job ID
    
    Returns:
        True if cancelled, False otherwise
    """
    rq_redis_client = get_rq_redis_client()
    if not rq_redis_client:
        return False
    
    try:
        job = Job.fetch(job_id, connection=rq_redis_client)
        job.cancel()
        logger.info(f"Job cancelled: {job_id}")
        return True
    except Exception as e:
        logger.warning(f"Failed to cancel job {job_id}: {e}")
        return False


def get_queue_stats(queue_name: str = "default") -> Dict[str, Any]:
    """
    Get queue statistics.
    
    Args:
        queue_name: Queue name
    
    Returns:
        Dict with queue statistics
    """
    queue = get_queue(queue_name)
    if not queue:
        return {"error": "Queue not available"}
    
    try:
        return {
            "queue_name": queue_name,
            "queued": len(queue),
            "started": len(queue.started_job_registry),
            "finished": len(queue.finished_job_registry),
            "failed": len(queue.failed_job_registry),
        }
    except Exception as e:
        logger.error(f"Failed to get queue stats: {e}")
        return {"error": str(e)}

