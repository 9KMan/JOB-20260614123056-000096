"""FastAPI app for the Automation Engine."""

from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Any, Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Ensure /workspace root is on PYTHONPATH so `shared.*` imports resolve
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

from app.api import delays, disputes, health, orders, stock  # noqa: E402
from app.workers.scheduler import get_scheduler_status, start_scheduler, stop_scheduler  # noqa: E402

configure_logging()
logger = logging.getLogger("automation_engine")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start/stop background scheduler and Redis on app startup/shutdown."""
    logger.info("automation engine starting up")
    start_scheduler()
    try:
        yield
    finally:
        logger.info("automation engine shutting down")
        stop_scheduler()
        await close_redis()


def create_app() -> FastAPI:
    """FastAPI app factory."""
    settings = get_settings()
    app = FastAPI(
        title="KMan Automation Engine",
        description="Rule-based automations: order checks, delay handling, stock control, dispute pre-screen.",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Correlation ID middleware
    @app.middleware("http")
    async def correlation_middleware(request: Request, call_next: Callable[[Request], Awaitable[Any]]):
        cid = request.headers.get("X-Correlation-Id") or new_correlation_id()
        request.state.correlation_id = cid
        response = await call_next(request)
        response.headers["X-Correlation-Id"] = cid
        return response

    # Error handler — uniform JSON envelope
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled exception: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": str(exc),
                    "correlation_id": getattr(request.state, "correlation_id", ""),
                    "timestamp": utcnow().isoformat(),
                }
            },
        )

    # Routes
    app.include_router(health.router)
    app.include_router(orders.router)
    app.include_router(delays.router)
    app.include_router(stock.router)
    app.include_router(disputes.router)

    @app.get("/healthz/scheduler")
    async def scheduler_health() -> dict:
        """Scheduler status — last run time, next run time per job."""
        return get_scheduler_status()

    return app


app = create_app()
