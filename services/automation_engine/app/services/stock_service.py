"""Stock service — stock checks and low-stock alerts."""

from __future__ import annotations

import logging
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.common.time import utcnow
from shared.contracts.automation_contract import (
    StockCheckRequest,
    StockCheckResult,
)
from shared.messaging.events import StockAlert
from shared.messaging.queue_contract import (
    QUEUE_STOCK_MONITOR,
    QueueMessage,
    enqueue_message,
)

from app.core.rules import compute_stock_trend, is_low_stock
from app.models.orm import StockLevel

logger = logging.getLogger(__name__)


async def run_stock_check(
    session: AsyncSession,
    req: StockCheckRequest,
) -> tuple[StockCheckResult, StockAlert | None]:
    """Run a single SKU stock check."""
    warehouse = req.warehouse or "default"
    stmt = select(StockLevel).where(
        StockLevel.sku == req.sku, StockLevel.warehouse == warehouse
    )
    level = (await session.execute(stmt)).scalar_one_or_none()
    if level is None:
        # Stub: assume a 0 reading on a brand-new SKU
        level = StockLevel(
            sku=req.sku,
            warehouse=warehouse,
            qty=0,
            threshold=req.threshold,
            history_json=[],
        )
        session.add(level)
        await session.flush()
    history = level.history_json or []
    history.append({"qty": level.qty, "ts": utcnow().isoformat()})
    level.history_json = history[-50:]  # keep last 50
    level.last_checked_at = utcnow().isoformat()
    trend = compute_stock_trend(history)
    is_low = is_low_stock(level.qty, level.threshold)
    days_of_cover = float(level.qty) / max(1, level.threshold)
    result = StockCheckResult(
        sku=req.sku,
        warehouse=warehouse,
        current_qty=level.qty,
        threshold=level.threshold,
        is_low=is_low,
        trend=trend,
        days_of_cover=round(days_of_cover, 2),
    )
    alert = None
    if is_low:
        alert = StockAlert(
            sku=req.sku,
            warehouse=warehouse,
            current_qty=level.qty,
            threshold=level.threshold,
            trend=trend,
        )
    return result, alert


async def list_alerts(session: AsyncSession, limit: int = 50) -> List[StockLevel]:
    stmt = (
        select(StockLevel)
        .where(StockLevel.qty <= StockLevel.threshold)
        .order_by(StockLevel.qty.asc())
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().all())


async def enqueue_stock_check(sku: str, warehouse: str | None = None) -> str:
    msg = QueueMessage(
        queue=QUEUE_STOCK_MONITOR,
        payload={"sku": sku, "warehouse": warehouse},
    )
    return await enqueue_message(msg)
