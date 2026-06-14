"""APScheduler-based background jobs for the Automation Engine.

Periodically enqueues:
- Order checks (every 5 minutes)
- Delay detections (every 15 minutes)
- Stock checks (every 30 minutes)
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from shared.common.time import utcnow

from app.services import delay_service, order_service, stock_service

logger = logging.getLogger(__name__)


# Sample order IDs used for scheduled checks in dev/test.
# In production, these come from a query against the e-commerce platform.
SAMPLE_SHIPPED_ORDERS: List[str] = [
    "ORD-1001", "ORD-1002", "ORD-1003",
]
SAMPLE_SKUS: List[str] = [
    "SKU-A1", "SKU-B2", "SKU-C3", "SKU-D4",
]


_scheduler: Optional[AsyncIOScheduler] = None


async def _scan_orders() -> None:
    """Enqueue order checks for all shipped orders needing verification."""
    for order_id in SAMPLE_SHIPPED_ORDERS:
        try:
            await order_service.enqueue_order_check(order_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("enqueue order check failed for %s: %s", order_id, exc)


async def _scan_delays() -> None:
    """Enqueue delay detections for orders past their expected delivery."""
    now = utcnow()
    for order_id in SAMPLE_SHIPPED_ORDERS:
        # For dev, assume each order was expected 4 days ago
        from datetime import timedelta
        expected = (now - timedelta(days=4)).isoformat()
        dispatched = (now - timedelta(days=10)).isoformat()
        try:
            await delay_service.enqueue_delay_check(order_id, dispatched, expected)
        except Exception as exc:  # noqa: BLE001
            logger.warning("enqueue delay check failed for %s: %s", order_id, exc)


async def _scan_stock() -> None:
    """Enqueue stock checks for the active SKU set."""
    for sku in SAMPLE_SKUS:
        try:
            await stock_service.enqueue_stock_check(sku)
        except Exception as exc:  # noqa: BLE001
            logger.warning("enqueue stock check failed for %s: %s", sku, exc)


def start_scheduler() -> None:
    """Start the background scheduler. Idempotent."""
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = AsyncIOScheduler(timezone="UTC")
    _scheduler.add_job(_scan_orders, IntervalTrigger(minutes=5), id="scan_orders", replace_existing=True)
    _scheduler.add_job(_scan_delays, IntervalTrigger(minutes=15), id="scan_delays", replace_existing=True)
    _scheduler.add_job(_scan_stock, IntervalTrigger(minutes=30), id="scan_stock", replace_existing=True)
    _scheduler.start()
    logger.info("automation engine scheduler started")


def stop_scheduler() -> None:
    """Stop the background scheduler. Idempotent."""
    global _scheduler
    if _scheduler is None:
        return
    _scheduler.shutdown(wait=False)
    _scheduler = None
    logger.info("automation engine scheduler stopped")


def get_scheduler_status() -> dict:
    """Return scheduler status (for /healthz/scheduler)."""
    if _scheduler is None:
        return {"running": False}
    jobs = []
    for job in _scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "next_run_at": job.next_run_time.isoformat() if job.next_run_time else None,
        })
    return {"running": True, "jobs": jobs}
