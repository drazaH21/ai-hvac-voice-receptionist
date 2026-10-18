CREATE TABLE IF NOT EXISTS calls (
    call_sid TEXT PRIMARY KEY,
    caller_phone TEXT,
    status TEXT NOT NULL DEFAULT "in_progress",
    current_turn INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS webhook_events (
    idempotency_key TEXT PRIMARY KEY,
    call_sid TEXT NOT NULL,
    raw_payload TEXT,
    response_twiml TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (call_sid) REFERENCES calls(call_sid) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    call_sid TEXT NOT NULL,
    customer_name TEXT NOT NULL,
    service_needed TEXT NOT NULL,
    slot_start TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT "confirmed",
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (call_sid) REFERENCES calls(call_sid) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_calls_sid ON calls(call_sid);
CREATE INDEX IF NOT EXISTS idx_webhook_key ON webhook_events(idempotency_key);
CREATE INDEX IF NOT EXISTS idx_appointments_slot ON appointments(slot_start);
