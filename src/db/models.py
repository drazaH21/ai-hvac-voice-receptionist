import sqlite3
from src.db.connection import get_db_connection

class CallRepository:
    def __init__(self, db_path: str = None):
        self.db_path = db_path

    def get_or_create_call(self, call_sid: str, caller_phone: str = "") -> sqlite3.Row:
        conn = get_db_connection(self.db_path)
        with conn:
            conn.execute(
                "INSERT OR IGNORE INTO calls (call_sid, caller_phone) VALUES (?, ?)",
                (call_sid, caller_phone)
            )
            cursor = conn.execute("SELECT * FROM calls WHERE call_sid = ?", (call_sid,))
            return cursor.fetchone()

class WebhookEventRepository:
    def __init__(self, db_path: str = None):
        self.db_path = db_path

    def get_event(self, idempotency_key: str):
        conn = get_db_connection(self.db_path)
        cursor = conn.execute("SELECT response_twiml FROM webhook_events WHERE idempotency_key = ?", (idempotency_key,))
        row = cursor.fetchone()
        conn.close()
        return row["response_twiml"] if row else None

    def record_event(self, idempotency_key: str, call_sid: str, raw_payload: str, response_twiml: str):
        conn = get_db_connection(self.db_path)
        with conn:
            conn.execute("INSERT OR IGNORE INTO calls (call_sid) VALUES (?)", (call_sid,))
            conn.execute(
                "INSERT INTO webhook_events (idempotency_key, call_sid, raw_payload, response_twiml) VALUES (?, ?, ?, ?)",
                (idempotency_key, call_sid, raw_payload, response_twiml)
            )

class AppointmentRepository:
    def __init__(self, db_path: str = None):
        self.db_path = db_path

    def create_appointment(self, call_sid: str, customer_name: str, service_needed: str, slot_start: str) -> int:
        conn = get_db_connection(self.db_path)
        with conn:
            conn.execute("INSERT OR IGNORE INTO calls (call_sid) VALUES (?)", (call_sid,))
            cursor = conn.execute(
                "INSERT INTO appointments (call_sid, customer_name, service_needed, slot_start) VALUES (?, ?, ?, ?)",
                (call_sid, customer_name, service_needed, slot_start)
            )
            return cursor.lastrowid
