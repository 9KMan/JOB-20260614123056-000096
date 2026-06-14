"""Reports endpoints."""

import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select

from shared.common.db import session_scope
from shared.common.time import utcnow

from app.models.orm import Report, ReportSchedule, ReportStatusEnum
from app.services import report_service, template_service, delivery_service
from app.workers.scheduler import _reload_schedules

router = APIRouter(prefix="/api/v1", tags=["reports"])


class GenerateDto(BaseModel):
    template: str
    period: str = Field(default_factory=lambda: utcnow().strftime("%Y-%m-%d"))
    output_format: str = "json"
    data: Dict[str, Any] = Field(default_factory=dict)
    deliver: bool = False
    recipients: list[str] = Field(default_factory=list)


class ScheduleDto(BaseModel):
    name: str
    template: str
    cron: str = "0 8 * * *"
    enabled: bool = True
    recipients: list[str] = Field(default_factory=list)


@router.get("/templates")
async def list_templates() -> list[dict]:
    return template_service.list_all()


@router.post("/reports")
async def generate_report(dto: GenerateDto) -> Dict[str, Any]:
    """Generate a report on demand."""
    data = report_service.summarize_for_template(dto.template, dto.data) if dto.data else {}
    report = await report_service.generate(
        dto.template, period=dto.period, output_format=dto.output_format, data=data or dto.data
    )
    delivered_info = None
    if dto.deliver and dto.recipients:
        body = f"📊 *{dto.template}* — {dto.period}\nArtifact: `{report.artifact_uri}`"
        delivered_info = await delivery_service.deliver_report(
            report_name=dto.template, period=dto.period, body=body,
            recipients=dto.recipients, artifact_uri=report.artifact_uri,
        )
    return {
        "id": report.id,
        "name": report.name,
        "period": report.period,
        "status": report.status.value if hasattr(report.status, "value") else report.status,
        "artifact_uri": report.artifact_uri,
        "delivered": delivered_info,
    }


@router.get("/reports")
async def list_reports(limit: int = Query(50, ge=1, le=500)) -> Dict[str, Any]:
    async with session_scope() as session:
        stmt = select(Report).order_by(Report.created_at.desc()).limit(limit)
        rows = list((await session.execute(stmt)).scalars().all())
    return {
        "items": [
            {
                "id": r.id, "name": r.name, "period": r.period, "kind": r.kind,
                "status": r.status.value if hasattr(r.status, "value") else r.status,
                "artifact_uri": r.artifact_uri, "summary": r.summary,
                "started_at": r.started_at, "finished_at": r.finished_at,
                "error": r.error, "created_at": r.created_at,
            }
            for r in rows
        ],
        "total": len(rows),
    }


@router.get("/reports/{report_id}")
async def get_report(report_id: str) -> Dict[str, Any]:
    async with session_scope() as session:
        stmt = select(Report).where(Report.id == report_id)
        r = (await session.execute(stmt)).scalar_one_or_none()
    if r is None:
        raise HTTPException(status_code=404, detail="report not found")
    return {
        "id": r.id, "name": r.name, "period": r.period, "kind": r.kind,
        "status": r.status.value if hasattr(r.status, "value") else r.status,
        "artifact_uri": r.artifact_uri, "summary": r.summary,
        "started_at": r.started_at, "finished_at": r.finished_at,
        "error": r.error, "created_at": r.created_at,
    }


@router.get("/reports/{report_id}/download")
async def download_report(report_id: str) -> Response:
    async with session_scope() as session:
        stmt = select(Report).where(Report.id == report_id)
        r = (await session.execute(stmt)).scalar_one_or_none()
    if r is None:
        raise HTTPException(status_code=404, detail="report not found")
    if not r.artifact_uri or not os.path.exists(r.artifact_uri):
        raise HTTPException(status_code=410, detail="artifact missing")
    with open(r.artifact_uri, "rb") as f:
        data = f.read()
    fmt = (r.summary or {}).get("format", "json")
    media_type = {"json": "application/json", "markdown": "text/markdown", "html": "text/html", "csv": "text/csv"}.get(fmt, "application/octet-stream")
    return Response(content=data, media_type=media_type)


@router.get("/schedules")
async def list_schedules() -> Dict[str, Any]:
    async with session_scope() as session:
        stmt = select(ReportSchedule).order_by(ReportSchedule.created_at.desc())
        rows = list((await session.execute(stmt)).scalars().all())
    return {
        "items": [
            {
                "id": s.id, "name": s.name, "template": s.template, "cron": s.cron,
                "enabled": s.enabled, "recipients": s.recipients_json,
                "last_run_at": s.last_run_at, "next_run_at": s.next_run_at,
            }
            for s in rows
        ],
        "total": len(rows),
    }


@router.post("/schedules")
async def create_schedule(dto: ScheduleDto) -> Dict[str, Any]:
    async with session_scope() as session:
        s = ReportSchedule(
            name=dto.name, template=dto.template, cron=dto.cron,
            enabled=dto.enabled, recipients_json=dto.recipients,
        )
        session.add(s)
        await session.flush()
        out = {
            "id": s.id, "name": s.name, "template": s.template, "cron": s.cron,
            "enabled": s.enabled, "recipients": s.recipients_json,
        }
    # Reload schedules so the new one is registered with APScheduler
    try:
        await _reload_schedules()
    except Exception:  # noqa: BLE001
        pass
    return out


@router.put("/schedules/{schedule_id}")
async def update_schedule(schedule_id: str, dto: ScheduleDto) -> Dict[str, Any]:
    async with session_scope() as session:
        stmt = select(ReportSchedule).where(ReportSchedule.id == schedule_id)
        s = (await session.execute(stmt)).scalar_one_or_none()
        if s is None:
            raise HTTPException(status_code=404, detail="schedule not found")
        s.name = dto.name
        s.template = dto.template
        s.cron = dto.cron
        s.enabled = dto.enabled
        s.recipients_json = dto.recipients
        out = {
            "id": s.id, "name": s.name, "template": s.template, "cron": s.cron,
            "enabled": s.enabled, "recipients": s.recipients_json,
        }
    try:
        await _reload_schedules()
    except Exception:  # noqa: BLE001
        pass
    return out


@router.delete("/schedules/{schedule_id}")
async def delete_schedule(schedule_id: str) -> Dict[str, Any]:
    async with session_scope() as session:
        stmt = select(ReportSchedule).where(ReportSchedule.id == schedule_id)
        s = (await session.execute(stmt)).scalar_one_or_none()
        if s is None:
            raise HTTPException(status_code=404, detail="schedule not found")
        await session.delete(s)
    return {"deleted": schedule_id}
