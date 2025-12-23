# api/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from api.routes import router
from api.chat import router as chat_router
from core.logging import setup_logging, request_id_ctx
from core.rate_limit import check_rate_limit
import uuid
import os

setup_logging()

app = FastAPI(title="AI Resume Tailor")

# Configure CORS - allow all origins in production (adjust as needed)
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173")
if cors_origins == "*":
    allow_origins = ["*"]
else:
    allow_origins = [origin.strip() for origin in cors_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Static files and SPA serving will be configured after router


@app.on_event("startup")
async def startup_event():
    """Initialize Redis connection pools and PostgreSQL database on startup."""
    from core.redis_pool import initialize_redis_pools
    from db.database import init_db
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Initialize Redis connection pools
    await initialize_redis_pools()
    
    # Initialize PostgreSQL database
    try:
        await init_db()
        logger.info("PostgreSQL database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize PostgreSQL database: {e}", exc_info=True)
        # Don't fail startup if DB is unavailable (for backward compatibility)
        logger.warning("Continuing without PostgreSQL - some features may be unavailable")


@app.on_event("shutdown")
async def shutdown_event():
    """Close Redis connection pools and PostgreSQL database on shutdown."""
    from core.redis_pool import close_redis_pools
    from db.database import close_db
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Close Redis connection pools
    await close_redis_pools()
    
    # Close PostgreSQL database
    try:
        await close_db()
        logger.info("PostgreSQL database closed")
    except Exception as e:
        logger.error(f"Error closing PostgreSQL database: {e}", exc_info=True)
    from core.redis_pool import close_sync_client, close_async_client
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Close sync pool
    close_sync_client()
    logger.info("Sync Redis connection pool closed")
    
    # Close async pool
    await close_async_client()
    logger.info("Async Redis connection pool closed")


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    token = request_id_ctx.set(request_id)

    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        request_id_ctx.reset(token)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """
    Rate limiting middleware.
    Skips rate limiting for health checks and static endpoints.
    """
    # Skip rate limiting for health checks and docs
    if request.url.path in ["/health", "/docs", "/openapi.json", "/redoc"]:
        return await call_next(request)
    
    # Check rate limit
    rate_limit_response = check_rate_limit(request)
    if rate_limit_response:
        return rate_limit_response
    
    response = await call_next(request)
    return response


@app.middleware("http")
async def api_usage_tracking_middleware(request: Request, call_next):
    """
    Track API usage for analytics.
    Records endpoint, method, response time, status code, etc.
    """
    import time
    from db.database import SessionLocal
    from db.repositories import create_api_usage
    from core.rate_limit import get_client_ip
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Skip tracking for health checks, docs, and analytics endpoints
    skip_paths = ["/health", "/docs", "/openapi.json", "/redoc", "/analytics"]
    if request.url.path.startswith("/analytics"):
        return await call_next(request)
    
    if request.url.path in skip_paths:
        return await call_next(request)
    
    # Track request start time
    start_time = time.time()
    
    # Get request metadata
    endpoint = request.url.path
    method = request.method
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "")
    
    # Try to get user_id from request (if available)
    user_id = None
    # You can extend this to extract user_id from auth token, session, etc.
    # For now, we'll track without user_id
    
    # Get request size (if available)
    request_size = None
    if hasattr(request, "_body"):
        try:
            request_size = len(request._body) if request._body else None
        except:
            pass
    
    # Process request
    response = None
    status_code = 500
    error_message = None
    
    try:
        response = await call_next(request)
        status_code = response.status_code
        
        # Get response size (if available)
        response_size = None
        if hasattr(response, "body"):
            try:
                response_size = len(response.body) if response.body else None
            except:
                pass
        
        return response
    except Exception as e:
        status_code = 500
        error_message = str(e)
        logger.error(f"Request failed: {e}", exc_info=True)
        raise
    finally:
        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Record API usage asynchronously (don't block response)
        try:
            async with SessionLocal() as session:
                await create_api_usage(
                    session=session,
                    endpoint=endpoint,
                    method=method,
                    status_code=status_code,
                    user_id=user_id,
                    client_ip=client_ip,
                    response_time_ms=response_time_ms,
                    request_size_bytes=request_size,
                    response_size_bytes=None,  # Would need to capture from response
                    user_agent=user_agent[:500],  # Limit length
                    error_message=error_message[:1000] if error_message else None,  # Limit length
                )
                await session.commit()
        except Exception as e:
            # Don't fail request if tracking fails
            # Only log if it's not a missing table error (migrations may not have run yet)
            error_str = str(e)
            if "does not exist" not in error_str and "UndefinedTableError" not in error_str:
                logger.warning(f"Failed to track API usage: {e}", exc_info=True)
            # Silently ignore missing table errors (migrations will fix this)


# Include API routes
app.include_router(router)
app.include_router(chat_router)

# Serve static files and SPA (must be after router to not interfere with API routes)
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    # Mount static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets")), name="assets")
    
    # Serve index.html for all non-API routes (SPA routing)
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str, request: Request):
        """
        Serve React app for all non-API routes.
        This enables client-side routing in the React app.
        """
        # Don't serve SPA for API routes, docs, health, or static files
        # Check for exact matches or paths starting with these prefixes
        excluded = ["health", "docs", "openapi.json", "redoc", "api", "static", "assets"]
        if full_path in excluded or any(full_path.startswith(f"{prefix}/") for prefix in excluded):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Not found")
        
        index_path = os.path.join(static_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Frontend not found")
