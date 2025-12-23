# api/routes_example_di.py
"""
Example routes demonstrating dependency injection usage.

This file shows how to use dependency injection in route handlers.
These patterns should be used when creating new routes or refactoring existing ones.
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
import redis
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import (
    get_fast_llm_client,
    get_smart_llm_client,
    get_redis_sync,
    require_redis_sync,
)
from core.llm import LLMClient
from core.cache import get_cached_jd, set_cached_jd
from db.database import get_db

router = APIRouter()


# Example 1: Using LLM client with dependency injection
@router.post("/example/llm")
async def example_llm(
    prompt: str,
    llm_client: LLMClient = Depends(get_fast_llm_client),
):
    """
    Example route using LLM client via dependency injection.
    
    Benefits:
    - Easy to test (can mock llm_client)
    - No global state
    - Explicit dependencies
    """
    result = llm_client.invoke(prompt)
    return {"result": result}


# Example 2: Using Redis with optional dependency
@router.get("/example/cache")
async def example_cache(
    key: str,
    redis_client: Optional[redis.Redis] = Depends(get_redis_sync),
):
    """
    Example route using optional Redis client.
    
    If Redis is unavailable, returns None instead of raising error.
    """
    if redis_client:
        value = redis_client.get(key)
        return {"cached": value, "redis_available": True}
    else:
        return {"cached": None, "redis_available": False}


# Example 3: Using Redis with required dependency
@router.post("/example/cache/set")
async def example_cache_set(
    key: str,
    value: str,
    redis_client: redis.Redis = Depends(require_redis_sync),
):
    """
    Example route requiring Redis client.
    
    Raises error if Redis is not available.
    """
    redis_client.set(key, value)
    return {"status": "cached"}


# Example 4: Using cache functions with dependency injection
@router.post("/example/jd-cache")
async def example_jd_cache(
    jd_text: str,
    redis_client: Optional[redis.Redis] = Depends(get_redis_sync),
):
    """
    Example using cache functions with injected Redis client.
    """
    # Check cache first
    cached = get_cached_jd(jd_text, redis_client_instance=redis_client)
    if cached:
        return {"cached": True, "result": cached}
    
    # Process and cache
    # ... processing logic ...
    result = {"role": "Software Engineer", "skills": ["Python", "FastAPI"]}
    
    set_cached_jd(jd_text, result, redis_client_instance=redis_client)
    return {"cached": False, "result": result}


# Example 5: Using database session
@router.get("/example/db")
async def example_db(
    db: AsyncSession = Depends(get_db),
):
    """
    Example using database session via dependency injection.
    """
    from db.models import User
    from sqlalchemy import select
    
    result = await db.execute(select(User).limit(10))
    users = result.scalars().all()
    return {"users": [{"id": str(u.id), "email": u.email} for u in users]}


# Example 6: Multiple dependencies
@router.post("/example/multiple")
async def example_multiple(
    prompt: str,
    fast_llm: LLMClient = Depends(get_fast_llm_client),
    smart_llm: LLMClient = Depends(get_smart_llm_client),
    redis_client: Optional[redis.Redis] = Depends(get_redis_sync),
    db: AsyncSession = Depends(get_db),
):
    """
    Example using multiple dependencies.
    
    Shows how to use LLM clients, Redis, and database in one route.
    """
    # Use fast LLM for quick response
    quick_result = fast_llm.invoke(f"Quick: {prompt}")
    
    # Use smart LLM for detailed analysis
    detailed_result = smart_llm.invoke(f"Detailed: {prompt}")
    
    # Cache results if Redis available
    if redis_client:
        redis_client.set(f"quick:{prompt}", quick_result)
        redis_client.set(f"detailed:{prompt}", detailed_result)
    
    # Save to database
    # ... database operations ...
    
    return {
        "quick": quick_result,
        "detailed": detailed_result,
        "cached": redis_client is not None,
    }

