"""Health endpoint."""

from fastapi import APIRouter

from app.schemas.dto import HealthDto

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthDto)
async def health() -> HealthDto:
    """Liveness/readiness probe."""
    return HealthDto()
