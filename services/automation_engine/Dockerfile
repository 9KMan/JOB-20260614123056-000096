FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps for asyncpg / psycopg wheels
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

# Install shared library and the service itself
COPY shared /app/shared
COPY services/automation_engine /app/services/automation_engine

ENV PYTHONPATH=/app:/app/services/automation_engine

RUN pip install --upgrade pip && \
    pip install -e /app/shared && \
    pip install -e /app/services/automation_engine

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -fsS http://localhost:8001/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
