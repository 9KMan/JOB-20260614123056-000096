"""Job lifecycle manager for pipeline jobs."""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class PipelineJob:
    id: str
    kind: str
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    params: Dict[str, Any] = field(default_factory=dict)
    result_summary: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    created_at: str = field(default_factory=lambda: __import__("shared.common.time", fromlist=["utcnow"]).utcnow().isoformat())
    cancel_event: asyncio.Event = field(default_factory=asyncio.Event, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "status": self.status.value,
            "progress": self.progress,
            "params": self.params,
            "result_summary": self.result_summary,
            "error": self.error,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "created_at": self.created_at,
        }


class JobService:
    """In-memory job registry with a lock for thread-safety."""

    def __init__(self) -> None:
        self._jobs: Dict[str, PipelineJob] = {}
        self._lock = asyncio.Lock()

    async def create_job(self, kind: str, params: Dict[str, Any]) -> PipelineJob:
        async with self._lock:
            job = PipelineJob(id=str(uuid.uuid4()), kind=kind, params=params)
            self._jobs[job.id] = job
            return job

    async def get_job(self, job_id: str) -> Optional[PipelineJob]:
        return self._jobs.get(job_id)

    async def list_jobs(self, limit: int = 50, status_filter: Optional[JobStatus] = None) -> List[PipelineJob]:
        rows = list(self._jobs.values())
        if status_filter is not None:
            rows = [r for r in rows if r.status is status_filter]
        rows.sort(key=lambda r: r.created_at, reverse=True)
        return rows[:limit]

    async def update(self, job_id: str, **changes: Any) -> None:
        job = self._jobs.get(job_id)
        if job is None:
            return
        for k, v in changes.items():
            setattr(job, k, v)


_singleton: Optional[JobService] = None


def get_job_service() -> JobService:
    """Return the process-wide JobService singleton."""
    global _singleton
    if _singleton is None:
        _singleton = JobService()
    return _singleton
