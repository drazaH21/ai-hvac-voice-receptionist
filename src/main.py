from fastapi import FastAPI, Depends
from src.config import get_settings
from src.logging import logger
from src.security.signature import validate_twilio_request
from src.api.routes_voice import router as voice_router

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)

app.include_router(voice_router)

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

@app.post("/api/v1/voice/validate-test", dependencies=[Depends(validate_twilio_request)], tags=["Voice"])
async def validate_test():
    return {"status": "valid"}
