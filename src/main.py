from fastapi import FastAPI
from src.config import get_settings
from src.logging import logger

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)

@app.get("/health/live", tags=["Health"])
async def health_live():
    return {"status": "alive"}

@app.get("/health/ready", tags=["Health"])
async def health_ready():
    return {
        "status": "ready",
        "version": settings.app_version,
        "database": "uninitialized",
    }
