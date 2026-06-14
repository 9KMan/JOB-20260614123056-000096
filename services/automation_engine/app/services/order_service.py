"""Order service — orchestrates the order check workflow."""

from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.common.time import utcnow
from shared.contracts.automation_contract import (
    OrderCheckRequest,
    OrderCheckResult,
    OrderStatus,
)
from shared.messaging.events import OrderChecked
from shared.messaging.queue_contract import (
    QUEUE_ORDER_CHECKS,
    QueueMessage,
    enqueue_message,
)

from app.core.rules import is_low_stock  # noqa: F401  (re-exported)
from app.models.orm import Order, OrderStatusEnum

logger = logging.getLogger(__name__)


# Configurable SLA threshold (days) before a shipped order is considered "delayed"
SHIPPED_DELIVERY_THRESHOLD_DAYS = 7


def derive_status(req: OrderCheckRequest) -> tuple[OrderStatus, List[str], bool]:
    """Pure function: derive status from request fields.

    Returns (status, reasons, needs_action). Used by the order check endpoint
    and by the scheduler.
    """
    reasons: List[str] = []
    needs_action = False
    if req.tracking_number and not req.carrier:
        reasons.append("tracking_number_without_carrier")
        needs_action = True
    if req.destination_country and req.destination_country.upper() in {"RU", "BR"}:
        reasons.append("high_risk_destination")
    return OrderStatus.PROCESSING, reasons, needs_action


async def run_order_check(
    session: AsyncSession,
    req: OrderCheckRequest,
) -> tuple[OrderCheckResult, OrderChecked]:
    """Run a single order check and persist the outcome.

    Looks up the order by ``req.order_id`` (creates a stub if not found —
    real systems would 404 here). Updates the last_check_at timestamp and
    returns the derived OrderCheckResult and emitted event.
    """
    status, reasons, needs_action = derive_status(req)
    stmt = select(Order).where(Order.order_id == req.order_id)
    order = (await session.execute(stmt)).scalar_one_or_none()
    if order is not None:
        order.last_check_at = utcnow().isoformat()
        order.carrier = req.carrier or order.carrier
        order.tracking_number = req.tracking_number or order.tracking_number
        order.destination_country = req.destination_country or order.destination_country
    else:
        order = Order(
            order_id=req.order_id,
            carrier=req.carrier,
            tracking_number=req.tracking_number,
            destination_country=req.destination_country,
            status=OrderStatusEnum.PROCESSING,
        )
        session.add(order)
    await session.flush()
    result = OrderCheckResult(
        order_id=req.order_id,
        status=status,
        needs_action=needs_action,
        reasons=reasons,
    )
    event = OrderChecked(
        order_id=req.order_id,
        status=status.value,
        needs_action=needs_action,
        reason="; ".join(reasons) if reasons else "ok",
    )
    logger.info("order.checked %s -> %s needs_action=%s", req.order_id, status.value, needs_action)
    return result, event


async def enqueue_order_check(order_id: str) -> str:
    """Enqueue an order check on the worker queue."""
    msg = QueueMessage(
        queue=QUEUE_ORDER_CHECKS,
        payload={"order_id": order_id},
    )
    return await enqueue_message(msg)


async def list_recent_orders(session: AsyncSession, limit: int = 50) -> List[Order]:
    stmt = select(Order).order_by(Order.created_at.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())
