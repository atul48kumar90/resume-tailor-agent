#!/usr/bin/env python
"""
RQ Worker for processing background jobs.

Run this worker to process jobs from the queue:
    python -m workers.job_worker

Or use rq command:
    rq worker --url redis://localhost:6379/0
"""
import os
import sys
from pathlib import Path

# Fix macOS fork() issue with langchain/pydantic
# This must be set BEFORE any imports that might use Objective-C runtime
if sys.platform == "darwin":  # macOS
    os.environ.setdefault("OBJC_DISABLE_INITIALIZE_FORK_SAFETY", "YES")

# Add project root (backend/) to path - this is critical for RQ to import functions
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Also add parent directory in case we need to import from project root
parent_root = project_root.parent
if str(parent_root) not in sys.path:
    sys.path.insert(0, str(parent_root))

# Setup logging first
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Explicitly import the job functions to ensure they're available
# This helps RQ find them when deserializing jobs
try:
    from api.routes import process_resume_job, process_resume_files_job
    logger.info("Successfully imported job functions: process_resume_job, process_resume_files_job")
except ImportError as e:
    # If import fails, log error but continue - RQ will try to import on demand
    logger.warning(f"Could not pre-import job functions: {e}. RQ will attempt to import on demand.")
    logger.warning(f"Python path: {sys.path}")

from rq import Worker
from core.job_queue import get_queue, get_rq_redis_client


def main():
    """Start RQ worker."""
    # RQ requires decode_responses=False for pickled data
    redis_client = get_rq_redis_client()
    
    if not redis_client:
        logger.error("Redis not available, cannot start worker")
        sys.exit(1)
    
    # Listen to default queue
    queue = get_queue("default")
    
    if not queue:
        logger.error("Job queue not available, cannot start worker")
        sys.exit(1)
    
    logger.info("Starting RQ worker...")
    logger.info(f"Listening to queue: default")
    logger.info(f"Redis: {os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', '6379')}")
    logger.info(f"Python path: {sys.path[:3]}...")  # Show first 3 paths
    
    # Verify we can import the job functions (critical for RQ)
    try:
        from api.routes import process_resume_job, process_resume_files_job
        logger.info("✅ Verified: Job functions are importable")
        logger.info(f"   - process_resume_job: {process_resume_job.__module__}.{process_resume_job.__name__}")
        logger.info(f"   - process_resume_files_job: {process_resume_files_job.__module__}.{process_resume_files_job.__name__}")
    except ImportError as e:
        logger.error(f"❌ CRITICAL: Cannot import job functions: {e}")
        logger.error("   RQ will not be able to process jobs!")
        logger.error(f"   Current working directory: {os.getcwd()}")
        logger.error(f"   Project root: {project_root}")
        logger.error(f"   Python path: {sys.path}")
        sys.exit(1)
    
    # Check queue status
    try:
        queued_count = len(queue)
        logger.info(f"Jobs in queue: {queued_count}")
        if queued_count > 0:
            logger.info(f"Found {queued_count} job(s) waiting to be processed")
    except Exception as e:
        logger.warning(f"Could not check queue length: {e}")
    
    # Create worker with the queue (queue already has the connection)
    # In newer RQ versions, Connection context manager is not needed
    worker = Worker([queue], connection=redis_client)
    logger.info("Worker created, starting to process jobs...")
    worker.work()


if __name__ == "__main__":
    main()

