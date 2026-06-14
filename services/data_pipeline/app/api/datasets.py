"""Dataset endpoints — paginated reads from the e-commerce connector."""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Query

from app.services.ecommerce_connector import make_connector

router = APIRouter(prefix="/api/v1/datasets", tags=["datasets"])


@router.get("/orders")
async def list_orders(
    since: Optional[str] = None,
    until: Optional[str] = None,
    limit: int = Query(100, ge=1, le=2000),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    """Paginated read of orders."""
    connector = make_connector()
    try:
        items = []
        idx = 0
        async for o in connector.list_orders(since=since, until=until):
            if idx >= offset and len(items) < limit:
                items.append(o)
            idx += 1
            if idx > offset + limit:
                break
        return {"items": items, "total_seen": idx, "limit": limit, "offset": offset}
    finally:
        await connector.aclose()


@router.get("/inventory")
async def list_inventory(limit: int = Query(100, ge=1, le=2000)) -> Dict[str, Any]:
    """Snapshot of inventory across all warehouses."""
    connector = make_connector()
    try:
        items = []
        async for row in connector.list_inventory():
            items.append(row)
            if len(items) >= limit:
                break
        return {"items": items, "total": len(items)}
    finally:
        await connector.aclose()
