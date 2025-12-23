# api/dependencies.py
"""
FastAPI dependency injection for shared resources.

This module provides dependencies for:
- LLM clients (sync and async)
- Redis clients (sync and async)
- Database sessions
"""
from typing import Optional
from functools import lru_cache
from fastapi import Depends

# LLM Dependencies
from core.llm import LLMClient
from core.llm_async import AsyncLLMClient

# Redis Dependencies
from core.redis_pool import get_sync_client, get_async_client, is_sync_available
import redis
import redis.asyncio as aioredis

# Database Dependencies
from db.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession


# ============================================================
# LLM Client Dependencies
# ============================================================

@lru_cache()
def get_fast_llm_client() -> LLMClient:
    """
    Get fast LLM client (gpt-4o-mini) as a dependency.
    Uses LRU cache to ensure singleton pattern.
    """
    return LLMClient("gpt-4o-mini")


@lru_cache()
def get_smart_llm_client() -> LLMClient:
    """
    Get smart LLM client (gpt-4o) as a dependency.
    Uses LRU cache to ensure singleton pattern.
    """
    return LLMClient("gpt-4o")


@lru_cache()
def get_fast_llm_client_async() -> AsyncLLMClient:
    """
    Get fast async LLM client (gpt-4o-mini) as a dependency.
    Uses LRU cache to ensure singleton pattern.
    """
    return AsyncLLMClient("gpt-4o-mini")


@lru_cache()
def get_smart_llm_client_async() -> AsyncLLMClient:
    """
    Get smart async LLM client (gpt-4o) as a dependency.
    Uses LRU cache to ensure singleton pattern.
    """
    return AsyncLLMClient("gpt-4o")


# ============================================================
# Redis Client Dependencies
# ============================================================

def get_redis_sync() -> Optional[redis.Redis]:
    """
    Get sync Redis client as a dependency.
    Returns None if Redis is not available.
    """
    return get_sync_client()


async def get_redis_async() -> Optional[aioredis.Redis]:
    """
    Get async Redis client as a dependency.
    Returns None if Redis is not available.
    """
    return await get_async_client()


def require_redis_sync(redis_client: Optional[redis.Redis] = Depends(get_redis_sync)) -> redis.Redis:
    """
    Require sync Redis client (raises error if not available).
    Use this when Redis is required for the endpoint.
    """
    if not redis_client or not is_sync_available():
        raise RuntimeError("Redis sync client is not available")
    return redis_client


async def require_redis_async(
    redis_client: Optional[aioredis.Redis] = Depends(get_redis_async)
) -> aioredis.Redis:
    """
    Require async Redis client (raises error if not available).
    Use this when Redis is required for the endpoint.
    """
    if not redis_client:
        raise RuntimeError("Redis async client is not available")
    return redis_client


# ============================================================
# Database Session Dependency
# ============================================================

# Re-export get_db for convenience
GetDBSession = Depends(get_db)


# ============================================================
# Convenience Type Aliases
# ============================================================

# For type hints in route handlers
FastLLMClient = Depends(get_fast_llm_client)
SmartLLMClient = Depends(get_smart_llm_client)
FastLLMClientAsync = Depends(get_fast_llm_client_async)
SmartLLMClientAsync = Depends(get_smart_llm_client_async)
RedisSync = Depends(get_redis_sync)
RedisAsync = Depends(get_redis_async)
RequireRedisSync = Depends(require_redis_sync)
RequireRedisAsync = Depends(require_redis_async)
