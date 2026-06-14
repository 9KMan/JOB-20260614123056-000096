# KMan Workflow Automations & Data Analyses

**Microservice-based Python + AI platform for e-commerce / dropshipping account management.**

Built by: **KMan | AI-Augmented Engineering Factory**

## Business Problem Solved

Account managers for e-commerce and dropshipping clients spend the bulk of their day on
recurring workflows: order checks, delay and compensation handling, dispute triage,
stock control, and reporting. Today these are manual — slow, error-prone, and
expensive. This platform automates the deterministic work and uses AI for the
judgment calls, freeing account managers to focus on the small fraction of cases
that actually need a human.

## Key Outcomes

- **Routine automations run unattended** — order status checks, delay detection,
  compensation decisions, low-stock alerts, scheduled reports.
- **Disputes get triaged consistently** — rule-based pre-screen + AI judgment,
  with confidence-based escalation to a human when uncertain.
- **Reports arrive on time, every time** — daily/weekly digest to the account
  manager's WhatsApp workspace, with full audit trail.
- **One integration point** — only the WhatsApp Adapter talks to the chat provider.
  The other services call this adapter through a clean webhook contract.

## What's Inside

| Service             | Port | Purpose                                              |
|---------------------|------|------------------------------------------------------|
| `automation_engine` | 8001 | Rule-based automations: orders, delays, stock, disputes |
| `ai_judgment`       | 8002 | Hosted-first AI service with adapter pattern         |
| `data_pipeline`     | 8003 | Streaming analytics: RFM, funnel, cohort, anomalies  |
| `reporting`         | 8004 | Scheduled + on-demand reports (JSON/CSV/MD/HTML)     |
| `whatsapp_adapter`  | 8005 | The only service that talks to the WhatsApp workspace|

Plus a `shared/` library with cross-service contracts, a Redis queue layer,
an event bus, and a circuit-breaker-wrapped HTTP client.

## Architecture

```
   ┌──────────────────┐
   │ E-commerce APIs  │ (Shopify, WooCommerce, etc.)
   └────────┬─────────┘
            │  (async streaming)
   ┌────────▼─────────┐    rule-based    ┌──────────────────┐
   │  data_pipeline   │  pre-screen +    │  automation_     │
   │  (RFM, funnel,   │  ───────────────►│  engine          │
   │   cohort)        │                  │  (order checks,  │
   └────────┬─────────┘                  │   delays, stock) │
            │                             └────────┬─────────┘
            │                                      │ judgment calls
            │                                      ▼
            │                             ┌──────────────────┐
            │                             │  ai_judgment     │
            │                             │  (OpenAI / Ant-  │
            │                             │   hropic / vLLM) │
            │                             └────────┬─────────┘
            │                                      │
            │                                      │ results
            │                             ┌────────▼─────────┐
            └────────────────────────────►│  reporting       │
                                          │  (cron, templates│
                                          │   render, deliv- │
                                          │   ery)           │
                                          └────────┬─────────┘
                                                   │ webhook
                                          ┌────────▼─────────┐
                                          │ whatsapp_adapter │ ◄── (only one that
                                          │ (rate-limit,     │      talks to chat
                                          │  dedupe, retry)  │      provider)
                                          └────────┬─────────┘
                                                   │
                                          ┌────────▼─────────┐
                                          │ WhatsApp         │
                                          │ workspace (other │
                                          │ developer's app)  │
                                          └──────────────────┘
```

## Quick Start

### Local (dev)

```bash
git clone https://github.com/9KMan/JOB-20260614123056-000096
cd JOB-20260614123056-000096
docker compose up --build
```

This starts PostgreSQL, Redis, and all five services. Wait for the health
checks, then:

```bash
# Health checks
curl http://localhost:8001/health   # automation engine
curl http://localhost:8002/health   # AI judgment
curl http://localhost:8003/health   # data pipeline
curl http://localhost:8004/health   # reporting
curl http://localhost:8005/health   # WhatsApp adapter
```

### One-off: run a service directly

```bash
cd services/automation_engine
pip install -e ../../shared
pip install -e .
uvicorn app.main:app --reload --port 8001
```

## Tech Stack

- **Backend:** Python 3.11, FastAPI, async SQLAlchemy 2.0, asyncpg
- **AI/ML:** OpenAI, Anthropic, vLLM/Ollama (via the ModelAdapter interface)
- **Messaging:** Redis lists (queue substrate), Redis pub/sub (events)
- **Scheduler:** APScheduler (AsyncIOScheduler)
- **Templating:** Jinja2 (reports)
- **Data:** PostgreSQL 16
- **Containers:** Docker, Docker Compose
- **Tests:** pytest, pytest-asyncio

## Project Structure

```
.
├── README.md                      # this file
├── docker-compose.yml             # all 5 services + postgres + redis
├── pytest.ini                     # test config
├── conftest.py                    # path setup for tests
├── shared/                        # cross-service library
│   ├── common/                    # config, logging, db, http, time
│   ├── messaging/                 # queue contract, events, pubsub
│   └── contracts/                 # Pydantic wire types
├── services/
│   ├── automation_engine/         # rule-based automations (port 8001)
│   ├── ai_judgment/               # hosted AI with adapter pattern (port 8002)
│   ├── data_pipeline/             # streaming analytics (port 8003)
│   ├── reporting/                 # scheduled reports (port 8004)
│   └── whatsapp_adapter/          # only service that talks to chat (port 8005)
├── tests/                         # unit tests (75 tests, all passing)
│   └── unit/
├── docs/                          # additional documentation
└── .planning/                     # phase plans (gitignored, never pushed)
```

## Microservice Principles

1. **Each service is independently deployable.** No service-to-service
   imports — all cross-service communication is via REST or Redis queues.
2. **One service can fail without breaking the rest.** The Automation
   Engine falls back to rule-based dispute triage if the AI service is
   down. The WhatsApp Adapter has retries with exponential backoff and a
   circuit breaker on the workspace webhook.
3. **All I/O is async.** All HTTP is via `shared.common.http.ServiceClient`
   (with circuit breaker). All DB I/O is via `asyncpg` + SQLAlchemy 2.0.
4. **Streaming-first for analytics.** The Data Pipeline never loads a full
   dataset into memory. Reads are async iterators, batches are bounded.
5. **Hosted-first for AI, swap-ready for self-hosted.** The
   `ModelAdapter` interface means business code never depends on a
   specific provider. To migrate from OpenAI to vLLM, you change one
   env var.

## Runbook

See [`docs/RUNBOOK.md`](docs/RUNBOOK.md) for operational procedures.

## Tests

```bash
uv pip install --python /home/deploy/.hermes/hermes-agent/venv/bin/python3 -e shared pytest pytest-asyncio redis
python3 -m pytest tests/unit/ -v
```

## Screening Question Coverage

This codebase is the implementation of the four screening questions
in SPEC.md:

1. **Rule-based + AI mix** — see `services/automation_engine/app/core/rules.py`
   (rules) and `services/ai_judgment/` (AI). The split is documented
   per-workflow in PROPOSAL.md and in each service's README.
2. **Hosted + self-hosted AI** — see `services/ai_judgment/app/adapters/`.
   The hosted-first design with `OPENAI_BASE_URL` swap is a one-env-var
   change.
3. **Microservice fault isolation** — see `services/automation_engine/app/services/dispute_service.py:ai_assisted_triage`
   (falls back to rule-based on AI failure), `services/whatsapp_adapter/app/workers/retry_worker.py`
   (exponential backoff), and `shared/common/http.py:ServiceClient` (circuit breaker).
4. **End-to-end ownership** — this repo: shared library, 5 services,
   tests, Docker Compose, runbook, adapter pattern, integration contract.

## License

MIT.
