# Tests

Unit tests for the KMan platform. Tests are organized by service:

- `test_rules.py` — Automation Engine rule engine (pure functions)
- `test_ai_parsers.py` — AI Judgment JSON parsers + cost calculator
- `test_analyzers.py` — Data Pipeline RFM, funnel, cohort, anomalies, MA
- `test_reporting.py` — Reporting aggregations + templates
- `test_contracts.py` — Shared contracts and events (round-trip serialization)
- `test_whatsapp.py` — WhatsApp adapter HMAC signature verification

## Running

```bash
pip install pytest pytest-asyncio
pytest tests/
```

## Coverage Map

| Module                        | Test file              | Coverage target |
|-------------------------------|------------------------|-----------------|
| `services/automation_engine/app/core/rules.py` | `test_rules.py` | delay detection, compensation, stock, dispute pre-screen |
| `services/ai_judgment/app/core/parsers.py`     | `test_ai_parsers.py` | JSON extraction, cost estimation |
| `services/ai_judgment/app/core/cost.py`        | `test_ai_parsers.py` | per-model pricing |
| `services/data_pipeline/app/core/analyzers.py` | `test_analyzers.py` | RFM, funnel, cohort, MA, anomalies |
| `services/reporting/app/core/aggregations.py`  | `test_reporting.py` | summarize_orders/compensations/disputes/stock |
| `services/reporting/app/core/templating.py`    | `test_reporting.py` | template list + render |
| `shared/contracts/*`                            | `test_contracts.py` | Pydantic round-trip |
| `shared/messaging/events.py`                    | `test_contracts.py` | event serialization |
| `shared/messaging/queue_contract.py`            | `test_contracts.py` | QueueMessage round-trip |
| `services/whatsapp_adapter/app/services/inbound_service.py` | `test_whatsapp.py` | HMAC verification |

## What's NOT Covered (out of scope for unit tests)

- Live HTTP calls to hosted AI APIs (smoke test in CI only)
- Redis Lua rate-limit script behavior (integration test, not unit)
- Database round-trips (integration test, not unit)
- Workspace webhook HMAC end-to-end (integration test)
- Scheduler cron timing (integration test)
