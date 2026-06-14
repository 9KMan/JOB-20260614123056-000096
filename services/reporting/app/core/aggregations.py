"""Report-specific aggregation functions.

Pure functions over dict lists. In production these would read from the
e-commerce connector or the automation engine's database; for the
template-driven reports here, the input is supplied by the caller.
"""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Dict, List


def _coerce_dt(s: Any) -> datetime:
    if isinstance(s, datetime):
        return s
    if isinstance(s, str):
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    raise TypeError(f"cannot parse datetime from {type(s).__name__}")


def summarize_orders(
    orders: List[Dict[str, Any]],
    since: str = "",
    until: str = "",
) -> Dict[str, Any]:
    """Summarize a list of orders."""
    filtered = []
    for o in orders:
        ts = o.get("ts") or o.get("dispatched_at") or o.get("created_at") or ""
        if since and ts < since:
            continue
        if until and ts > until:
            continue
        filtered.append(o)
    by_status: Counter = Counter()
    by_sku_value: Dict[str, int] = defaultdict(int)
    by_sku_count: Counter = Counter()
    total_value_cents = 0
    for o in filtered:
        by_status[str(o.get("status", "unknown"))] += 1
        sku = str(o.get("sku", ""))
        by_sku_count[sku] += 1
        by_sku_value[sku] += int(o.get("value_cents", 0) or 0)
        total_value_cents += int(o.get("value_cents", 0) or 0)
    top_skus = by_sku_count.most_common(10)
    return {
        "order_count": len(filtered),
        "total_value_cents": total_value_cents,
        "by_status": dict(by_status),
        "top_skus": [{"sku": s, "count": c} for s, c in top_skus],
    }


def summarize_compensations(
    compensations: List[Dict[str, Any]],
    since: str = "",
    until: str = "",
) -> Dict[str, Any]:
    """Summarize a list of compensations."""
    by_decision: Counter = Counter()
    total_cents = 0
    by_decision_amount: Dict[str, int] = defaultdict(int)
    for c in compensations:
        ts = c.get("decided_at") or ""
        if since and ts < since:
            continue
        if until and ts > until:
            continue
        decision = str(c.get("decision", "unknown"))
        by_decision[decision] += 1
        amount = int(c.get("amount_cents", 0) or 0)
        total_cents += amount
        by_decision_amount[decision] += amount
    return {
        "count": sum(by_decision.values()),
        "total_amount_cents": total_cents,
        "by_decision": dict(by_decision),
        "by_decision_amount_cents": dict(by_decision_amount),
    }


def summarize_disputes(
    disputes: List[Dict[str, Any]],
    since: str = "",
    until: str = "",
) -> Dict[str, Any]:
    """Summarize a list of disputes."""
    by_verdict: Counter = Counter()
    confidences: List[float] = []
    for d in disputes:
        ts = d.get("triaged_at") or ""
        if since and ts < since:
            continue
        if until and ts > until:
            continue
        by_verdict[str(d.get("verdict", "unknown"))] += 1
        c = d.get("confidence", 0.0)
        try:
            confidences.append(float(c))
        except (TypeError, ValueError):
            pass
    avg_confidence = round(statistics.mean(confidences), 3) if confidences else 0.0
    return {
        "count": sum(by_verdict.values()),
        "by_verdict": dict(by_verdict),
        "avg_confidence": avg_confidence,
    }


def summarize_stock(stock_levels: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Summarize stock levels — low-stock count, total SKUs, total qty."""
    low = [s for s in stock_levels if int(s.get("qty", 0) or 0) <= int(s.get("threshold", 0) or 0)]
    total_qty = sum(int(s.get("qty", 0) or 0) for s in stock_levels)
    return {
        "total_skus": len(stock_levels),
        "low_stock_count": len(low),
        "low_stock_skus": [s.get("sku") for s in low[:20]],
        "total_qty": total_qty,
    }
