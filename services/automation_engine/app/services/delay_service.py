"""Delay service — detect delays and decide compensation."""

from __future__ import annotations

import logging
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.common.time import utcnow
from shared.contracts.automation_contract import (
    CompensationDecision,
    DelayCheckRequest,
    DelayCheckResult,
)
from shared.messaging.events import OrderDelayed
from shared.messaging.queue_contract import (
    QUEUE_DELAY_HANDLER,
    QueueMessage,
    enqueue_message,
)

from app.core.rules import decide_compensation, detect_delay, is_compensation_eligible
from app.models.orm import Compensation, Order, OrderStatusEnum

logger = logging.getLogger(__name__)


# Threshold above which we consider a delay actionable
DELAY_THRESHOLD_DAYS = 3


def _threshold_for(req: DelayCheckRequest) -> int:
    """Pick the threshold based on the request (configurable per carrier)."""
    carrier = (req.carrier or "").lower()
    if "express" in carrier:
        return 2
    if "economy" in carrier:
        return 5
    return DELAY_THRESHOLD_DAYS


def compute_delay_result(req: DelayCheckRequest) -> DelayCheckResult:
    """Pure function: compute the delay result from a request."""
    delay_days = detect_delay(req.dispatched_at, req.expected_delivery)
    threshold = _threshold_for(req)
    is_delayed = delay_days >= threshold
    eligible = is_compensation_eligible(delay_days, 5000, "standard") if is_delayed else False
    if not is_delayed:
        action = "none"
    elif delay_days >= 10:
        action = "refund"
    elif delay_days >= 5:
        action = "coupon"
    else:
        action = "monitor"
    return DelayCheckResult(
        order_id=req.order_id,
        delay_days=delay_days,
        is_delayed=is_delayed,
        threshold_days=threshold,
        compensation_eligible=eligible,
        suggested_action=action,
    )


async def run_delay_check(
    session: AsyncSession,
    req: DelayCheckRequest,
) -> tuple[DelayCheckResult, OrderDelayed]:
    """Run a delay check and emit the OrderDelayed event."""
    result = compute_delay_result(req)
    event = OrderDelayed(
        order_id=req.order_id,
        delay_days=result.delay_days,
        threshold_days=result.threshold_days,
        compensation_eligible=result.compensation_eligible,
    )
    # Update the order row if present
    stmt = select(Order).where(Order.order_id == req.order_id)
    order = (await session.execute(stmt)).scalar_one_or_none()
    if order is not None:
        order.dispatched_at = req.dispatched_at
        order.expected_delivery = req.expected_delivery
        if result.compensation_eligible:
            order.status = OrderStatusEnum.DELAYED
    await session.flush()
    return result, event


async def decide(
    session: AsyncSession,
    order_id: str,
    delay_days: int,
    order_value_cents: int,
    customer_tier: str = "standard",
) -> CompensationDecision:
    """Decide compensation and persist the decision."""
    decision = decide_compensation(order_id, delay_days, order_value_cents, customer_tier)
    row = Compensation(
        order_id=order_id,
        decision=decision.decision,
        amount_cents=decision.amount_cents,
        coupon_code=decision.coupon_code,
        rationale=decision.rationale,
        decided_at=utcnow().isoformat(),
    )
    session.add(row)
    await session.flush()
    return decision


async def enqueue_delay_check(order_id: str, dispatched_at: str, expected_delivery: str) -> str:
    msg = QueueMessage(
        queue=QUEUE_DELAY_HANDLER,
        payload={
            "order_id": order_id,
            "dispatched_at": dispatched_at,
            "expected_delivery": expected_delivery,
        },
    )
    return await enqueue_message(msg)
