"""SQLAlchemy ORM for the WhatsApp adapter."""

from __future__ import annotations

import enum
from typing import Optional

from sqlalchemy import (
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from shared.common.db import Base
from shared.common.time import utcnow


class DeliveryStatusEnum(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"
    REJECTED = "rejected"


def _new_id() -> str:
    from shared.common.ids import new_uuid
    return new_uuid()


class DeliveryAttempt(Base):
    __tablename__ = "whatsapp_delivery_attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    message_id: Mapped[str] = mapped_column(String(64), index=True)
    dedupe_id: Mapped[str] = mapped_column(String(64), index=True)
    account_id: Mapped[str] = mapped_column(String(64), index=True)
    channel: Mapped[str] = mapped_column(String(16), default="whatsapp")
    destination: Mapped[str] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(
        String(16),
        default=DeliveryStatusEnum.PENDING.value,
        index=True,
    )
    http_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_attempt_at: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    created_at: Mapped[str] = mapped_column(String(32), default=lambda: utcnow().isoformat())
    updated_at: Mapped[str] = mapped_column(
        String(32), default=lambda: utcnow().isoformat(),
        onupdate=lambda: utcnow().isoformat(),
    )

    __table_args__ = (
        Index("ix_wa_dedupe_status", "dedupe_id", "status"),
    )
