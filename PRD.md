# Product Requirements Document (PRD)

## 1. Executive Overview
**Problem Statement**  
Our service must reliably handle inbound voice calls from Twilio, understand the caller’s intent via a Large Language Model (LLM), and book appointments in real‑time. The solution should be stateless at the HTTP layer, persist session state safely, and guarantee idempotent processing of Twilio webhook retries.

**Target Operational Metrics**  
| Metric | Target |
|--------|--------|
| Call answer latency (time from Twilio POST to first `<Say>` response) | **< 1.5 seconds** |
| LLM extraction latency (Groq API round‑trip) | **≤ 2.5 seconds** (client‑side timeout) |
| End‑to‑end request latency (P95) | **< 3 seconds** |
| Duplicate webhook handling error rate | **< 0.5 %** |
| System availability (live + ready) | **99.9 %** |
| Database write latency (SQLite WAL) | **≤ 5 ms** (95th percentile) |

---

## 2. System Scope & Ingestion
- **Twilio Voice Webhooks** – Use `<Gather input="speech">` to capture spoken input and `<Say>` for voice prompts. All webhook calls are HTTP POSTs to our stateless handlers.
- **Stateless Handlers + Persistent Session** – Each request is processed without in‑memory session data; the current call state is stored in SQLite and re‑hydrated on every webhook delivery.
- **Local/Offline Simulation Runner** – A CLI‑based simulator reproduces Twilio webhook payloads for automated testing, avoiding consumption of live Twilio credits.
- **Live Calls over TLS Tunnel** – Ngrok provides a secure TLS tunnel (`https://<subdomain>.ngrok.io`) exposing the public endpoints to Twilio during development and staging.

---

## 3. System Constraints
- **Network** – All external traffic must travel over TLS 1.2+; Ngrok tunnel must enforce certificate verification.
- **Security** – Verify every Twilio request using the `X‑Twilio‑Signature` header. No raw PII (e.g., full phone numbers, spoken text) is written to logs; only hashed identifiers are stored.
- **API Versioning** – All public endpoints are prefixed with `/api/v1`. Future versions will be introduced as `/api/v2`, `/api/v3`, etc., without breaking existing contracts.
- **Rate Limiting** –  
  - Twilio webhook rate is bounded by Twilio’s own retry policy (max 5 attempts).  
  - Groq API calls are limited to **30 req/s** per account; a client‑side circuit breaker will open on sustained failures.

---

## 4. Data & State Management
### Database Architecture
- **Engine** – SQLite 3 with Write‑Ahead Logging (WAL) enabled and foreign‑key enforcement.
- **Connection Management** – Bounded connection pool (max 10 connections) with a busy‑timeout of **5000 ms**. All DB access goes through an isolated service layer to simplify future migration to PostgreSQL.
- **Schema Highlights**  

| Table | Primary Key | Important Columns | Indexes |
|-------|-------------|-------------------|---------|
| `calls` | `id` (auto) | `call_sid` (Twilio), `status`, `created_at` | `idx_calls_call_sid` on `call_sid` |
| `webhook_events` | `id` (auto) | `idempotency_key`, `processed_at`, `twiml_response` | `idx_webhook_idempotency` on `idempotency_key` (UNIQUE) |
| `appointments` | `id` (auto) | `slot_start`, `slot_end`, `customer_name`, `status` | Composite index `idx_appointments_slot_status` on (`slot_start`, `status`) (UNIQUE on (`slot_start`, `status`) for confirmed bookings) |

### State & Idempotency
- **Composite Idempotency Key** – `CallSid + action_name + turn_id`. This key is generated for every webhook turn and stored in `webhook_events`.
- **Turn Identifier** – `turn_id` is injected into downstream action URLs (e.g., LLM extraction endpoint) to maintain traceability.
- **Atomic Transactions** – Each webhook processing step runs inside a single SQLite transaction that:
  1. Checks for an existing `idempotency_key`. If present, returns the stored `twiml_response` (safe replay).
  2. Persists the new state (`calls`, `appointments` if a booking is made) and the generated TwiML.
  3. Commits only after all constraints (unique keys, foreign keys) succeed.
- **Unique Constraints** – Enforced on `idempotency_key` and on confirmed appointment slots to prevent double‑booking.

---

## 5. LLM Extraction & Latency Budgets
- **Provider** – Groq API (hosted LLM) returns a structured JSON payload containing:
  - `intent`
  - `customer_name`
  - `service_needed`
  - `requested_time_text`
- **Timeout** – Client‑side timeout of **2.5 seconds**. No retry is performed within the same call turn to avoid exceeding the overall call latency budget.
- **Validation** – Response is validated against a **Pydantic** schema. On validation failure or timeout, the system falls back to deterministic recovery phrases (e.g., “I’m sorry, I didn’t catch that. Could you repeat?”) and logs the incident.
- **Separation of Concerns** – The LLM never writes to the `appointments` table. After extraction, the application logic performs conflict checks and, if safe, creates the booking inside the same atomic transaction.

---

## 6. API Versioning, Routing & Health Probes
### Endpoints
| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/v1/voice/incoming` | Call initialization – creates a `calls` record and returns the first `<Gather>` TwiML. |
| `POST` | `/api/v1/voice/turn` | Iterative Gather/Say loop – processes each speech turn, invokes Groq, updates state, and returns next TwiML. |
| `POST` | `/api/v1/voice/status` | Call lifecycle cleanup – marks call as completed, releases resources, and logs final metrics. |
| `GET`  | `/health/live` | Liveliness probe – verifies the process is running; does **not** depend on external services. |
| `GET`  | `/health/ready` | Readiness probe – checks configuration load, SQLite read/write capability, and Groq circuit‑breaker status (degraded flag if open). |

### Observability
- **Structured JSON Logging** – Every request logs: `request_id`, `call_sid`, `endpoint`, `turn_id`, `latency_ms`, `status_code`, and a **hash** of any PII. No raw speech text is logged.
- **Latency Tracking** – Prometheus‑compatible histograms for request latency (`p50`, `p95`, `p99`) per endpoint.
- **Circuit Breaker** – Groq client wrapped with a circuit‑breaker; when open, `/health/ready` reports `degraded: true` and the system returns fallback phrases.

---

## 7. Non‑Functional Requirements
- **Memory Management** – The service must not exceed **150 MB** RSS in steady state; periodic GC checks and explicit closing of DB cursors are required.
- **Async Concurrency Limits** – Maximum of **20** concurrent inbound webhook processing tasks to keep SQLite contention low.
- **Fault Tolerance** – All external calls (Twilio, Groq) are wrapped with timeout and retry policies (max 2 retries for non‑idempotent operations). On permanent failure, the caller receives a graceful error message and the event is persisted for later manual review.
- **Scalability** – Although SQLite is sufficient for the MVP, the isolated data‑access layer is designed for a drop‑in PostgreSQL implementation with minimal code changes.
- **Compliance** – No storage of raw audio or speech transcripts; only derived intent data is persisted, complying with GDPR and local data‑privacy regulations.

---

## 8. Acceptance Criteria
1. **Functional** – All three API endpoints respond with valid TwiML, handle duplicate webhook deliveries idempotently, and correctly create appointments without double‑booking.
2. **Performance** – End‑to‑end latency meets the targets defined in Section 1 under load of **100 concurrent calls**.
3. **Reliability** – Health probes return `200 OK` when the service is ready; `/health/ready` reflects Groq circuit‑breaker state accurately.
4. **Observability** – Logs are JSON‑formatted, contain no raw PII, and latency histograms are exposed on `/metrics`.
5. **Security** – Every incoming Twilio request passes signature verification; all external traffic is TLS‑encrypted.

---  

*Prepared according to the “To PRD” skill guidelines (see `.claude/skills/to-prd.md`).*