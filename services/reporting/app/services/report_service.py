"""Report service — orchestrates template + aggregation + render + persist."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from shared.common.time import utcnow

from app.core.aggregations import (
    summarize_compensations,
    summarize_disputes,
    summarize_orders,
    summarize_stock,
)
from app.core.renderers import render
from app.core.templating import TEMPLATES, render_template, list_templates
from app.models.orm import Report, ReportStatusEnum
from shared.common.db import session_scope

logger = logging.getLogger(__name__)


REPORT_OUTPUT_DIR = os.environ.get("KMAN_REPORT_OUTPUT_DIR", "/tmp/kman-reports")


async def generate(
    template_name: str,
    *,
    period: str = "current",
    output_format: str = "json",
    data: Optional[Dict[str, Any]] = None,
) -> Report:
    """Generate a report end-to-end and persist the Report row + artifact."""
    os.makedirs(REPORT_OUTPUT_DIR, exist_ok=True)
    info = TEMPLATES.get(template_name)
    if info is None:
        raise ValueError(f"unknown template: {template_name}")
    if output_format not in info.output_formats:
        output_format = info.output_formats[0]
    data = data or {}

    # Create a pending Report row
    async with session_scope() as session:
        report = Report(
            name=template_name,
            period=period,
            kind=template_name,
            status=ReportStatusEnum.RUNNING,
            started_at=utcnow().isoformat(),
        )
        session.add(report)
        await session.flush()
        report_id = report.id

    try:
        # Render body
        body_md = render_template(template_name, data, period=period)
        artifact_bytes = render(
            output_format,
            data,
            title=f"{template_name} ({period})",
            body=body_md,
        )
        ext = {"json": "json", "csv": "csv", "markdown": "md", "html": "html"}.get(output_format, "txt")
        filename = f"{template_name}_{period}_{report_id[:8]}.{ext}"
        path = os.path.join(REPORT_OUTPUT_DIR, filename)
        with open(path, "wb") as f:
            f.write(artifact_bytes)

        # Update Report row
        async with session_scope() as session:
            from sqlalchemy import select
            stmt = select(Report).where(Report.id == report_id)
            r = (await session.execute(stmt)).scalar_one()
            r.status = ReportStatusEnum.DONE
            r.finished_at = utcnow().isoformat()
            r.artifact_uri = path
            r.summary = {"format": output_format, "size_bytes": len(artifact_bytes), "period": period}

        return r
    except Exception as exc:  # noqa: BLE001
        logger.exception("report generation failed: %s", exc)
        async with session_scope() as session:
            from sqlalchemy import select
            stmt = select(Report).where(Report.id == report_id)
            r = (await session.execute(stmt)).scalar_one()
            r.status = ReportStatusEnum.FAILED
            r.finished_at = utcnow().isoformat()
            r.error = str(exc)
        raise


def list_template_infos() -> List[Dict[str, Any]]:
    """Return the template catalog."""
    return list_templates()


def summarize_for_template(template_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Run the appropriate aggregation function for the given template + data."""
    if template_name == "daily_order_summary" or template_name == "executive_dashboard":
        return summarize_orders(data.get("orders", []))
    if template_name == "weekly_compensation":
        return summarize_compensations(data.get("compensations", []))
    if template_name == "weekly_dispute_summary":
        return summarize_disputes(data.get("disputes", []))
    if template_name == "stock_coverage":
        return summarize_stock(data.get("stock", []))
    raise ValueError(f"unknown template: {template_name}")
