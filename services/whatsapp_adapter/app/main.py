"""FastAPI app for the WhatsApp Adapter."""

from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Any, Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

_WORKSPACE_ROOT = os.environ.get(
    "KMAN_WORKSPACE_ROOT",
    "/home/deploy/squad/build-worker/JOB-20260614123056-000096",
)
if _WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, _WORKSPACE_ROOT)

from shared.common.config import get_settings  # noqa: E402
from shared.common.ids import new_correlation_id  # noqa: E402
from shared.common.logging import configure_logging  # noqa: E402
from shared.common.time import utcnow  # noqa: E402
from shared.messaging.queue_contract import close_redis  # noqa: E402

from app.api import deliver, health, status, webhooks  # noqa: E402
from app.workers.retry_worker import RetryWorker  # noqa: E402

configure_logging()
logger = logging.getLogger("whatsapp_adapter")
_retry: RetryWorker | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _retry
    logger.info("whatsapp adapter starting up")
    _retry = RetryWorker(interval_seconds=30.0)
    await _retry.start()
    try:
        yield
    finally:
        logger.info("whatsapp adapter shutting down")
        if _retry is not None:
            await _retry.stop()
        await close_redis()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="KMan WhatsApp Adapter",
        description="The only service that talks to the WhatsApp workspace. Owns the webhook contract, retries, rate limiting, dedup.",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def correlation_middleware(request: Request, call_next: Callable[[Request], Awaitable[Any]]):
        cid = request.headers.get("X-Correlation-Id") or new_correlation_id()
        request.state.correlation_id = cid
        response = await call_next(request)
        response.headers["X-Correlation-Id"] = cid
        return response

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled exception: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": {
                "code": "internal_error",
                "message": str(exc),
                "correlation_id": getattr(request.state, "correlation_id", ""),
                "timestamp": utcnow().isoformat(),
            }},
        )

    app.include_router(health.router)
    app.include_router(deliver.router)
    app.include_router(status.router)
    app.include_router(webhooks.router)
    return app


app = create_app()
