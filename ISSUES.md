# Engineering Issues & TDD Implementation Roadmap

## Issue 01: Scaffolding, Configuration, Logging & Health Probes
- **Prerequisites**: None
- **Target Files**:
  - `src/config.py`
  - `src/logging.py`
  - `src/main.py`
  - `tests/test_health.py`
- **Acceptance Criteria**:
  - Environment settings loaded via `pydantic-settings` with default port `8000`.
  - Structured JSON logger writing timestamp, level, path, and method.
  - `GET /health/live` returns HTTP 200 `{"status": "alive"}` without external dependencies.
  - `GET /health/ready` returns HTTP 200 `{"status": "ready"}` with basic configuration validation.
- **TDD Test Scenarios**:
  - `test_health_live_returns_200_ok`
  - `test_health_ready_returns_200_ok`
  - `test_config_reads_env_overrides`

## Issue 02: SQLite Storage Engine (WAL Mode & Transactions)
- **Prerequisites**: Issue 01
- **Target Files**:
  - `src/db/connection.py`
  - `src/db/models.py`
  - `src/db/schema.sql`
  - `tests/test_database.py`
- **Acceptance Criteria**:
  - SQLite initialized with `PRAGMA journal_mode=WAL;` and `PRAGMA foreign_keys=ON;`.
  - Busy timeout configured to 5000ms.
  - Tables created: `calls`, `webhook_events`, `appointments`.
  - Indexes created on `calls(call_sid)`, `webhook_events(idempotency_key)`, `appointments(slot_start)`.
- **TDD Test Scenarios**:
  - `test_db_initializes_with_wal_mode`
  - `test_idempotency_key_enforces_unique_constraint`
  - `test_appointment_insert_and_conflict_detection`

## Issue 03: Twilio Signature Validation Middleware & Simulation Harness
- **Prerequisites**: Issue 01
- **Target Files**:
  - `src/security/signature.py`
  - `tests/harness/simulator.py`
  - `tests/test_security.py`
- **Acceptance Criteria**:
  - Request validation verifies `X-Twilio-Signature` using auth token and request URL + form params.
  - Local bypass switch (`ENVIRONMENT=development`) to allow offline testing.
  - Simulator utility that signs mock webhook requests locally.
- **TDD Test Scenarios**:
  - `test_signature_valid_returns_200`
  - `test_signature_invalid_returns_403`
  - `test_signature_dev_bypass_flag`

## Issue 04: Idempotent Webhook Handler (`/api/v1/voice/incoming` & `/turn`)
- **Prerequisites**: Issue 02, Issue 03
- **Target Files**:
  - `src/api/routes_voice.py`
  - `src/services/webhook_service.py`
  - `tests/test_webhooks.py`
- **Acceptance Criteria**:
  - Generates composite idempotency key: `CallSid + ":" + action + ":" + turn_id`.
  - Replays existing cached TwiML on duplicate key submission without re-executing logic.
  - Atomic persistence of incoming event and generated response.
- **TDD Test Scenarios**:
  - `test_incoming_call_initializes_session_and_returns_twiml`
  - `test_duplicate_turn_replays_cached_response_without_duplicate_row`

## Issue 05: Groq Structured LLM Extraction Service
- **Prerequisites**: Issue 01
- **Target Files**:
  - `src/services/llm_extractor.py`
  - `src/schemas/extraction.py`
  - `tests/test_llm_extractor.py`
- **Acceptance Criteria**:
  - Extracts caller intent, customer name, requested service, and appointment time text.
  - Enforces strict 2.5s client-side timeout.
  - Fallback to safe deterministic error response on timeout or parse failure.
- **TDD Test Scenarios**:
  - `test_extractor_parses_valid_payload`
  - `test_extractor_handles_timeout_with_fallback`
  - `test_extractor_handles_malformed_json_gracefully`

## Issue 06: State Machine & TwiML Appointment Flow
- **Prerequisites**: Issue 04, Issue 05
- **Target Files**:
  - `src/services/conversation.py`
  - `tests/test_conversation.py`
- **Acceptance Criteria**:
  - Manages turn states: GREETING -> COLLECTING_INFO -> CONFIRMING -> BOOKED.
  - Generates valid TwiML `<Gather input="speech">` and `<Say>` tags.
  - Atomic insert of appointment on customer confirmation.
- **TDD Test Scenarios**:
  - `test_full_conversation_happy_path`
  - `test_appointment_created_only_upon_explicit_confirmation`

## Issue 07: Observability, Latency Metrics & Integration Suite
- **Prerequisites**: Issues 01-06
- **Target Files**:
  - `src/middleware/metrics.py`
  - `tests/test_integration_end_to_end.py`
- **Acceptance Criteria**:
  - Measures request durations; exposes summary histograms/metrics.
  - End-to-end simulated 4-turn call creates exactly 1 booking record.
- **TDD Test Scenarios**:
  - `test_latency_middleware_records_timings`
  - `test_end_to_end_simulated_call`
