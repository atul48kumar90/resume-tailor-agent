# core/cache_async.py
"""
Async Redis cache operations for better concurrency.
"""
import json
import hashlib
import os
import logging
from typing import Optional, Dict, Any
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

# Async Redis client with connection pooling
from core.redis_pool import get_async_client, is_async_available, close_async_client


async def get_redis_client(redis_client_instance: Optional[aioredis.Redis] = None) -> Optional[aioredis.Redis]:
    """
    Get async Redis client from connection pool.
    
    Args:
        redis_client_instance: Optional Redis client (for dependency injection)
    
    Returns:
        Redis client or None
    """
    if redis_client_instance:
        return redis_client_instance
    return await get_async_client()


def _hash(text: str) -> str:
    """Generate SHA256 hash for cache keys."""
    return hashlib.sha256(text.encode()).hexdigest()


def _get_cache_key(prefix: str, *args: str) -> str:
    """Generate cache key from prefix and arguments."""
    combined = "|".join(args)
    return f"{prefix}:{_hash(combined)}"


async def _safe_get(key: str, redis_client_instance: Optional[aioredis.Redis] = None) -> Optional[Any]:
    """
    Safely get value from cache, return None on error.
    
    Args:
        key: Cache key
        redis_client_instance: Optional Redis client (for dependency injection)
    
    Returns:
        Cached value or None
    """
    import asyncio
    
    # Check if event loop is available and not closed
    try:
        loop = asyncio.get_running_loop()
        if loop.is_closed():
            logger.warning(f"Event loop is closed, cannot get cache for key {key}")
            return None
    except RuntimeError:
        # No running loop, might be in sync context
        logger.warning(f"No running event loop, cannot get cache for key {key}")
        return None
    
    try:
        client = await get_redis_client(redis_client_instance)
        if not client:
            return None
        data = await client.get(key)
        return json.loads(data) if data else None
    except (RuntimeError, asyncio.CancelledError) as e:
        # Event loop issues
        logger.warning(f"Async cache get failed for key {key} (event loop issue): {e}")
        return None
    except Exception as e:
        logger.warning(f"Async cache get failed for key {key}: {e}")
        return None


async def _safe_set(key: str, value: Any, ttl: int = 3600, redis_client_instance: Optional[aioredis.Redis] = None) -> bool:
    """
    Safely set value in cache, return False on error.
    
    Args:
        key: Cache key
        value: Value to cache
        ttl: Time to live in seconds
        redis_client_instance: Optional Redis client (for dependency injection)
    
    Returns:
        True if successful, False otherwise
    """
    import asyncio
    
    # Check if event loop is available and not closed
    try:
        loop = asyncio.get_running_loop()
        if loop.is_closed():
            logger.warning(f"Event loop is closed, cannot set cache for key {key}")
            return False
    except RuntimeError:
        # No running loop, might be in sync context
        logger.warning(f"No running event loop, cannot set cache for key {key}")
        return False
    
    try:
        client = await get_redis_client(redis_client_instance)
        if not client:
            return False
        await client.setex(key, ttl, json.dumps(value))
        return True
    except (RuntimeError, asyncio.CancelledError) as e:
        # Event loop issues
        logger.warning(f"Async cache set failed for key {key} (event loop issue): {e}")
        return False
    except Exception as e:
        logger.warning(f"Async cache set failed for key {key}: {e}")
        return False


# =========================================================
# JD Analysis Cache (Async)
# =========================================================

async def get_cached_jd_async(jd_text: str) -> Optional[Dict[str, Any]]:
    """Get cached JD analysis result."""
    key = _get_cache_key("jd", jd_text)
    return await _safe_get(key)


async def set_cached_jd_async(jd_text: str, value: dict, ttl: int = 3600) -> bool:
    """Cache JD analysis result."""
    key = _get_cache_key("jd", jd_text)
    return await _safe_set(key, value, ttl)


# =========================================================
# Resume Rewrite Cache (Async)
# =========================================================

async def get_cached_rewrite_async(resume_text: str, jd_keywords_hash: str) -> Optional[Dict[str, Any]]:
    """Get cached resume rewrite result."""
    key = _get_cache_key("rewrite", resume_text, jd_keywords_hash)
    return await _safe_get(key)


async def set_cached_rewrite_async(
    resume_text: str,
    jd_keywords_hash: str,
    value: dict,
    ttl: int = 7200,
) -> bool:
    """Cache resume rewrite result."""
    key = _get_cache_key("rewrite", resume_text, jd_keywords_hash)
    return await _safe_set(key, value, ttl)


# =========================================================
# ATS Score Cache (Async)
# =========================================================

async def get_cached_ats_score_async(resume_text: str, jd_keywords_hash: str) -> Optional[Dict[str, Any]]:
    """Get cached ATS score result."""
    key = _get_cache_key("ats", resume_text, jd_keywords_hash)
    return await _safe_get(key)


async def set_cached_ats_score_async(
    resume_text: str,
    jd_keywords_hash: str,
    value: dict,
    ttl: int = 7200,
) -> bool:
    """Cache ATS score result."""
    key = _get_cache_key("ats", resume_text, jd_keywords_hash)
    return await _safe_set(key, value, ttl)


# =========================================================
# Resume Parse Cache (Async)
# =========================================================

async def get_cached_resume_parse(resume_hash: str, redis_client_instance: Optional[aioredis.Redis] = None) -> Optional[Dict[str, Any]]:
    """Get cached resume parse result."""
    key = f"resume_parse:{resume_hash}"
    return await _safe_get(key, redis_client_instance)


async def set_cached_resume_parse(
    resume_hash: str,
    value: dict,
    ttl: int = 86400,  # 24 hours
    redis_client_instance: Optional[aioredis.Redis] = None
) -> bool:
    """Cache resume parse result."""
    key = f"resume_parse:{resume_hash}"
    return await _safe_set(key, value, ttl, redis_client_instance)


# =========================================================
# Helper: Hash JD Keywords
# =========================================================

def hash_jd_keywords(jd_keywords: Dict[str, Any]) -> str:
    """Generate hash for JD keywords dict for cache key."""
    sorted_dict = json.dumps(jd_keywords, sort_keys=True)
    return _hash(sorted_dict)

