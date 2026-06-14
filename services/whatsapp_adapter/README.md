# WhatsApp Adapter

**The only service that talks to the other developer's WhatsApp workspace.**

This service is the integration boundary. Internal services (Automation
Engine, AI Judgment, Reporting) call this service — they never call the
underlying chat provider directly. This gives us:

- A single point to evolve the integration
- Idempotent delivery (dedupe IDs)
- Rate limiting (token bucket per destination)
- Retries with exponential backoff
- HMAC signature verification on inbound
- Best-effort delivery semantics

## Webhook Contract (this service → WhatsApp workspace)

**Outbound delivery request:**

```http
POST /api/v1/workspace/deliver
Content-Type: application/json
X-KMan-Signature: <hex(hmac_sha256(secret, body))>

{
  "id": "uuid",
  "channel": "whatsapp",
  "account_id": "acct-123",
  "correlation_id": "abc123",
  "messages": [
    {
      "id": "msg-uuid",
      "to": "+15551234567",
      "body": "Hello",
      "media_url": null,
      "metadata": {"key": "value"}
    }
  ]
}
```

**Outbound delivery response (success):**

```http
200 OK

{
  "id": "uuid",
  "accepted": 1,
  "rejected": 0,
  "errors": [],
  "delivered_at": "2026-06-14T14:55:00Z"
}
```

**Error responses:**

- `400` — validation error, do NOT retry
- `429` — rate limited, retry with `Retry-After`
- `5xx` — workspace down, retry with backoff

## Inbound Webhook (WhatsApp workspace → this service)

```http
POST /api/v1/webhooks/incoming
Content-Type: application/json
X-KMan-Signature: <hex(hmac_sha256(secret, body))>

{ "from": "+15551234567", "body": "hi", ... }
```

We verify the HMAC, publish the payload to the `kman:inbound` Redis
pub/sub channel, and return `202 Accepted` immediately.

## Internal Endpoints

| Method | Path                              | Description                       |
|--------|-----------------------------------|-----------------------------------|
| GET    | /health                           | Liveness                          |
| POST   | /api/v1/deliver                   | Internal: deliver a batch         |
| GET    | /api/v1/messages/{id}             | Get delivery status for a message |
| GET    | /api/v1/messages                  | List recent deliveries            |
| POST   | /api/v1/webhooks/incoming         | Inbound from workspace            |

## Rate Limiting

Per-destination token-bucket. Defaults: capacity 5, refill 0.5/sec
(1 message every 2 seconds). Configurable via env.

The limiter uses an atomic Redis Lua script so multiple adapter
instances see the same state. If Redis is unavailable, the limiter
fails open (allows the message) — better to risk duplicates than to
drop messages.

## Retry Semantics

- 5xx from workspace → retry with backoff (max 5 attempts)
- 429 from workspace → retry after `Retry-After` header
- 4xx from workspace → mark as `rejected`, do NOT retry
- Circuit breaker opens after 5 consecutive failures

## Idempotency

Each message has a `dedupe_id` (default: the message's own `id`). The
adapter's dedupe store (`SETNX` with 24h TTL) ensures retries do not
produce duplicate deliveries.

## Environment

| Variable                          | Default                           | Description              |
|-----------------------------------|-----------------------------------|--------------------------|
| `KMAN_WORKSPACE_WEBHOOK_URL`      | `http://whatsapp-workspace:8000`  | Workspace webhook URL    |
| `KMAN_WORKSPACE_WEBHOOK_SECRET`   | (empty)                           | HMAC secret              |
| `KMAN_WHATSAPP_RATE_CAPACITY`     | `5`                               | Token bucket capacity    |
| `KMAN_WHATSAPP_RATE_REFILL`       | `0.5`                             | Refill rate per second   |
| `REDIS_URL`                       | `redis://redis:6379/0`            | Dedupe + rate limiter    |
| `DATABASE_URL`                    | (postgres)                        | DeliveryAttempt storage  |

## Local Development

```bash
pip install -e ../../shared
pip install -e .
uvicorn app.main:app --reload --port 8005
```

## Mocking the Workspace

In dev, point `KMAN_WORKSPACE_WEBHOOK_URL` at a mock server. The
adapter will POST delivery requests there. The mock should accept
the contract above and return `200 OK` with the documented response.
