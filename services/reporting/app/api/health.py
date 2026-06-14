"""Health endpoint."""

from fastapi import APIRouter

from app.workers.scheduler import get_status

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "reporting", "version": "0.1.0"}


@router.get("/healthz/scheduler")
async def scheduler_health() -> dict:
    return get_status()
