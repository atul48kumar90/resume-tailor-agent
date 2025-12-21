# api/main.py
from fastapi import FastAPI, Request
from api.routes import router
from core.logging import setup_logging, request_id_ctx
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


app.include_router(router)
