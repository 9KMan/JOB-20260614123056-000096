"""Jobs endpoints."""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.job_service import (
    JobService,
    JobStatus,
    get_job_service,
)
from app.workers.runner import JobRunner

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


class CreateJobDto(BaseModel):
    kind: str
    params: Dict[str, Any] = Field(default_factory=dict)


@router.post("")
async def create_job(dto: CreateJobDto) -> Dict[str, Any]:
    """Create a new pipeline job."""
    jobs: JobService = get_job_service()
    job = await jobs.create_job(dto.kind, dto.params)
    return job.to_dict()


@router.get("")
async def list_jobs(
    limit: int = Query(50, ge=1, le=500),
    status: Optional[str] = None,
) -> Dict[str, Any]:
    jobs: JobService = get_job_service()
    status_filter = JobStatus(status) if status else None
    rows = await jobs.list_jobs(limit=limit, status_filter=status_filter)
    return {"items": [j.to_dict() for j in rows], "total": len(rows)}


@router.get("/{job_id}")
async def get_job(job_id: str) -> Dict[str, Any]:
    jobs: JobService = get_job_service()
    job = await jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job.to_dict()


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str) -> Dict[str, Any]:
    jobs: JobService = get_job_service()
    job = await jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    job.cancel_event.set()
    return {"id": job_id, "cancel_requested": True}
