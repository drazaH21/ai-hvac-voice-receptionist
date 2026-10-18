# Skill: To PRD

## Purpose
Convert the output of the /grill-me discovery session into a structured, production-ready Product Requirements Document (PRD.md).

## Required Output Structure
1. **Executive Overview**: Problem statement and target operational metrics (e.g., call answer latency < 1.5s).
2. **System Constraints**: Network, security (TLS), API versioning, rate limiting.
3. **Data & State Management**: Database schema, indexing requirements, connection pooling, idempotency keys.
4. **External Integrations**: Twilio Webhook contract, Groq LLM latency budget, CRM persistence.
5. **Observability & Health**: `/health/live`, `/health/ready`, structured JSON logs, latency tracing.
6. **Non-Functional Requirements**: Memory leak boundaries, async concurrency limits.
