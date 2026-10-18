# 📞 AI HVAC & Home Services Voice Receptionist

[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Groq](https://img.shields.io/badge/Groq-Llama_3-f55036)](https://groq.com)
[![SQLite](https://img.shields.io/badge/SQLite-WAL_Mode-003B57?logo=sqlite&logoColor=white)](https://sqlite.org)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)

An asynchronous, voice-first AI receptionist backend engineered for residential home services (HVAC, plumbing, electrical). The system processes telephony webhooks (Twilio TwiML), performs low-latency structured entity extraction using Groq, guides callers through a deterministic finite-state machine to collect scheduling slots, and persists bookings in SQLite with strict idempotency guarantees.

---

## 🏛️ System Architecture

```text
 Telephony Webhook (Twilio / HTTP Test Harness)
                   |
                   v  POST /api/v1/voice/incoming
       +-----------------------+
       |  FastAPI Application  |
       +-----------+-----------+
                   |
                   +---> [Metrics & Audit Middleware]
                   |
                   v
       +-----------------------+
       |    Webhook Service    |<---> [Idempotency Guard (SQLite)]
       +-----------+-----------+
                   |
                   v
       +-----------------------+
       | Conversation Manager  |
       +-----------+-----------+
                   |
         +---------+-------------------------+
         v                                   v
+------------------+               +------------------+
|  LLM Extractor   |               |  State Machine   |
|   (Groq Cloud)   |               |   Transitions    |
+------------------+               +---------+--------+
         |                                   |
         | Structured JSON                   | Next State + TwiML
         +-----------------> <---------------+
                           |
                           v
                 +-------------------+
                 |   SQLite (WAL)    |
                 | - appointments    |
                 | - calls           |
                 | - webhook_events  |
                 +-------------------+
```

---

## ⚙️ Core Technical Capabilities

### 1. Deterministic Multi-Turn State Machine
Rather than granting an LLM unconstrained control over conversation flow and database updates, this architecture decouples **semantic extraction** from **control flow**:
* **GREETING (Turn 0)**: Emits initial greeting TwiML and initiates speech capture.
* **COLLECTING_INFO (Turn 1)**: Extracts core slots (`customer_name`, `service_needed`, `slot_start`). If mandatory slots are missing or invalid, the machine re-prompts for clarification and remains in `COLLECTING_INFO`.
* **CONFIRMING (Turn 2)**: Summarizes extracted appointment slots back to the caller for verbal confirmation (`"Yes"`, `"Please confirm"`).
* **COMPLETED**: Atomically writes the verified booking to the database and delivers concluding TwiML.

### 2. Strict Domain Guardrails & Out-of-Scope Rejection
The entity extraction pipeline enforces trade-specific validation:
* **In-Scope Intent:** *"My AC is broken, can someone come tomorrow at 2 PM?"* -> Correctly normalizes service trade to `hvac` and extracts the requested time slot.
* **Out-of-Scope Intent:** *"Can I get a large cheese pizza delivered?"* -> Non-maintenance requests result in `service_needed = null`, preventing transition to `CONFIRMING` and prompting the caller to specify a valid home repair need.

### 3. Telephony Webhook Idempotency
Telephony carriers retry unacknowledged webhook deliveries automatically upon latency spikes. To eliminate duplicate reservations:
* Every turn computes a compound idempotency key:
  `idempotency_key = CallSid + ":" + endpoint + ":" + turn_id`
* If an incoming key already exists in `webhook_events`, execution immediately short-circuits and replays the cached TwiML response.
* SQLite Write-Ahead Logging (`PRAGMA journal_mode=WAL;`) guarantees transactional safety under concurrent access.

### 4. Resilient Fallbacks
* **LLM Deadlines:** Wrapped in strict HTTP timeouts via `httpx.AsyncClient`. Timeouts or unparseable JSON payloads trigger a rule-based deterministic fallback prompt instead of dropping the call.
* **Silence & Disconnects:** Twilio `<Gather>` elements feature configured timeouts to terminate inactive sessions cleanly.

---

## 🛠️ Tech Stack

* **Framework:** FastAPI (Asynchronous ASGI endpoints)
* **LLM Engine:** Groq Cloud (`llama-3.1-8b-instant` / OpenAI-compatible API)
* **Database:** SQLite with WAL mode enabled
* **Telephony Protocol:** Twilio Voice TwiML (XML synthesis and speech gathering)
* **Data Modeling:** Pydantic v2 & `pydantic-settings`
* **Server:** Uvicorn

---

## 🗄️ Database Schema

* `calls`: Tracks session status, caller number, active turn count, and timestamps.
* `appointments`: Stores confirmed bookings (`customer_name`, `service_needed`, `slot_start`, `status`).
* `webhook_events`: Stores raw idempotency records and cached TwiML payloads.

---

## 🚀 Getting Started

### 1. Prerequisites
* Python 3.11+
* Groq Cloud API Key

### 2. Installation
```powershell
# Clone the repository
git clone https://github.com/drazaH21/ai-hvac-voice-receptionist.git
cd ai-hvac-voice-receptionist

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Setup
Create a `.env` file in the root directory:
```env
DATABASE_URL=sqlite:///receptionist.db
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
GROQ_TIMEOUT_SECONDS=3.0
```

### 4. Initialize Database
```powershell
python -c "from src.db.connection import init_db; init_db(); print('Database tables initialized!')"
```

### 5. Start the Server
```powershell
uvicorn src.main:app --reload --port 8000
```

---

## 🧪 Telephony Simulation Test Harness

Simulate the end-to-end multi-turn conversation locally using PowerShell without needing an active Twilio number:

#### Turn 0: Inbound Call
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/voice/incoming" -Method Post -Body @{
    CallSid = "CA_DEMO_CALL_101"
    From = "+15551234567"
}
```

#### Turn 1: Caller Details (Extraction via Groq)
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/voice/turn?turn_id=1" -Method Post -Body @{
    CallSid = "CA_DEMO_CALL_101"
    SpeechResult = "Hi, my name is Alex and my AC is broken. Can someone come tomorrow at 2 PM?"
}
```

#### Turn 2: Caller Confirmation (Database Persistence)
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/voice/turn?turn_id=2&state=CONFIRMING" -Method Post -Body @{
    CallSid = "CA_DEMO_CALL_101"
    SpeechResult = "Yes, please confirm that."
}
```

#### Verify SQLite Record
```powershell
python -c "import sqlite3; conn = sqlite3.connect('receptionist.db'); print(conn.execute('SELECT * FROM appointments').fetchall())"
```