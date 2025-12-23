import json
import hashlib
import redis
import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Redis client with connection pooling
from core.redis_pool import get_sync_client, is_sync_available

# Global Redis client (for backward compatibility - prefer dependency injection)
redis_client = get_sync_client()
_redis_available = is_sync_available()


def get_cache_redis_client() -> Optional[redis.Redis]:
    """
    Get Redis client for caching.
    
    For dependency injection, use api.dependencies.get_redis_sync() instead.
    """
    return get_sync_client()


def _hash(text: str) -> str:
    """Generate SHA256 hash for cache keys."""
    return hashlib.sha256(text.encode()).hexdigest()


def _get_cache_key(prefix: str, *args: str) -> str:
    """Generate cache key from prefix and arguments."""
    combined = "|".join(args)
    return f"{prefix}:{_hash(combined)}"


def _safe_get(key: str, redis_client_instance: Optional[redis.Redis] = None) -> Optional[Any]:
    """Safely get value from cache, return None on error."""
    client = redis_client_instance or redis_client
    if not _redis_available or not client:
        return None
    try:
        data = client.get(key)
        return json.loads(data) if data else None
    except Exception as e:
        logger.warning(f"Cache get failed for key {key}: {e}")
        return None


def _safe_set(key: str, value: Any, ttl: int = 3600, redis_client_instance: Optional[redis.Redis] = None) -> bool:
    """Safely set value in cache, return False on error."""
    client = redis_client_instance or redis_client
    if not _redis_available or not client:
        return False
    try:
        client.setex(key, ttl, json.dumps(value))
        return True
    except Exception as e:
        logger.warning(f"Cache set failed for key {key}: {e}")
        return False


# =========================================================
# JD Analysis Cache
# =========================================================

def get_cached_jd(jd_text: str) -> Optional[Dict[str, Any]]:
    """Get cached JD analysis result."""
    key = _get_cache_key("jd", jd_text)
    return _safe_get(key)


def set_cached_jd(jd_text: str, value: dict, ttl: int = 3600, redis_client_instance: Optional[redis.Redis] = None) -> bool:
    """
    Cache JD analysis result.
    
    Args:
        jd_text: Job description text
        value: JD analysis result to cache
        ttl: Time to live in seconds
        redis_client_instance: Optional Redis client (for dependency injection)
    
    Returns:
        True if successful, False otherwise
    """
    key = _get_cache_key("jd", jd_text)
    return _safe_set(key, value, ttl, redis_client_instance)


# =========================================================
# Resume Rewrite Cache
# =========================================================

def get_cached_rewrite(resume_text: str, jd_keywords_hash: str, redis_client_instance: Optional[redis.Redis] = None) -> Optional[Dict[str, Any]]:
    """
    Get cached resume rewrite result.
    
    Args:
        resume_text: Original resume text
        jd_keywords_hash: Hash of JD keywords dict (for cache key)
        redis_client_instance: Optional Redis client (for dependency injection)
    
    Returns:
        Cached rewrite result or None
    """
    key = _get_cache_key("rewrite", resume_text, jd_keywords_hash)
    return _safe_get(key, redis_client_instance)


def set_cached_rewrite(
    resume_text: str,
    jd_keywords_hash: str,
    value: dict,
    ttl: int = 7200,  # 2 hours
    redis_client_instance: Optional[redis.Redis] = None,
) -> bool:
    """
    Cache resume rewrite result.
    
    Args:
        resume_text: Original resume text
        jd_keywords_hash: Hash of JD keywords dict
        value: Rewrite result to cache
        ttl: Time to live in seconds
        redis_client_instance: Optional Redis client (for dependency injection)
    
    Returns:
        True if successful, False otherwise
    """
    key = _get_cache_key("rewrite", resume_text, jd_keywords_hash)
    return _safe_set(key, value, ttl, redis_client_instance)


# =========================================================
# ATS Score Cache
# =========================================================

def get_cached_ats_score(resume_text: str, jd_keywords_hash: str) -> Optional[Dict[str, Any]]:
    """
    Get cached ATS score result.
    
    Args:
        resume_text: Resume text
        jd_keywords_hash: Hash of JD keywords dict
    
    Returns:
        Cached ATS score result or None
    """
    key = _get_cache_key("ats", resume_text, jd_keywords_hash)
    return _safe_get(key)


def set_cached_ats_score(
    resume_text: str,
    jd_keywords_hash: str,
    value: dict,
    ttl: int = 7200,  # 2 hours
) -> bool:
    """Cache ATS score result."""
    key = _get_cache_key("ats", resume_text, jd_keywords_hash)
    return _safe_set(key, value, ttl)


# =========================================================
# Resume Text Preprocessing Cache
# =========================================================

def get_cached_normalized_text(raw_text: str) -> Optional[str]:
    """Get cached normalized resume text."""
    key = _get_cache_key("normalized", raw_text)
    return _safe_get(key)


def set_cached_normalized_text(raw_text: str, normalized_text: str, ttl: int = 86400) -> bool:
    """Cache normalized resume text (24 hours)."""
    key = _get_cache_key("normalized", raw_text)
    return _safe_set(key, normalized_text, ttl)


def get_cached_extracted_text(file_hash: str) -> Optional[str]:
    """
    Get cached extracted text from file.
    
    Args:
        file_hash: SHA256 hash of file content
    
    Returns:
        Cached extracted text or None
    """
    key = _get_cache_key("extracted", file_hash)
    return _safe_get(key)


def set_cached_extracted_text(file_hash: str, extracted_text: str, ttl: int = 86400) -> bool:
    """
    Cache extracted text from file.
    
    Args:
        file_hash: SHA256 hash of file content
        extracted_text: Extracted text
        ttl: Time to live in seconds (default: 24 hours)
    """
    key = _get_cache_key("extracted", file_hash)
    return _safe_set(key, extracted_text, ttl)


def get_cached_tokens(text: str) -> Optional[list]:
    """
    Get cached tokenized text.
    
    Args:
        text: Normalized text
    
    Returns:
        Cached list of tokens or None
    """
    key = _get_cache_key("tokens", text)
    return _safe_get(key)


def set_cached_tokens(text: str, tokens: list, ttl: int = 86400) -> bool:
    """
    Cache tokenized text.
    
    Args:
        text: Normalized text
        tokens: List of tokens
        ttl: Time to live in seconds (default: 24 hours)
    """
    key = _get_cache_key("tokens", text)
    return _safe_set(key, tokens, ttl)


# =========================================================
# Helper: Hash JD Keywords
# =========================================================

def hash_jd_keywords(jd_keywords: Dict[str, Any]) -> str:
    """Generate hash for JD keywords dict for cache key."""
    # Sort keys and values for consistent hashing
    sorted_dict = json.dumps(jd_keywords, sort_keys=True)
    return _hash(sorted_dict)
