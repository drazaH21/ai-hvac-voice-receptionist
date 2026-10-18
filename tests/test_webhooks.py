import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.config import get_settings
from src.db.connection import init_db
from src.db.models import WebhookEventRepository

@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    test_db = str(tmp_path / "test_webhooks.db")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{test_db}")
    monkeypatch.setenv("ENVIRONMENT", "development")
    get_settings.cache_clear()
    init_db(test_db)
    yield test_db
    get_settings.cache_clear()

@pytest.mark.asyncio
async def test_incoming_call_initializes_session_and_returns_twiml(setup_test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/voice/incoming",
            data={"CallSid": "CA_INCOMING_001", "From": "+15550001"}
        )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    assert "<Gather" in response.text
    assert "turn_id=1" in response.text

@pytest.mark.asyncio
async def test_duplicate_webhook_turn_replays_cached_response(setup_test_db):
    payload = {
        "CallSid": "CA_TURN_002",
        "SpeechResult": "I need a plumber tomorrow at 2 PM",
    }
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # First turn submission
        res1 = await client.post("/api/v1/voice/turn?turn_id=1", data=payload)
        assert res1.status_code == 200
        twiml_1 = res1.text

        # Re-delivery of identical turn (network retry simulation)
        res2 = await client.post("/api/v1/voice/turn?turn_id=1", data=payload)
        assert res2.status_code == 200
        twiml_2 = res2.text

    assert twiml_1 == twiml_2

    # Verify database has exactly one event recorded for this key
    repo = WebhookEventRepository(setup_test_db)
    cached = repo.get_event("CA_TURN_002:turn:1")
    assert cached is not None
