import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.config import get_settings
from tests.harness.simulator import compute_twilio_signature

@pytest.mark.asyncio
async def test_twilio_signature_dev_bypass(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    get_settings.cache_clear()
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/voice/validate-test",
            data={"CallSid": "CA12345"}
        )
    assert response.status_code == 200
    assert response.json() == {"status": "valid"}

@pytest.mark.asyncio
async def test_twilio_signature_enforced_in_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "mock_auth_token_12345")
    get_settings.cache_clear()

    url = "http://test/api/v1/voice/validate-test"
    params = {"CallSid": "CA12345"}
    valid_sig = compute_twilio_signature(url, params, "mock_auth_token_12345")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Request with valid signature
        res_ok = await client.post(
            "/api/v1/voice/validate-test",
            data=params,
            headers={"X-Twilio-Signature": valid_sig}
        )
        assert res_ok.status_code == 200

        # Request with invalid signature
        res_bad = await client.post(
            "/api/v1/voice/validate-test",
            data=params,
            headers={"X-Twilio-Signature": "invalid_sig"}
        )
        assert res_bad.status_code == 403
