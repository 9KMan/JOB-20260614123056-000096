FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

COPY shared /app/shared
COPY services/whatsapp_adapter /app/services/whatsapp_adapter

ENV PYTHONPATH=/app:/app/services/whatsapp_adapter

RUN pip install --upgrade pip && \
    pip install -e /app/shared && \
    pip install -e /app/services/whatsapp_adapter

EXPOSE 8005

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -fsS http://localhost:8005/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8005"]
