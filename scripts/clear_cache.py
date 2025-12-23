#!/usr/bin/env python3
"""
Python script to clear Redis cache for resume tailor agent.

Usage:
    python scripts/clear_cache.py              # Clear all cache
    python scripts/clear_cache.py rewrite      # Clear only rewrite cache
    python scripts/clear_cache.py jd           # Clear only JD analysis cache
    python scripts/clear_cache.py ats          # Clear only ATS score cache
    python scripts/clear_cache.py all          # Clear all cache
"""

import sys
import redis
from typing import List, Tuple

# Cache key patterns
CACHE_PATTERNS = {
    "rewrite": "rewrite:*",
    "jd": "jd:*",
    "ats": "ats:*",
    "normalized": "normalized:*",
    "extracted": "extracted:*",
    "tokens": "tokens:*",
}


def get_redis_client() -> redis.Redis:
    """Get Redis client."""
    try:
        from core.settings import REDIS_HOST, REDIS_PORT, REDIS_DB
        client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            decode_responses=False,  # Binary mode for compatibility
            socket_connect_timeout=5,
        )
        client.ping()
        return client
    except Exception as e:
        print(f"❌ Error connecting to Redis: {e}")
        print("\nPlease ensure Redis is running:")
        print("  - macOS: brew services start redis")
        print("  - Docker: docker run -d -p 6379:6379 redis:7")
        sys.exit(1)


def clear_cache_pattern(client: redis.Redis, pattern: str) -> int:
    """Clear all keys matching a pattern. Returns count of deleted keys."""
    count = 0
    cursor = 0
    while True:
        cursor, keys = client.scan(cursor, match=pattern, count=1000)
        if keys:
            deleted = client.delete(*keys)
            count += deleted
        if cursor == 0:
            break
    return count


def clear_cache(cache_type: str = "all") -> None:
    """Clear Redis cache based on type."""
    client = get_redis_client()
    
    print("🔄 Clearing Redis cache...\n")
    
    if cache_type == "all":
        # Clear all cache types
        total = 0
        for name, pattern in CACHE_PATTERNS.items():
            count = clear_cache_pattern(client, pattern)
            if count > 0:
                print(f"  ✓ {name.capitalize()} cache: {count} entries")
            total += count
        
        if total == 0:
            print("  ℹ️  No cache entries found")
        else:
            print(f"\n✅ Total: {total} entries cleared")
    elif cache_type in CACHE_PATTERNS:
        # Clear specific cache type
        pattern = CACHE_PATTERNS[cache_type]
        count = clear_cache_pattern(client, pattern)
        if count > 0:
            print(f"✅ Cleared {count} {cache_type} cache entries")
        else:
            print(f"ℹ️  No {cache_type} cache entries found")
    else:
        print(f"❌ Unknown cache type: {cache_type}")
        print(f"Available types: {', '.join(CACHE_PATTERNS.keys())}, all")
        sys.exit(1)
    
    print("\n✅ Cache cleared successfully!")


if __name__ == "__main__":
    # Add backend to path
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
    
    cache_type = sys.argv[1] if len(sys.argv) > 1 else "all"
    clear_cache(cache_type)

