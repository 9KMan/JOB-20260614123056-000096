"""Job runner — executes pending PipelineJobs with concurrency control."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional

from shared.common.time import utcnow

from app.services.analytics_service import AnalyticsService
from app.services.ecommerce_connector import make_connector
from app.services.job_service import (
    JobService,
    JobStatus,
    PipelineJob,
    get_job_service,
)

logger = logging.getLogger(__name__)


JobHandler = Callable[[PipelineJob], Awaitable[Dict[str, Any]]]


class JobRunner:
    """Polls the job registry, runs pending jobs with a concurrency cap."""

    def __init__(
        self,
        job_service: Optional[JobService] = None,
        concurrency: int = 2,
        poll_interval: float = 1.0,
    ) -> None:
        self.jobs = job_service or get_job_service()
        self.concurrency = concurrency
        self.poll_interval = poll_interval
        self._stop_event: Optional[asyncio.Event] = None
        self._runner_task: Optional[asyncio.Task] = None
        self._semaphore = asyncio.Semaphore(concurrency)
        self._handlers: Dict[str, JobHandler] = {
            "rfm": self._run_rfm,
            "funnel": self._run_funnel,
            "cohort": self._run_cohort,
            "anomalies": self._run_anomalies,
        }

    def register(self, kind: str, handler: JobHandler) -> None:
        """Register a custom job handler."""
        self._handlers[kind] = handler

    async def start(self) -> None:
        """Start the runner loop."""
        if self._runner_task is not None:
            return
        self._stop_event = asyncio.Event()
        self._runner_task = asyncio.create_task(self._loop(), name="data-pipeline-runner")

    async def stop(self) -> None:
        """Stop the runner loop."""
        if self._stop_event is not None:
            self._stop_event.set()
        if self._runner_task is not None:
            try:
                await asyncio.wait_for(self._runner_task, timeout=5.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                self._runner_task.cancel()
        self._runner_task = None
        self._stop_event = None

    async def _loop(self) -> None:
        assert self._stop_event is not None
        while not self._stop_event.is_set():
            try:
                pending = await self.jobs.list_jobs(limit=20, status_filter=JobStatus.PENDING)
                for job in pending:
                    if job.cancel_event.is_set():
                        await self.jobs.update(job.id, status=JobStatus.CANCELLED, finished_at=utcnow().isoformat())
                        continue
                    asyncio.create_task(self._execute(job))
            except Exception as exc:  # noqa: BLE001
                logger.exception("runner loop error: %s", exc)
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.poll_interval)
            except asyncio.TimeoutError:
                pass

    async def _execute(self, job: PipelineJob) -> None:
        async with self._semaphore:
            handler = self._handlers.get(job.kind)
            if handler is None:
                await self.jobs.update(
                    job.id, status=JobStatus.FAILED,
                    error=f"no handler for job kind: {job.kind}",
                    finished_at=utcnow().isoformat(),
                )
                return
            try:
                await self.jobs.update(
                    job.id, status=JobStatus.RUNNING,
                    started_at=utcnow().isoformat(), progress=0.05,
                )
                result = await handler(job)
                await self.jobs.update(
                    job.id, status=JobStatus.DONE, progress=1.0,
                    result_summary=result, finished_at=utcnow().isoformat(),
                )
                logger.info("job %s done (kind=%s)", job.id, job.kind)
            except asyncio.CancelledError:
                await self.jobs.update(
                    job.id, status=JobStatus.CANCELLED, finished_at=utcnow().isoformat(),
                )
                raise
            except Exception as exc:  # noqa: BLE001
                logger.exception("job %s failed: %s", job.id, exc)
                await self.jobs.update(
                    job.id, status=JobStatus.FAILED,
                    error=str(exc), finished_at=utcnow().isoformat(),
                )

    # ---- job handlers ----

    async def _run_rfm(self, job: PipelineJob) -> Dict[str, Any]:
        svc = AnalyticsService()
        try:
            result = await svc.compute_rfm(
                since=job.params.get("since"),
                until=job.params.get("until"),
            )
        finally:
            await svc.aclose()
        return {"customer_count": result["customer_count"], "segments": result["segment_counts"]}

    async def _run_funnel(self, job: PipelineJob) -> Dict[str, Any]:
        steps = job.params.get("steps") or ["paid", "shipped", "delivered"]
        svc = AnalyticsService()
        try:
            rows = await svc.compute_funnel(
                steps=steps,
                since=job.params.get("since"),
                until=job.params.get("until"),
            )
        finally:
            await svc.aclose()
        return {"steps": rows}

    async def _run_cohort(self, job: PipelineJob) -> Dict[str, Any]:
        svc = AnalyticsService()
        try:
            result = await svc.compute_cohort(
                cohort_period=job.params.get("cohort_period", "month"),
                since=job.params.get("since"),
                until=job.params.get("until"),
            )
        finally:
            await svc.aclose()
        return result

    async def _run_anomalies(self, job: PipelineJob) -> Dict[str, Any]:
        series = job.params.get("series") or []
        threshold = float(job.params.get("threshold_sigma", 3.0))
        svc = AnalyticsService()
        try:
            result = await svc.compute_anomalies(series, threshold)
        finally:
            await svc.aclose()
        return result
