"""Delay detection + compensation endpoints."""

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from shared.common.db import session_scope
from shared.contracts.automation_contract import (
    CompensationDecision,
    DelayCheckRequest,
    DelayCheckResult,
)

from app.services import delay_service

router = APIRouter(prefix="/api/v1/delays", tags=["delays"])


class DecideRequest(BaseModel):
    order_id: str
    delay_days: int = Field(ge=0)
    order_value_cents: int = Field(ge=0)
    customer_tier: str = "standard"


@router.post("/detect", response_model=DelayCheckResult)
async def detect_delay(req: DelayCheckRequest) -> DelayCheckResult:
    """Detect whether an order is past its expected delivery SLA."""
    async with session_scope() as session:
        result, _event = await delay_service.run_delay_check(session, req)
    return result


@router.post("/decide", response_model=CompensationDecision)
async def decide_compensation(req: DecideRequest) -> CompensationDecision:
    """Decide compensation (refund/coupon/escalate/reject) for a delayed order."""
    async with session_scope() as session:
        decision = await delay_service.decide(
            session,
            order_id=req.order_id,
            delay_days=req.delay_days,
            order_value_cents=req.order_value_cents,
            customer_tier=req.customer_tier,
        )
    return decision
