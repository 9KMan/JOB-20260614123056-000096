"""SQLAlchemy ORM models for the Automation Engine."""

from __future__ import annotations

import enum
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.common.db import Base
from shared.common.time import utcnow


class OrderStatusEnum(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    DELAYED = "delayed"
    RETURNED = "returned"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"


class DisputeVerdictEnum(str, enum.Enum):
    AUTO_RESOLVE = "auto_resolve"
    ESCALATE = "escalate"
    NEEDS_HUMAN = "needs_human"


def _new_id() -> str:
    from shared.common.ids import new_uuid
    return new_uuid()


class TimestampMixin:
    created_at: Mapped[str] = mapped_column(
        String(32), default=lambda: utcnow().isoformat(), nullable=False
    )
    updated_at: Mapped[str] = mapped_column(
        String(32),
        default=lambda: utcnow().isoformat(),
        onupdate=lambda: utcnow().isoformat(),
        nullable=False,
    )


class Order(TimestampMixin, Base):
    __tablename__ = "automation_orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    order_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    customer_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    customer_tier: Mapped[str] = mapped_column(String(16), default="standard")
    status: Mapped[str] = mapped_column(
        SAEnum(OrderStatusEnum, name="order_status_enum"),
        default=OrderStatusEnum.PENDING,
        index=True,
    )
    order_value_cents: Mapped[int] = mapped_column(Integer, default=0)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    carrier: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    tracking_number: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    destination_country: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    dispatched_at: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    expected_delivery: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    last_check_at: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)


class StockLevel(TimestampMixin, Base):
    __tablename__ = "automation_stock_levels"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    sku: Mapped[str] = mapped_column(String(64), index=True)
    warehouse: Mapped[str] = mapped_column(String(32), index=True)
    qty: Mapped[int] = mapped_column(Integer, default=0)
    threshold: Mapped[int] = mapped_column(Integer, default=5)
    last_checked_at: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    history_json: Mapped[list] = mapped_column(JSON, default=list)


class Compensation(TimestampMixin, Base):
    __tablename__ = "automation_compensations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    order_id: Mapped[str] = mapped_column(String(64), index=True)
    decision: Mapped[str] = mapped_column(String(32))
    amount_cents: Mapped[int] = mapped_column(Integer, default=0)
    coupon_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decided_at: Mapped[str] = mapped_column(
        String(32), default=lambda: utcnow().isoformat()
    )


class Dispute(TimestampMixin, Base):
    __tablename__ = "automation_disputes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    dispute_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    order_id: Mapped[str] = mapped_column(String(64), index=True)
    customer_message: Mapped[str] = mapped_column(Text, default="")
    verdict: Mapped[str] = mapped_column(
        SAEnum(DisputeVerdictEnum, name="dispute_verdict_enum"),
        default=DisputeVerdictEnum.NEEDS_HUMAN,
    )
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    suggested_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    triaged_at: Mapped[str] = mapped_column(
        String(32), default=lambda: utcnow().isoformat()
    )
