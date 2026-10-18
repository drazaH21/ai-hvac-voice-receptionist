import pytest
from unittest.mock import AsyncMock
from src.db.connection import init_db
from src.db.models import AppointmentRepository
from src.schemas.extraction import ExtractedCallIntent
from src.services.conversation import ConversationStateMachine

@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    test_db = str(tmp_path / "test_conversation.db")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{test_db}")
    init_db(test_db)
    yield test_db

@pytest.mark.asyncio
async def test_conversation_extracts_and_prompts_for_confirmation(setup_test_db):
    mock_extractor = AsyncMock()
    mock_extractor.extract_intent.return_value = ExtractedCallIntent(
        intent="request_appointment",
        customer_name="Alice Smith",
        service_needed="pipe repair",
        requested_time_text="tomorrow at 10 AM",
        confidence_score=0.95
    )

    machine = ConversationStateMachine(db_path=setup_test_db, extractor=mock_extractor)
    
    twiml, next_state = await machine.process_turn(
        call_sid="CA_CONV_1",
        turn_id=1,
        user_utterance="Hi, I am Alice Smith and need pipe repair tomorrow at 10 AM",
        current_state="GREETING"
    )

    assert "<Gather" in twiml
    assert "confirm" in twiml.lower() or "Alice Smith" in twiml
    assert next_state == "CONFIRMING"

@pytest.mark.asyncio
async def test_conversation_commits_appointment_upon_confirmation(setup_test_db):
    mock_extractor = AsyncMock()
    mock_extractor.extract_intent.return_value = ExtractedCallIntent(
        intent="confirm",
        confidence_score=0.95
    )

    machine = ConversationStateMachine(db_path=setup_test_db, extractor=mock_extractor)
    
    # Store partial session context
    machine.session_store["CA_CONV_2"] = {
        "customer_name": "Bob Stone",
        "service_needed": "HVAC tuneup",
        "slot_start": "2026-10-20T14:00:00Z"
    }

    twiml, next_state = await machine.process_turn(
        call_sid="CA_CONV_2",
        turn_id=2,
        user_utterance="Yes, that sounds perfect. Confirm it.",
        current_state="CONFIRMING"
    )

    assert "booked" in twiml.lower() or "confirmed" in twiml.lower()
    assert next_state == "BOOKED"

    repo = AppointmentRepository(setup_test_db)
    from src.db.connection import get_db_connection
    c = get_db_connection(setup_test_db)
    row = c.execute("SELECT * FROM appointments WHERE call_sid = 'CA_CONV_2'").fetchone()
    assert row is not None
    assert row["customer_name"] == "Bob Stone"
    assert row["service_needed"] == "HVAC tuneup"
