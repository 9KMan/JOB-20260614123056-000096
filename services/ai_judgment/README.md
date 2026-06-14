# AI Judgment Service

Hosted-first AI service with a **swap-ready adapter pattern** for self-hosted models.

## Why this exists

The screening brief is explicit: AI starts hosted (OpenAI / Anthropic
APIs), but the system must be designed so the migration to self-hosted
models (vLLM, Ollama) requires **zero business-logic changes**.

That goal is met by the `ModelAdapter` abstraction in
`app/adapters/base.py`. Every concrete adapter implements the same four
methods: `complete`, `classify`, `extract`, `summarize`. The rest of
the service consumes that interface.

## Architecture

```
rule service  ──►  AI Judgment Service  ──►  ModelAdapter  ──►  Hosted API
                                                            └─►  vLLM  (future)
                                                            └─►  Ollama (future)
```

## Adapters

| Provider   | Status       | Notes                                                 |
|------------|--------------|-------------------------------------------------------|
| OpenAI     | Implemented  | `gpt-4o-mini` default, JSON mode for structured tasks |
| Anthropic  | Implemented  | `claude-3-5-sonnet` default                           |
| vLLM       | Stub         | OpenAI-compatible; set OPENAI_BASE_URL in the meantime |
| Ollama     | Stub         | OpenAI-compatible; set OPENAI_BASE_URL in the meantime |

## Endpoints

| Method | Path                  | Description                                |
|--------|-----------------------|--------------------------------------------|
| GET    | /health               | Liveness                                   |
| GET    | /adapters             | Active provider + config status            |
| POST   | /api/v1/judgment      | Generic judgment call                      |
| POST   | /api/v1/classify      | Text classification                        |
| POST   | /api/v1/extract       | Structured field extraction                |
| POST   | /api/v1/summarize     | Text summarization                         |

## Environment

| Variable                | Default     | Description                              |
|-------------------------|-------------|------------------------------------------|
| `KMAN_AI_PROVIDER`      | `openai`    | openai / anthropic / vllm / ollama       |
| `KMAN_AI_MODEL`         | provider-specific | Model name to use                  |
| `OPENAI_API_KEY`        | (none)      | Required when KMAN_AI_PROVIDER=openai    |
| `ANTHROPIC_API_KEY`     | (none)      | Required when KMAN_AI_PROVIDER=anthropic |
| `OPENAI_BASE_URL`       | (none)      | Override to point at vLLM / proxy        |
| `VLLM_BASE_URL`         | (none)      | Used by VllmAdapter when implemented     |
| `OLLAMA_BASE_URL`       | (none)      | Used by OllamaAdapter when implemented   |
| `DATABASE_URL`          | (postgres)  | Audit + dispute persistence              |
| `REDIS_URL`             | (redis)     | Queue consumer (QUEUE_DISPUTES)          |

## Migration path: Hosted → Self-hosted

1. Stand up vLLM (or Ollama) with the model you want.
2. If the model server speaks OpenAI's API, point the existing
   `OpenAIAdapter` at it: `OPENAI_BASE_URL=http://vllm:8000/v1`.
3. If you need a dedicated `VllmAdapter`/`OllamaAdapter`, fill in
   the `NotImplementedError` stubs in `app/adapters/vllm_adapter.py`
   and `ollama_adapter.py`. The interface is the same.
4. Set `KMAN_AI_PROVIDER=vllm` (or `ollama`) and restart.
5. No business-logic or API-contract changes.

## Local Development

```bash
export KMAN_AI_PROVIDER=openai
export OPENAI_API_KEY=sk-...
pip install -e ../../shared
pip install -e .
uvicorn app.main:app --reload --port 8002
```

## Cost Tracking

Every call emits a structured audit log entry:

```json
{
  "ts": "2026-06-14T14:55:00.000Z",
  "kind": "ai_call_audit",
  "task": "judge",
  "model": "gpt-4o-mini",
  "tokens_in": 412,
  "tokens_out": 98,
  "cost_cents": 0.013,
  "duration_ms": 740,
  "correlation_id": "...",
  "actor": "system",
  "service": "ai-judgment"
}
```

The `cost_cents` field is computed from the per-model pricing table
in `app/core/cost.py`. Update that table as pricing changes.

## Failure Isolation

The AI service can be down without breaking the rest of the platform:

- The Automation Engine falls back to rule-based dispute triage if
  the AI service is unreachable.
- Adapters retry transient failures with exponential backoff.
- Errors are logged with correlation IDs and never crash the consumer
  loop — failed messages are re-enqueued.
