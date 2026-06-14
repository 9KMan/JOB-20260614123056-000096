# Architecture Decisions

This document records the *why* behind non-obvious design choices in the
KMan Workflow Automations platform. Read it before making structural changes.

## ADR-001: Microservices over monolith

**Status:** Accepted

**Context:** The brief requires "if one breaks, the rest keeps running".
A monolith shares a single process — one bad request handler can crash the
whole app.

**Decision:** Five independently deployable services. Each has its own
port, its own Dockerfile, its own deployment unit.

**Consequences:**
- (+) Hard isolation: the WhatsApp Adapter can be down without
  affecting the Automation Engine.
- (+) Independent scaling: AI judgment (CPU-bound) can scale separately
  from the Automation Engine (I/O-bound).
- (-) Operational complexity: more services to monitor.
- (-) Cross-service calls: each is a network hop. Mitigated by
  aggressive use of Redis queues for non-blocking work.

## ADR-002: Adapter pattern for AI providers

**Status:** Accepted

**Context:** Screening question #2 explicitly requires the AI system to
support both hosted APIs (OpenAI, Anthropic) and self-hosted models
(vLLM, Ollama). Naively calling `openai.ChatCompletion.create(...)` in
business code would make migration a rewrite.

**Decision:** All AI calls go through `ModelAdapter` (abstract base).
The factory picks the concrete adapter based on `KMAN_AI_PROVIDER`.
vLLM and Ollama adapters are stubs with `NotImplementedError` —
documenting the migration path explicitly is the point.

**Consequences:**
- (+) Migration = change one env var, no code changes.
- (+) New providers = add a subclass of `ModelAdapter`.
- (-) vLLM and Ollama are not implemented in this build (out of scope
  per the brief — "to start" hosted).

## ADR-003: Streaming-first for analytics

**Status:** Accepted

**Context:** The Data Pipeline handles "real data volumes" per the
screening brief. Loading 1M orders into memory to compute RFM
guarantees OOM at scale.

**Decision:** All reads in the Data Pipeline are async iterators. The
`EcommerceConnector` base class mandates `async def list_X(...)` that
yields. The `JobRunner` processes jobs in bounded batches.

**Consequences:**
- (+) Memory profile is bounded regardless of dataset size.
- (+) Cancellation propagates through the async generator.
- (-) Slightly more code (must `async for` everywhere).
- (-) No SQL-style random access mid-iteration. Mitigated by materialized
  snapshots for the dashboard endpoints.

## ADR-004: WhatsApp Adapter is the ONLY service that talks to the chat provider

**Status:** Accepted

**Context:** The brief notes that a separate developer is building the
WhatsApp workspace ("skin"). Two teams integrating separately.

**Decision:** The WhatsApp Adapter owns the webhook contract. Every
other service that needs to send a message calls this adapter. The
adapter is responsible for retries, rate limiting, dedup, HMAC
signing, and inbound verification.

**Consequences:**
- (+) Single point to evolve the integration.
- (+) The other team only needs to implement ONE webhook to be
  compatible with our platform.
- (-) The adapter is a single point of failure for outbound messaging.
  Mitigated by retries + circuit breaker + DLQ table.

## ADR-005: Redis lists as the queue substrate

**Status:** Accepted

**Context:** Need a queue but want to avoid the operational burden of
RabbitMQ / Kafka. The throughput is modest (a few thousand messages/min
at peak).

**Decision:** Use Redis lists (LPUSH/BRPOP) as the queue substrate.
Wrap them in a thin `QueueMessage` type with idempotent enqueue
(SETNX-based dedup).

**Consequences:**
- (+) No new broker to operate.
- (+) Idempotent retry built in.
- (-) No native priority queues, no dead-letter, no DLQ TTL. The DLQ
  table is in PostgreSQL; the queue is in Redis.
- (-) If we ever need >10k msg/s, we'll need to revisit. (We're at
  ~100 msg/s today.)

## ADR-006: PostgreSQL as the only persistent store

**Status:** Accepted

**Context:** All five services need to persist state. Options:
- One shared DB for all services (tight coupling)
- One DB per service (operational overhead)
- A single schema with per-service table prefixes

**Decision:** One PostgreSQL instance with per-service table prefixes
(`automation_*`, `reporting_*`, `whatsapp_*`, `ai_*`).

**Consequences:**
- (+) One operational surface.
- (+) Cross-service queries are possible (for ops dashboards).
- (-) Schema migrations need coordination across services. Mitigated
  by per-service migration directories.
- (-) At very high scale, this would become a bottleneck. Out of
  scope for the brief.
