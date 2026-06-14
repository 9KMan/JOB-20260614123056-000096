# Reporting Service

Scheduled + on-demand reports. Outputs JSON / CSV / Markdown / HTML.
Delivers to the WhatsApp workspace via the WhatsApp adapter.

## Templates

| Name | Description | Default schedule |
|------|-------------|------------------|
| `daily_order_summary` | Daily order status breakdown + top SKUs | `0 8 * * *` |
| `weekly_compensation` | Weekly compensation spend by decision type | `0 9 * * MON` |
| `weekly_dispute_summary` | Weekly dispute resolution summary | `0 10 * * MON` |
| `stock_coverage` | Stock coverage + low-stock alerts | `0 7 * * *` |
| `executive_dashboard` | One-page digest combining all key metrics | `0 8 * * *` |

## Endpoints

| Method | Path                              | Description                       |
|--------|-----------------------------------|-----------------------------------|
| GET    | /health                           | Liveness                          |
| GET    | /healthz/scheduler                | Scheduler status                  |
| GET    | /api/v1/templates                 | List available templates          |
| POST   | /api/v1/reports                   | Generate a report on demand       |
| GET    | /api/v1/reports                   | List recent reports               |
| GET    | /api/v1/reports/{id}              | Get report detail                 |
| GET    | /api/v1/reports/{id}/download     | Download report artifact          |
| GET    | /api/v1/schedules                 | List scheduled reports            |
| POST   | /api/v1/schedules                 | Create a schedule                 |
| PUT    | /api/v1/schedules/{id}            | Update a schedule                 |
| DELETE | /api/v1/schedules/{id}            | Delete a schedule                 |

## Delivery

Reports can be delivered to the WhatsApp workspace on completion
(scheduled runs always deliver to the configured recipients; on-demand
runs deliver only when `deliver: true` is set in the request body).

Delivery is best-effort — failure to deliver does NOT fail the report.
The report summary records the delivery outcome.

## Scheduler

APScheduler with `AsyncIOScheduler`. On startup, all enabled
`ReportSchedule` rows are loaded and registered as cron jobs. Adding or
updating a schedule via the API triggers a reload.

## Environment

| Variable                    | Default                       | Description                |
|-----------------------------|-------------------------------|----------------------------|
| `KMAN_REPORT_OUTPUT_DIR`    | `/tmp/kman-reports`           | Where artifacts are saved  |
| `KMAN_WHATSAPP_URL`         | `http://whatsapp_adapter:8005` | WhatsApp adapter URL      |
| `KMAN_ACCOUNT_ID`           | `default`                     | Account ID for delivery    |
| `DATABASE_URL`              | (postgres)                    | Schedule + report metadata |
| `REDIS_URL`                 | (redis)                       | Event publishing           |

## Local Development

```bash
pip install -e ../../shared
pip install -e .
uvicorn app.main:app --reload --port 8004
```
