# core/redis_pool.py
"""
Centralized Redis connection pool management.

Provides connection pooling for both sync and async Redis clients
to improve performance and handle concurrent requests efficiently.
"""
import logging
import redis
import redis.asyncio as aioredis
from typing import Optional
from core.settings import (
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
    REDIS_MAX_CONNECTIONS,
    REDIS_CONNECTION_TIMEOUT,
    REDIS_SOCKET_TIMEOUT,
    REDIS_HEALTH_CHECK_INTERVAL,
)

logger = logging.getLogger(__name__)

# Sync connection pool
_sync_pool: Optional[redis.ConnectionPool] = None
_sync_client: Optional[redis.Redis] = None
_sync_available = False

# Async connection pool
_async_pool: Optional[aioredis.ConnectionPool] = None
_async_client: Optional[aioredis.Redis] = None
_async_available = False


def get_sync_pool() -> Optional[redis.ConnectionPool]:
    """Get or create sync Redis connection pool."""
    global _sync_pool, _sync_available
    
    if _sync_pool is not None:
        return _sync_pool
    
    try:
        _sync_pool = redis.ConnectionPool(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            max_connections=REDIS_MAX_CONNECTIONS,
            socket_connect_timeout=REDIS_CONNECTION_TIMEOUT,
            socket_timeout=REDIS_SOCKET_TIMEOUT,
            retry_on_timeout=True,
            health_check_interval=REDIS_HEALTH_CHECK_INTERVAL,
            decode_responses=True,
        )
        _sync_available = True
        logger.info(f"Sync Redis connection pool created (max_connections={REDIS_MAX_CONNECTIONS})")
        return _sync_pool
    except Exception as e:
        logger.error(f"Failed to create sync Redis connection pool: {e}")
        _sync_available = False
        return None


def get_sync_client() -> Optional[redis.Redis]:
    """Get sync Redis client from pool."""
    global _sync_client
    
    if _sync_client is not None:
        return _sync_client
    
    pool = get_sync_pool()
    if not pool:
        return None
    
    try:
        _sync_client = redis.Redis(connection_pool=pool)
        # Test connection
        _sync_client.ping()
        logger.info("Sync Redis client connected via pool")
        return _sync_client
    except Exception as e:
        logger.error(f"Failed to create sync Redis client: {e}")
        return None


async def get_async_pool() -> Optional[aioredis.ConnectionPool]:
    """Get or create async Redis connection pool."""
    global _async_pool, _async_available
    
    if _async_pool is not None:
        return _async_pool
    
    try:
        _async_pool = aioredis.ConnectionPool(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            max_connections=REDIS_MAX_CONNECTIONS,
            socket_connect_timeout=REDIS_CONNECTION_TIMEOUT,
            socket_timeout=REDIS_SOCKET_TIMEOUT,
            retry_on_timeout=True,
            health_check_interval=REDIS_HEALTH_CHECK_INTERVAL,
            decode_responses=True,
        )
        _async_available = True
        logger.info(f"Async Redis connection pool created (max_connections={REDIS_MAX_CONNECTIONS})")
        return _async_pool
    except Exception as e:
        logger.error(f"Failed to create async Redis connection pool: {e}")
        _async_available = False
        return None


async def get_async_client() -> Optional[aioredis.Redis]:
    """Get async Redis client from pool."""
    global _async_client
    
    if _async_client is not None:
        return _async_client
    
    pool = await get_async_pool()
    if not pool:
        return None
    
    try:
        _async_client = aioredis.Redis(connection_pool=pool)
        # Test connection
        await _async_client.ping()
        logger.info("Async Redis client connected via pool")
        return _async_client
    except Exception as e:
        logger.error(f"Failed to create async Redis client: {e}")
        return None


async def close_async_client():
    """Close async Redis client and pool."""
    global _async_client, _async_pool
    
    if _async_client:
        await _async_client.close()
        _async_client = None
    
    if _async_pool:
        await _async_pool.disconnect()
        _async_pool = None


def close_sync_client():
    """Close sync Redis client and pool."""
    global _sync_client, _sync_pool
    
    if _sync_client:
        _sync_client.close()
        _sync_client = None
    
    if _sync_pool:
        _sync_pool.disconnect()
        _sync_pool = None


def is_sync_available() -> bool:
    """Check if sync Redis is available."""
    return _sync_available and _sync_client is not None


async def is_async_available() -> bool:
    """Check if async Redis is available."""
    return _async_available and _async_client is not None


async def initialize_redis_pools():
    """Initialize both sync and async Redis connection pools."""
    # Initialize sync pool
    get_sync_client()
    
    # Initialize async pool
    await get_async_client()


async def close_redis_pools():
    """Close both sync and async Redis connection pools."""
    close_sync_client()
    await close_async_client()

