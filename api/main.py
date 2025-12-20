from fastapi import FastAPI
from api.routes import router

app = FastAPI(
    title="AI Resume Tailoring Agent",
    version="1.0.0",
    description="End-to-end AI agent for resume tailoring"
)

app.include_router(router, prefix="/api")

@app.get("/")
def root():
    return {"status": "running"}
