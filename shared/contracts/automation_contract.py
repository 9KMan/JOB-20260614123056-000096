"""Automation contract — request/response types for the Automation Engine.

These are the wire types for the order check, delay handler, stock
monitor, and dispute triage workflows.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from shared.common.ids import new_uuid
from shared.common.time import utcnow


class OrderStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    DELAYED = "delayed"
    RETURNED = "returned"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"


class OrderCheckRequest(BaseModel):
    order_id: str
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    destination_country: Optional[str] = None


class OrderCheckResult(BaseModel):
    id: str = Field(default_factory=new_uuid)
    order_id: str
    status: OrderStatus
    needs_action: bool = False
    reasons: List[str] = Field(default_factory=list)
    checked_at: str = Field(default_factory=lambda: utcnow().isoformat())


class DelayCheckRequest(BaseModel):
    order_id: str
    dispatched_at: str
    expected_delivery: str
    carrier: Optional[str] = None


class DelayCheckResult(BaseModel):
    id: str = Field(default_factory=new_uuid)
    order_id: str
    delay_days: int
    is_delayed: bool
    threshold_days: int
    compensation_eligible: bool = False
    suggested_action: str = ""  # refund | coupon | monitor | none


class CompensationDecision(BaseModel):
    id: str = Field(default_factory=new_uuid)
    order_id: str
    decision: str  # refund_full | refund_partial | coupon | escalate | reject
    amount_cents: int = 0
    coupon_code: Optional[str] = None
    rationale: str = ""
    decided_at: str = Field(default_factory=lambda: utcnow().isoformat())


class StockCheckRequest(BaseModel):
    sku: str
    warehouse: Optional[str] = None
    threshold: int = 5


class StockCheckResult(BaseModel):
    id: str = Field(default_factory=new_uuid)
    sku: str
    warehouse: str
    current_qty: int
    threshold: int
    is_low: bool
    trend: str = "stable"  # dropping | stable | rising
    days_of_cover: float = 0.0


class DisputeVerdict(str, Enum):
    AUTO_RESOLVE = "auto_resolve"
    ESCALATE = "escalate"
    NEEDS_HUMAN = "needs_human"


class DisputeTriageRequest(BaseModel):
    dispute_id: str
    order_id: str
    customer_message: str
    order_value_cents: int = 0
    prior_disputes: int = 0


class DisputeTriageResult(BaseModel):
    id: str = Field(default_factory=new_uuid)
    dispute_id: str
    verdict: DisputeVerdict
    confidence: float = 0.0
    rationale: str = ""
    suggested_response: str = ""
    triaged_at: str = Field(default_factory=lambda: utcnow().isoformat())


__all__ = [
    "OrderStatus",
    "OrderCheckRequest",
    "OrderCheckResult",
    "DelayCheckRequest",
    "DelayCheckResult",
    "CompensationDecision",
    "StockCheckRequest",
    "StockCheckResult",
    "DisputeVerdict",
    "DisputeTriageRequest",
    "DisputeTriageResult",
]
