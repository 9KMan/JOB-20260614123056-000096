# Automation Engine

Rule-based automations for the KMan e-commerce / dropshipping platform.

## Purpose

This service runs the deterministic, threshold-based automations:
order status checks, delay detection, compensation decisions, stock
control, and dispute pre-screen. It is the **fast path** for routine
work. The **judgment path** (dispute triage, nuanced tone analysis,
response drafting) is handled by the AI Judgment Service.

## Endpoints

| Method | Path                       | Description                                  |
|--------|----------------------------|----------------------------------------------|
| GET    | /health                    | Liveness probe                               |
| GET    | /healthz/scheduler         | Scheduler status + next run times            |
| POST   | /api/v1/orders/check       | Run an order check                           |
| GET    | /api/v1/orders             | List recent orders                           |
| POST   | /api/v1/delays/detect      | Detect whether an order is past its SLA      |
| POST   | /api/v1/delays/decide      | Decide compensation for a delayed order      |
| POST   | /api/v1/stock/check        | Check stock for a SKU                        |
| GET    | /api/v1/stock/alerts       | List low-stock alerts                        |
| POST   | /api/v1/disputes/triage    | Triage a dispute (rule-based or AI-assisted) |
| GET    | /api/v1/disputes           | List recent triaged disputes                 |

## Rule Engine

All rule logic lives in `app/core/rules.py` and is unit-testable
without any I/O. The rules cover:

- **Delay detection** — computes days past expected delivery
- **Compensation eligibility** — tiered by delay duration and order value
- **Compensation decision** — refund / partial refund / coupon / reject
- **Low-stock check** — qty vs reorder threshold
- **Stock trend** — rising / stable / dropping from history
- **Dispute pre-screen** — flags for legal threats, refund requests, aggressive tone

## Scheduled Jobs (APScheduler)

- `scan_orders` — every 5 minutes, enqueue order checks
- `scan_delays` — every 15 minutes, enqueue delay detections
- `scan_stock` — every 30 minutes, enqueue stock checks

## Environment

| Variable                | Default                                            | Description                |
|-------------------------|----------------------------------------------------|----------------------------|
| `SERVICE_NAME`          | `automation-engine`                                | Service identity           |
| `DATABASE_URL`          | `postgresql+asyncpg://kman:kman@postgres:5432/kman` | Database                   |
| `REDIS_URL`             | `redis://redis:6379/0`                             | Redis (queues)             |
| `KMAN_AI_URL`           | `http://ai_judgment:8002`                          | AI service URL             |
| `KMAN_AI_TIMEOUT`       | `8.0`                                              | AI HTTP timeout (seconds)  |
| `CORS_ORIGINS`          | `["*"]`                                            | JSON list                  |
| `LOG_LEVEL`             | `INFO`                                             | Root log level             |

## Local Development

```bash
pip install -e ../../shared
pip install -e .
uvicorn app.main:app --reload --port 8001
```

## Docker

```bash
docker build -t kman-automation-engine .
docker run --rm -p 8001:8001 \
  -e DATABASE_URL=postgresql+asyncpg://kman:kman@host:5432/kman \
  -e REDIS_URL=redis://host:6379/0 \
  -e KMAN_AI_URL=http://host:8002 \
  kman-automation-engine
```

## Failure Isolation

This service can fail without taking down the rest of the platform:

- Outbound calls to the AI service go through a circuit breaker
  (`shared.common.http.ServiceClient`). If the AI service is down, the
  Automation Engine falls back to rule-based dispute triage.
- DB and Redis are owned by this service; their outage does not
  impact other services.
- The scheduler re-enqueues failed enqueues on a short backoff.
