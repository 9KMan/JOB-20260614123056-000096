# Data Pipeline Service

Streaming-first data pipeline for the KMan platform. Built for batch
workloads: e-commerce platform aggregation, large-dataset analytics
(RFM, funnel, cohort, anomaly detection).

## Philosophy

**Never load a full dataset into memory.** Every read is a streaming
async iterator. Every batch is sized to fit in memory with a
configurable ceiling. Every pipeline job has a `progress` field and
supports cancellation.

## Endpoints

| Method | Path                          | Description                          |
|--------|-------------------------------|--------------------------------------|
| GET    | /health                       | Liveness                             |
| POST   | /api/v1/jobs                  | Create a pipeline job                |
| GET    | /api/v1/jobs                  | List recent jobs                     |
| GET    | /api/v1/jobs/{id}             | Get job status                       |
| POST   | /api/v1/jobs/{id}/cancel      | Request cancellation                 |
| GET    | /api/v1/datasets/orders       | Paginated read of orders             |
| GET    | /api/v1/datasets/inventory    | Inventory snapshot                   |
| POST   | /api/v1/analytics/rfm         | RFM segmentation                     |
| POST   | /api/v1/analytics/funnel      | Funnel analysis                      |
| POST   | /api/v1/analytics/cohort      | Cohort retention                     |
| POST   | /api/v1/analytics/anomalies   | Anomaly detection on a series        |

## Analyzers

All in `app/core/analyzers.py` — pure functions, deterministic, unit-testable.

- **RFM** — recency/frequency/monetary segmentation. Segments: champions, loyal, at_risk, hibernating, new, regular.
- **Funnel** — step-by-step conversion rates.
- **Cohort retention** — by day / week / month cohort.
- **Anomalies** — sigma-based outlier detection on a numeric series.
- **Moving average** — for smoothing before anomaly detection.

## E-commerce Connector

`EcommerceConnector` is the base class. The default is `MockEcommerceConnector`,
which yields synthetic data for dev/test. To add a real platform:

1. Subclass `EcommerceConnector`
2. Implement `list_orders`, `list_products`, `list_inventory`, `list_customers` as async iterators
3. Add the new platform to `make_connector()`

Streaming throughout — never load the full result set into memory.
All HTTP calls go through `shared.common.http.ServiceClient` which
includes a circuit breaker.

## Job Lifecycle

```
pending → running → done
                  → failed
                  → cancelled (via /cancel endpoint)
```

Jobs are processed by `JobRunner` (started in app lifespan) with a
configurable concurrency cap (default 2). Progress is exposed via the
job's `progress` field (0..1).

## Environment

| Variable                | Default     | Description                  |
|-------------------------|-------------|------------------------------|
| `KMAN_ECOM_PLATFORM`    | `mock`      | Connector platform           |
| `DATABASE_URL`          | (postgres)  | Optional persistence         |
| `REDIS_URL`             | (redis)     | Optional pub/sub             |

## Local Development

```bash
pip install -e ../../shared
pip install -e .
uvicorn app.main:app --reload --port 8003
```
