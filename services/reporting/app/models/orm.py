"""SQLAlchemy ORM for the Reporting service."""

from __future__ import annotations

import enum
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Enum as SAEnum,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from shared.common.db import Base
from shared.common.time import utcnow


class ReportStatusEnum(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


def _new_id() -> str:
    from shared.common.ids import new_uuid
    return new_uuid()


class Report(Base):
    __tablename__ = "reporting_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    name: Mapped[str] = mapped_column(String(128), index=True)
    period: Mapped[str] = mapped_column(String(32), default="daily")
    kind: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(
        SAEnum(ReportStatusEnum, name="report_status_enum"),
        default=ReportStatusEnum.PENDING,
        index=True,
    )
    artifact_uri: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    started_at: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    finished_at: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String(32), default=lambda: utcnow().isoformat())
    updated_at: Mapped[str] = mapped_column(
        String(32), default=lambda: utcnow().isoformat(),
        onupdate=lambda: utcnow().isoformat(),
    )


class ReportSchedule(Base):
    __tablename__ = "reporting_schedules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    template: Mapped[str] = mapped_column(String(64), index=True)
    cron: Mapped[str] = mapped_column(String(64), default="0 8 * * *")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    recipients_json: Mapped[list] = mapped_column(JSON, default=list)
    last_run_at: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    next_run_at: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    created_at: Mapped[str] = mapped_column(String(32), default=lambda: utcnow().isoformat())
    updated_at: Mapped[str] = mapped_column(
        String(32), default=lambda: utcnow().isoformat(),
        onupdate=lambda: utcnow().isoformat(),
    )
