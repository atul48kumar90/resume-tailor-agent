# agents/resume_versions.py
import json
import uuid
import logging
import redis
from typing import Dict, Optional
from core.settings import (
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
    VERSION_TTL_SECONDS,
)

logger = logging.getLogger(__name__)

# Redis client with connection pooling
try:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True,
    )
    # Test connection
    redis_client.ping()
except (redis.ConnectionError, redis.TimeoutError) as e:
    logger.error(f"Failed to connect to Redis: {e}")
    redis_client = None


def _version_key(resume_id: str, version_id: str) -> str:
    return f"resume:{resume_id}:version:{version_id}"


def _pointer_key(resume_id: str) -> str:
    return f"resume:{resume_id}:pointer"


def _versions_list_key(resume_id: str) -> str:
    return f"resume:{resume_id}:versions"


def get_current_version(resume_id: str) -> Optional[Dict]:
    """
    Get the current version for a resume.
    
    Args:
        resume_id: Unique identifier for the resume session
    
    Returns:
        Current version dict or None if not found
    """
    if not redis_client:
        logger.error("Redis not available, cannot get version")
        return None
    
    try:
        pointer = redis_client.get(_pointer_key(resume_id))
        if pointer is None:
            return None
        
        version_id = redis_client.lindex(_versions_list_key(resume_id), int(pointer))
        if not version_id:
            return None
        
        version_data = redis_client.get(_version_key(resume_id, version_id))
        if not version_data:
            return None
        
        return json.loads(version_data)
    except (redis.RedisError, json.JSONDecodeError, ValueError) as e:
        logger.error(f"Error getting current version for resume {resume_id}: {e}")
        return None


def save_new_version(resume_id: str, parent: str, resume: Dict, change_summary: str) -> Optional[str]:
    """
    Save a new version of the resume.
    
    Args:
        resume_id: Unique identifier for the resume session
        parent: Parent version ID
        resume: Resume data dictionary
        change_summary: Description of changes
    
    Returns:
        New version ID or None if failed
    """
    if not redis_client:
        logger.error("Redis not available, cannot save version")
        return None
    
    try:
        version_id = f"v{uuid.uuid4().hex[:8]}"
        version_data = {
            "version_id": version_id,
            "parent": parent,
            "resume": resume,
            "summary": change_summary,
        }
        
        # Save version data
        redis_client.setex(
            _version_key(resume_id, version_id),
            VERSION_TTL_SECONDS,
            json.dumps(version_data),
        )
        
        # Get current pointer
        pointer = redis_client.get(_pointer_key(resume_id))
        if pointer is not None:
            pointer = int(pointer)
            # Trim versions list after current pointer (for undo/redo)
            versions_list = redis_client.lrange(_versions_list_key(resume_id), 0, pointer)
            redis_client.delete(_versions_list_key(resume_id))
            if versions_list:
                redis_client.rpush(_versions_list_key(resume_id), *versions_list)
        
        # Add new version to list
        redis_client.rpush(_versions_list_key(resume_id), version_id)
        redis_client.expire(_versions_list_key(resume_id), VERSION_TTL_SECONDS)
        
        # Update pointer
        new_pointer = redis_client.llen(_versions_list_key(resume_id)) - 1
        redis_client.setex(_pointer_key(resume_id), VERSION_TTL_SECONDS, str(new_pointer))
        
        logger.info(f"Saved new version {version_id} for resume {resume_id}")
        return version_id
    except (redis.RedisError, json.JSONEncodeError) as e:
        logger.error(f"Error saving version for resume {resume_id}: {e}")
        return None


def undo_version(resume_id: str) -> Optional[Dict]:
    """
    Undo to previous version.
    
    Args:
        resume_id: Unique identifier for the resume session
    
    Returns:
        Previous version dict or None if not found
    """
    if not redis_client:
        logger.error("Redis not available, cannot undo version")
        return None
    
    try:
        pointer = redis_client.get(_pointer_key(resume_id))
        if pointer is None:
            return None
        
        pointer = int(pointer)
        if pointer <= 0:
            return None
        
        new_pointer = pointer - 1
        redis_client.setex(_pointer_key(resume_id), VERSION_TTL_SECONDS, str(new_pointer))
        
        version_id = redis_client.lindex(_versions_list_key(resume_id), new_pointer)
        if not version_id:
            return None
        
        version_data = redis_client.get(_version_key(resume_id, version_id))
        if not version_data:
            return None
        
        logger.info(f"Undone to version {version_id} for resume {resume_id}")
        return json.loads(version_data)
    except (redis.RedisError, json.JSONDecodeError, ValueError) as e:
        logger.error(f"Error undoing version for resume {resume_id}: {e}")
        return None


def redo_version(resume_id: str) -> Optional[Dict]:
    """
    Redo to next version.
    
    Args:
        resume_id: Unique identifier for the resume session
    
    Returns:
        Next version dict or None if not found
    """
    if not redis_client:
        logger.error("Redis not available, cannot redo version")
        return None
    
    try:
        pointer = redis_client.get(_pointer_key(resume_id))
        if pointer is None:
            return None
        
        pointer = int(pointer)
        list_length = redis_client.llen(_versions_list_key(resume_id))
        
        if pointer >= list_length - 1:
            return None
        
        new_pointer = pointer + 1
        redis_client.setex(_pointer_key(resume_id), VERSION_TTL_SECONDS, str(new_pointer))
        
        version_id = redis_client.lindex(_versions_list_key(resume_id), new_pointer)
        if not version_id:
            return None
        
        version_data = redis_client.get(_version_key(resume_id, version_id))
        if not version_data:
            return None
        
        logger.info(f"Redone to version {version_id} for resume {resume_id}")
        return json.loads(version_data)
    except (redis.RedisError, json.JSONDecodeError, ValueError) as e:
        logger.error(f"Error redoing version for resume {resume_id}: {e}")
        return None
