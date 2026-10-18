import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
from src.main import app
from src.config import get_settings
from src.db.connection import init_db, get_db_connection
from src.schemas.extraction import ExtractedCallIntent

@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    test_db = str(tmp_path / "test_e2e.db")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{test_db}")
    monkeypatch.setenv("ENVIRONMENT", "development")
    get_settings.cache_clear()
    init_db(test_db)
    yield test_db
    get_settings.cache_clear()

@pytest.mark.asyncio
async def test_latency_middleware_adds_header_and_logs():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/health/live")
    assert res.status_code == 200
    assert "x-response-time-ms" in res.headers

@pytest.mark.asyncio
async def test_full_call_lifecycle_creates_single_appointment(setup_test_db):
    call_sid = "CA_E2E_SIMULATED_999"
    caller_num = "+15553219876"

    # Mock sequential LLM extraction turns
    turn1_intent = ExtractedCallIntent(
        intent="request_appointment",
        customer_name="David Miller",
        service_needed="AC Repair",
        requested_time_text="Monday at 11 AM",
        confidence_score=0.98
    )
    turn2_intent = ExtractedCallIntent(
        intent="confirm",
        confidence_score=0.99
    )

    with patch("src.services.conversation.LLMExtractor.extract_intent", side_effect=[turn1_intent, turn2_intent]):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. Incoming call
            res_incoming = await client.post(
                "/api/v1/voice/incoming",
                data={"CallSid": call_sid, "From": caller_num}
            )
            assert res_incoming.status_code == 200
            assert "<Gather" in res_incoming.text

            # 2. Turn 1: User states intent and details
            res_turn1 = await client.post(
                "/api/v1/voice/turn?turn_id=1",
                data={"CallSid": call_sid, "SpeechResult": "Hi, I am David Miller and my AC is broken. Can someone come Monday at 11 AM?"}
            )
            assert res_turn1.status_code == 200
            assert "David Miller" in res_turn1.text or "CONFIRMING" in res_turn1.text

            # 3. Network glitch replay test (Turn 1 redelivery must yield identical TwiML)
            res_turn1_retry = await client.post(
                "/api/v1/voice/turn?turn_id=1",
                data={"CallSid": call_sid, "SpeechResult": "Hi, I am David Miller and my AC is broken. Can someone come Monday at 11 AM?"}
            )
            assert res_turn1_retry.status_code == 200
            assert res_turn1_retry.text == res_turn1.text

            # 4. Turn 2: User confirms booking
            res_turn2 = await client.post(
                "/api/v1/voice/turn?turn_id=2&state=CONFIRMING",
                data={"CallSid": call_sid, "SpeechResult": "Yes, please confirm that time."}
            )
            assert res_turn2.status_code == 200
            assert "<Hangup/>" in res_turn2.text or "confirmed" in res_turn2.text.lower()

    # 5. Database State Assertions
    conn = get_db_connection(setup_test_db)
    call_record = conn.execute("SELECT * FROM calls WHERE call_sid = ?", (call_sid,)).fetchone()
    assert call_record is not None

    events = conn.execute("SELECT COUNT(*) as count FROM webhook_events WHERE call_sid = ?", (call_sid,)).fetchone()
    # 3 unique keys recorded: incoming:0, turn:1, turn:2 (the turn:1 retry was deduplicated)
    assert events["count"] == 3

    appointments = conn.execute("SELECT * FROM appointments WHERE call_sid = ?", (call_sid,)).fetchall()
    assert len(appointments) == 1
    assert appointments[0]["customer_name"] == "David Miller"
    assert appointments[0]["service_needed"] == "AC Repair"
    conn.close()
