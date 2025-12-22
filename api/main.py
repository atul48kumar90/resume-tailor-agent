# api/main.py
from fastapi import FastAPI, Request
from api.routes import router
from core.logging import setup_logging, request_id_ctx
from core.rate_limit import check_rate_limit
import uuid

setup_logging()

app = FastAPI(title="AI Resume Tailor")


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


app.include_router(router)
