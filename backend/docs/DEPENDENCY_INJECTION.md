# Dependency Injection Guide

This application uses FastAPI's dependency injection system to manage shared resources (LLM clients, Redis clients, database sessions) instead of global state.

## Benefits

1. **Better Testability**: Easy to mock dependencies in tests
2. **Cleaner Code**: No global state, explicit dependencies
3. **Flexibility**: Can swap implementations easily
4. **Type Safety**: Better IDE support and type checking

## Available Dependencies

### LLM Clients

```python
from api.dependencies import (
    get_fast_llm_client,
    get_smart_llm_client,
    get_fast_llm_client_async,
    get_smart_llm_client_async,
)

# In route handler
@router.post("/example")
async def example(
    fast_llm: LLMClient = Depends(get_fast_llm_client),
    smart_llm: LLMClient = Depends(get_smart_llm_client),
):
    result = fast_llm.invoke("Your prompt")
    return {"result": result}
```

### Redis Clients

```python
from api.dependencies import (
    get_redis_sync,
    get_redis_async,
    require_redis_sync,
    require_redis_async,
)

# Optional Redis (returns None if unavailable)
@router.get("/example")
async def example(redis: Optional[redis.Redis] = Depends(get_redis_sync)):
    if redis:
        value = redis.get("key")
    return {"value": value}

# Required Redis (raises error if unavailable)
@router.get("/example")
async def example(redis: redis.Redis = Depends(require_redis_sync)):
    value = redis.get("key")
    return {"value": value}
```

### Database Sessions

```python
from db.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

@router.get("/example")
async def example(db: AsyncSession = Depends(get_db)):
    # Use db session
    result = await db.execute(select(User))
    return {"users": result.scalars().all()}
```

## Migration Guide

### Before (Global State)

```python
from core.llm import fast_llm_call
from core.cache import get_cached_jd

@router.post("/analyze")
def analyze_jd(jd: str):
    # Uses global LLM client
    result = fast_llm_call(f"Analyze: {jd}")
    
    # Uses global Redis client
    cached = get_cached_jd(jd)
    return {"result": result}
```

### After (Dependency Injection)

```python
from api.dependencies import get_fast_llm_client, get_redis_sync
from core.llm import LLMClient
from core.cache import get_cached_jd
import redis

@router.post("/analyze")
async def analyze_jd(
    jd: str,
    llm_client: LLMClient = Depends(get_fast_llm_client),
    redis_client: Optional[redis.Redis] = Depends(get_redis_sync),
):
    # Use injected LLM client
    result = llm_client.invoke(f"Analyze: {jd}")
    
    # Use injected Redis client
    cached = get_cached_jd(jd, redis_client_instance=redis_client)
    return {"result": result}
```

## Backward Compatibility

All global functions still work for backward compatibility:

```python
# Still works (uses global state)
from core.llm import fast_llm_call
result = fast_llm_call("prompt")

# But prefer dependency injection
from api.dependencies import get_fast_llm_client
@router.post("/example")
def example(llm: LLMClient = Depends(get_fast_llm_client)):
    return llm.invoke("prompt")
```

## Testing with Dependencies

### Mocking Dependencies

```python
from unittest.mock import Mock, AsyncMock
from fastapi.testclient import TestClient

def test_example():
    # Create mock LLM client
    mock_llm = Mock()
    mock_llm.invoke.return_value = "Mocked response"
    
    # Override dependency
    app.dependency_overrides[get_fast_llm_client] = lambda: mock_llm
    
    client = TestClient(app)
    response = client.post("/example", json={"prompt": "test"})
    
    assert response.status_code == 200
    assert response.json()["result"] == "Mocked response"
    
    # Clean up
    app.dependency_overrides.clear()
```

### Testing with Real Dependencies

```python
def test_with_real_dependencies():
    # Use real dependencies (requires Redis/LLM to be available)
    client = TestClient(app)
    response = client.post("/example", json={"prompt": "test"})
    
    assert response.status_code == 200
```

## Best Practices

1. **Always use dependency injection in new code**
2. **Prefer async dependencies for async routes**
3. **Use `require_*` dependencies when the resource is mandatory**
4. **Use optional dependencies when the resource might be unavailable**
5. **Mock dependencies in tests for faster, isolated tests**

## Common Patterns

### Pattern 1: Simple Dependency

```python
@router.get("/items")
async def get_items(db: AsyncSession = Depends(get_db)):
    items = await db.execute(select(Item))
    return items.scalars().all()
```

### Pattern 2: Multiple Dependencies

```python
@router.post("/process")
async def process(
    data: str,
    llm: LLMClient = Depends(get_smart_llm_client),
    redis: redis.Redis = Depends(require_redis_sync),
    db: AsyncSession = Depends(get_db),
):
    # Use all dependencies
    result = llm.invoke(data)
    redis.set("key", result)
    # Save to database
    return {"result": result}
```

### Pattern 3: Conditional Logic

```python
@router.get("/cache")
async def get_cache(
    key: str,
    redis: Optional[redis.Redis] = Depends(get_redis_sync),
):
    if redis:
        value = redis.get(key)
        return {"cached": value}
    else:
        return {"cached": None, "note": "Redis unavailable"}
```

## Migration Checklist

When migrating existing code:

- [ ] Replace global LLM calls with dependency injection
- [ ] Replace global Redis client access with dependency injection
- [ ] Update function signatures to accept optional client parameters
- [ ] Update tests to mock dependencies
- [ ] Document dependency requirements in route docstrings

