# API Reference

Generated from the FastAPI OpenAPI schemas. The full interactive docs
are at `/docs` on each running service.

| Service             | Port | OpenAPI docs | ReDoc |
|---------------------|------|--------------|-------|
| automation_engine   | 8001 | http://localhost:8001/docs | http://localhost:8001/redoc |
| ai_judgment         | 8002 | http://localhost:8002/docs | http://localhost:8002/redoc |
| data_pipeline       | 8003 | http://localhost:8003/docs | http://localhost:8003/redoc |
| reporting           | 8004 | http://localhost:8004/docs | http://localhost:8004/redoc |
| whatsapp_adapter    | 8005 | http://localhost:8005/docs | http://localhost:8005/redoc |

## Cross-cutting Conventions

### Correlation IDs

Every request gets an `X-Correlation-Id` header. If the caller provides
one, it's echoed back. If not, the service generates a 16-char hex
string. This ID flows through queue messages and audit log entries,
so you can trace a single request across all five services.

### Error Envelope

Errors are returned as JSON with a consistent shape:

```json
{
  "error": {
    "code": "internal_error",
    "message": "human-readable description",
    "correlation_id": "abc123",
    "timestamp": "2026-06-14T15:00:00.000Z"
  }
}
```

### CORS

All services allow CORS from the origins in `CORS_ORIGINS` (default
`*` in dev). Tighten this in production.

### Auth

JWT (HS256) is supported via `JWT_SECRET`. This build does not include
a login flow — the expectation is that an upstream gateway (e.g. the
WhatsApp workspace itself) mints tokens.

## Inter-Service Contracts

The wire types that flow between services are defined in
`shared/contracts/`. See the module docstrings for the full schema.

- `automation_contract.py` — order/delay/stock/dispute types
- `ai_contract.py` — judgment/classify/extract/summarize types
- `whatsapp_contract.py` — delivery request/response types

## Event Bus

Services emit domain events on Redis pub/sub channels:

- `kman:events:report_ready`
- `kman:inbound` (WhatsApp workspace → this platform)

The events are JSON-serialized dataclasses — see
`shared/messaging/events.py` for the registry.
