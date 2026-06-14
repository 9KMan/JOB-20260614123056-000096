"""Order endpoints."""

from fastapi import APIRouter, Depends, Query

from shared.common.db import session_scope
from shared.contracts.automation_contract import (
    OrderCheckRequest,
    OrderCheckResult,
)

from app.schemas.dto import ListResponse
from app.services import order_service

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


@router.post("/check", response_model=OrderCheckResult)
async def check_order(req: OrderCheckRequest) -> OrderCheckResult:
    """Run a single order check and persist the outcome."""
    async with session_scope() as session:
        result, _event = await order_service.run_order_check(session, req)
    return result


@router.get("", response_model=ListResponse[dict])
async def list_orders(limit: int = Query(50, ge=1, le=500)) -> ListResponse[dict]:
    """List recent orders (newest first)."""
    async with session_scope() as session:
        rows = await order_service.list_recent_orders(session, limit=limit)
    items = [
        {
            "id": r.id,
            "order_id": r.order_id,
            "status": r.status.value if hasattr(r.status, "value") else r.status,
            "customer_tier": r.customer_tier,
            "order_value_cents": r.order_value_cents,
            "carrier": r.carrier,
            "tracking_number": r.tracking_number,
            "dispatched_at": r.dispatched_at,
            "expected_delivery": r.expected_delivery,
            "last_check_at": r.last_check_at,
            "created_at": r.created_at,
        }
        for r in rows
    ]
    return ListResponse[dict](items=items, total=len(items))
