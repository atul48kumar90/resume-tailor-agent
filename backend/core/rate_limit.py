# core/rate_limit.py
"""
Simple rate limiting using Redis.
"""
import time
import logging
from typing import Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

from core.settings import RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW

# Per-endpoint limits (more restrictive for expensive operations)
ENDPOINT_LIMITS = {
    "/ats/compare": {"requests": 20, "window": 3600},  # 20 per hour
    "/tailor": {"requests": 10, "window": 3600},  # 10 per hour
    "/tailor/files": {"requests": 10, "window": 3600},  # 10 per hour
}


def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    if request.client:
        return request.client.host
    return "unknown"


def check_rate_limit(request: Request) -> Optional[JSONResponse]:
    """
    Check if request exceeds rate limit.
    
    Returns:
        JSONResponse with 429 status if rate limited, None otherwise
    """
    try:
        from api.jobs import redis_client
        
        if not redis_client:
            # If Redis is unavailable, allow requests (fail open)
            logger.warning("Redis unavailable, skipping rate limit check")
            return None
        
        client_ip = get_client_ip(request)
        path = request.url.path
        
        # Get endpoint-specific limits or use defaults
        limits = ENDPOINT_LIMITS.get(path, {
            "requests": RATE_LIMIT_REQUESTS,
            "window": RATE_LIMIT_WINDOW
        })
        
        max_requests = limits["requests"]
        window = limits["window"]
        
        # Create rate limit key
        key = f"rate_limit:{client_ip}:{path}"
        current_time = int(time.time())
        window_start = current_time - window
        
        # Get current count
        try:
            # Use sorted set to track requests in time window
            redis_client.zremrangebyscore(key, 0, window_start)
            count = redis_client.zcard(key)
            
            if count >= max_requests:
                # Get oldest request time to calculate retry-after
                oldest = redis_client.zrange(key, 0, 0, withscores=True)
                if oldest:
                    retry_after = int(oldest[0][1] + window - current_time)
                else:
                    retry_after = window
                
                logger.warning(
                    f"Rate limit exceeded for {client_ip} on {path}: "
                    f"{count}/{max_requests} requests in {window}s"
                )
                
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "Rate limit exceeded",
                        "message": f"Too many requests. Limit: {max_requests} requests per {window} seconds.",
                        "retry_after": retry_after,
                        "limit": max_requests,
                        "window": window
                    },
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": str(max_requests),
                        "X-RateLimit-Remaining": str(max(0, max_requests - count - 1)),
                        "X-RateLimit-Reset": str(current_time + window)
                    }
                )
            
            # Add current request
            redis_client.zadd(key, {str(current_time): current_time})
            redis_client.expire(key, window)
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}", exc_info=True)
            # Fail open - allow request if rate limiting fails
            return None
        
        return None
        
    except Exception as e:
        logger.error(f"Rate limiting error: {e}", exc_info=True)
        # Fail open - allow request if rate limiting fails
        return None

