import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.config import get_settings

@pytest.mark.asyncio
async def test_health_live_returns_200_ok():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}

@pytest.mark.asyncio
async def test_health_ready_returns_200_ok():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "version" in data
    assert data["database"] == "ready"

def test_config_reads_defaults():
    settings = get_settings()
    assert settings.app_name == "voice-receptionist-poc"
    assert settings.api_v1_prefix == "/api/v1"
    assert settings.groq_timeout_seconds == 2.5
