"""Stock control endpoints."""

from fastapi import APIRouter

from shared.common.db import session_scope
from shared.contracts.automation_contract import (
    StockCheckRequest,
    StockCheckResult,
)

from app.schemas.dto import ListResponse
from app.services import stock_service

router = APIRouter(prefix="/api/v1/stock", tags=["stock"])


@router.post("/check", response_model=StockCheckResult)
async def check_stock(req: StockCheckRequest) -> StockCheckResult:
    """Check stock for a single SKU/warehouse."""
    async with session_scope() as session:
        result, _alert = await stock_service.run_stock_check(session, req)
    return result


@router.get("/alerts", response_model=ListResponse[dict])
async def list_alerts(limit: int = 50) -> ListResponse[dict]:
    """List SKUs at or below their reorder threshold."""
    async with session_scope() as session:
        rows = await stock_service.list_alerts(session, limit=limit)
    items = [
        {
            "id": r.id,
            "sku": r.sku,
            "warehouse": r.warehouse,
            "qty": r.qty,
            "threshold": r.threshold,
            "last_checked_at": r.last_checked_at,
        }
        for r in rows
    ]
    return ListResponse[dict](items=items, total=len(items))
