"""APScheduler-based report scheduler."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from shared.common.db import session_scope
from shared.common.time import utcnow
from shared.messaging.events import ReportReady
from shared.messaging.queue_contract import publish

from app.models.orm import ReportSchedule
from app.services import report_service, delivery_service

logger = logging.getLogger(__name__)


_scheduler: Optional[AsyncIOScheduler] = None


async def _run_scheduled(schedule_id: str) -> None:
    """Run a scheduled report end-to-end."""
    async with session_scope() as session:
        from sqlalchemy import select
        stmt = select(ReportSchedule).where(ReportSchedule.id == schedule_id)
        s = (await session.execute(stmt)).scalar_one_or_none()
        if s is None:
            return
        if not s.enabled:
            return
        template = s.template
        recipients = list(s.recipients_json or [])
    period = utcnow().strftime("%Y-%m-%d")
    try:
        report = await report_service.generate(template, period=period, output_format="markdown")
        body = (
            f"📊 *{template}* — {period}\n\n"
            f"Artifact: `{report.artifact_uri}`\n\n"
            f"See attached file for full content."
        )
        delivery = await delivery_service.deliver_report(
            report_name=template, period=period, body=body,
            recipients=recipients, artifact_uri=report.artifact_uri,
        )
        # Persist last_run_at
        async with session_scope() as session:
            from sqlalchemy import select
            stmt = select(ReportSchedule).where(ReportSchedule.id == schedule_id)
            s = (await session.execute(stmt)).scalar_one()
            s.last_run_at = utcnow().isoformat()
        # Publish event
        event = ReportReady(
            report_id=report.id, report_type=template, period=period,
            artifact_uri=report.artifact_uri or "",
        )
        try:
            await publish("kman:events:report_ready", event.to_dict())
        except Exception as exc:  # noqa: BLE001
            logger.warning("publish report_ready failed: %s", exc)
        logger.info("scheduled report %s done; delivery=%s", schedule_id, delivery)
    except Exception as exc:  # noqa: BLE001
        logger.exception("scheduled report %s failed: %s", schedule_id, exc)


async def _reload_schedules() -> None:
    """Load all enabled schedules from the DB and register cron jobs."""
    assert _scheduler is not None
    async with session_scope() as session:
        from sqlalchemy import select
        stmt = select(ReportSchedule).where(ReportSchedule.enabled == True)  # noqa: E712
        rows = list((await session.execute(stmt)).scalars().all())
    for s in rows:
        try:
            trigger = CronTrigger.from_crontab(s.cron)
        except Exception as exc:  # noqa: BLE001
            logger.warning("invalid cron for %s: %s (%s)", s.name, s.cron, exc)
            continue
        job_id = f"report-{s.id}"
        try:
            _scheduler.add_job(_run_scheduled, trigger, args=[s.id], id=job_id, replace_existing=True)
            logger.info("registered schedule %s (cron=%s)", s.name, s.cron)
        except Exception as exc:  # noqa: BLE001
            logger.warning("failed to register %s: %s", s.name, exc)


def start_scheduler() -> None:
    """Start the scheduler and load schedules from the DB."""
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = AsyncIOScheduler(timezone="UTC")
    _scheduler.start()
    asyncio.create_task(_reload_schedules())
    logger.info("reporting scheduler started")


def stop_scheduler() -> None:
    """Stop the scheduler."""
    global _scheduler
    if _scheduler is None:
        return
    _scheduler.shutdown(wait=False)
    _scheduler = None
    logger.info("reporting scheduler stopped")


def get_status() -> Dict[str, Any]:
    """Return scheduler status (jobs and next-run times)."""
    if _scheduler is None:
        return {"running": False}
    jobs = []
    for j in _scheduler.get_jobs():
        jobs.append({
            "id": j.id,
            "next_run_at": j.next_run_time.isoformat() if j.next_run_time else None,
        })
    return {"running": True, "jobs": jobs}
