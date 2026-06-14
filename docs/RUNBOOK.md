# Operational Runbook

This document is the operator's playbook for the KMan Workflow Automations platform.

## Services

| Service             | Port | Health check | Liveness interval |
|---------------------|------|--------------|-------------------|
| automation_engine   | 8001 | `/health`    | 30s               |
| ai_judgment         | 8002 | `/health`    | 30s               |
| data_pipeline       | 8003 | `/health`    | 30s               |
| reporting           | 8004 | `/health`    | 30s               |
| whatsapp_adapter    | 8005 | `/health`    | 30s               |

## Common Operations

### Restart a single service

```bash
docker compose restart automation_engine
```

### View logs

```bash
docker compose logs -f --tail=200 automation_engine
```

### Tail a queue

```bash
docker compose exec redis redis-cli LLEN kman:queue:disputes
docker compose exec redis redis-cli LRANGE kman:queue:disputes 0 -1
```

### Check circuit breaker state (per-service)

The circuit breaker is in-process. To check it, hit a service's
/health endpoint and look for the breaker state in the response —
or look at the logs for "circuit breaker opened/closed" lines.

### Trigger an ad-hoc report

```bash
curl -X POST http://localhost:8004/api/v1/reports \
  -H 'Content-Type: application/json' \
  -d '{
    "template": "daily_order_summary",
    "period": "2026-06-14",
    "output_format": "markdown",
    "data": {},
    "deliver": false
  }'
```

### Manually enqueue an order check

```bash
docker compose exec redis redis-cli LPUSH kman:queue:order_checks \
  '{"dedupe_id":"manual-1","correlation_id":"manual","enqueued_at":"2026-06-14T15:00:00Z","payload":{"order_id":"ORD-1234"}}'
```

## Failure Modes

### "AI service is down — disputes are still being triaged, but with rule-based verdicts only"

- The Automation Engine's `dispute_service.ai_assisted_triage` catches
  any exception from the AI service and returns the rule-based verdict
  with confidence=0.0.
- Verify by checking `ai_judgment` logs. Restart it.
- No action needed for in-flight disputes.

### "WhatsApp adapter is failing deliveries"

- Check the workspace webhook URL: `KMAN_WORKSPACE_WEBHOOK_URL`
- Check the workspace's health (the other developer's service)
- Failed deliveries are persisted in `whatsapp_delivery_attempts` table
  with `status='failed'`. The retry worker picks them up every 30s.
- After 5 attempts the row is left as-is. Operator can manually retry
  by POSTing to `/api/v1/deliver` with a fresh request_id.

### "Rate limit hit at the workspace"

- 429 responses are retried with `Retry-After` honored.
- The token bucket is per-destination (phone number).
- To temporarily raise the limit, increase `KMAN_WHATSAPP_RATE_REFILL`.

### "Report scheduler is not running"

- Hit `GET /healthz/scheduler` on the reporting service. It returns
  the list of registered jobs and their next run times.
- If empty, the service failed to load schedules from the DB on startup.
  Check DB connectivity and the `ReportSchedule` table.

### "Order check is returning 'shipped' for every order"

- Likely the rule engine has regressed. Check `app/core/rules.py` and
  the unit tests: `pytest tests/unit/test_rules.py`.
- The "needs_action" flag should fire for high-risk destinations,
  tracking-without-carrier cases, etc.

## Migrations

Each service uses SQLAlchemy 2.0 declarative ORM. The `Base` is
`shared.common.db.Base`. To create the schema:

```python
from shared.common.db import get_engine
from shared.common.db import Base
# Import all models so SQLAlchemy sees them:
from app.models.orm import Order, StockLevel, Compensation, Dispute
# Then:
async with get_engine().begin() as conn:
    await conn.run_sync(Base.metadata.create_all)
```

In production use Alembic — the structure is set up for it (the
`alembic/` directory exists, ready to be initialized per-service).

## Backups

- PostgreSQL: standard `pg_dump` cron (not included here — depends on
  the deployment target).
- Redis: optional RDB snapshots via `SAVE` or AOF.
- Report artifacts: stored under `KMAN_REPORT_OUTPUT_DIR` (default
  `/var/kman/reports` in Docker). Mount as a persistent volume.

## Metrics

Each service exposes `/health` (liveness). For full observability,
add Prometheus instrumentation via `prometheus-fastapi-instrumentator`
(not included in this build — out of scope).

## Cost Monitoring

The AI service emits structured audit log entries on every call:

```json
{
  "kind": "ai_call_audit",
  "task": "judge",
  "model": "gpt-4o-mini",
  "tokens_in": 412,
  "tokens_out": 98,
  "cost_cents": 0.013,
  "duration_ms": 740
}
```

Pipe these to your log aggregator and set up alerts on:
- `cost_cents` per minute > threshold
- `duration_ms` p99 > 10s
- error rate > 1%
