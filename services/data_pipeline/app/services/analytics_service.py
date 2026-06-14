"""Analytics service — orchestrates streaming reads + analyzer functions."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, List, Optional

from app.core.analyzers import (
    cohort_retention,
    detect_anomalies,
    funnel,
    moving_average,
    rfm_segment,
)
from app.services.ecommerce_connector import make_connector

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Read-through analytics: streams from the connector, runs analyzers."""

    def __init__(self) -> None:
        self.connector = make_connector()

    async def aclose(self) -> None:
        await self.connector.aclose()

    async def _orders_since(
        self, since: Optional[str], until: Optional[str]
    ) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        async for o in self.connector.list_orders(since=since, until=until):
            rows.append(o)
        return rows

    async def compute_rfm(
        self, since: Optional[str] = None, until: Optional[str] = None
    ) -> Dict[str, Any]:
        """Run RFM analysis on a date range."""
        orders = await self._orders_since(since, until)
        now = datetime.now(timezone.utc)
        segments = rfm_segment(orders, now)
        # Aggregate segment counts
        counts: Dict[str, int] = {}
        for v in segments.values():
            seg = v["segment"]
            counts[seg] = counts.get(seg, 0) + 1
        return {
            "as_of": now.isoformat(),
            "customer_count": len(segments),
            "segment_counts": counts,
            "segments": segments,
        }

    async def compute_funnel(
        self, steps: List[str], since: Optional[str] = None, until: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Compute a funnel on synthetic user events (orders in this build)."""
        # Map orders to step events: we treat every order with a "status" as a step
        # and use order_id prefix as the user. For real funnel, the connector should
        # expose user events directly.
        events: List[Dict[str, Any]] = []
        async for o in self.connector.list_orders(since=since, until=until):
            events.append({"user_id": o["order_id"], "step": o["status"]})
        return funnel(events, steps)

    async def compute_cohort(
        self, cohort_period: str = "month", since: Optional[str] = None, until: Optional[str] = None
    ) -> Dict[str, Any]:
        orders = await self._orders_since(since, until)
        cohorts = cohort_retention(orders, cohort_period=cohort_period)
        return {"cohort_period": cohort_period, "cohorts": cohorts}

    async def compute_anomalies(
        self, series: List[float], threshold_sigma: float = 3.0
    ) -> Dict[str, Any]:
        indices = detect_anomalies(series, threshold_sigma=threshold_sigma)
        ma = moving_average(series, window=max(2, min(7, len(series) // 4 or 2)))
        return {
            "anomaly_indices": indices,
            "moving_average": ma,
            "threshold_sigma": threshold_sigma,
        }
