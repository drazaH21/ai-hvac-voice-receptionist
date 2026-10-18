import pytest
import sqlite3
from src.config import get_settings
from src.db.connection import get_db_connection, init_db
from src.db.models import CallRepository, WebhookEventRepository, AppointmentRepository

@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    test_db = str(tmp_path / "test_receptionist.db")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{test_db}")
    get_settings.cache_clear()
    init_db(test_db)
    yield test_db
    get_settings.cache_clear()

def test_db_initializes_with_wal_mode_and_foreign_keys(setup_test_db):
    conn = get_db_connection(setup_test_db)
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA journal_mode;")
    mode = cursor.fetchone()[0]
    assert mode.lower() == "wal"

    cursor.execute("PRAGMA foreign_keys;")
    fk = cursor.fetchone()[0]
    assert fk == 1
    conn.close()

def test_idempotency_key_enforces_unique_constraint(setup_test_db):
    repo = WebhookEventRepository(setup_test_db)
    key = "CA123:turn:1"
    
    repo.record_event(idempotency_key=key, call_sid="CA123", raw_payload="{}", response_twiml="<Response/>")
    
    with pytest.raises(sqlite3.IntegrityError):
        repo.record_event(idempotency_key=key, call_sid="CA123", raw_payload="{}", response_twiml="<Response/>")

def test_appointment_insert_and_conflict_detection(setup_test_db):
    repo = AppointmentRepository(setup_test_db)
    
    app_id = repo.create_appointment(
        call_sid="CA123",
        customer_name="Alice Smith",
        service_needed="plumbing",
        slot_start="2026-10-19T10:00:00Z"
    )
    assert app_id is not None

    with pytest.raises(sqlite3.IntegrityError):
        repo.create_appointment(
            call_sid="CA456",
            customer_name="Bob Jones",
            service_needed="plumbing",
            slot_start="2026-10-19T10:00:00Z"
        )
