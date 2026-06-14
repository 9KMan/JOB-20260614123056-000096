"""Pure analytics functions — RFM, funnel, cohort, anomalies, MA.

All functions here are deterministic and side-effect-free.
"""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Tuple


# ---- helpers ----

def _parse_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    s = str(value)
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


# ---- RFM segmentation ----

def rfm_segment(
    orders: List[Dict[str, Any]],
    now: datetime,
) -> Dict[str, Dict[str, Any]]:
    """Compute RFM segments per customer.

    ``orders`` is a list of {customer_id, order_id, ts, value_cents}.
    Returns {customer_id: {recency_days, frequency, monetary_cents, segment}}.
    """
    if not orders:
        return {}
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for o in orders:
        cid = str(o.get("customer_id", ""))
        if cid:
            grouped[cid].append(o)
    out: Dict[str, Dict[str, Any]] = {}
    for cid, items in grouped.items():
        items.sort(key=lambda x: _parse_dt(x.get("ts", now.isoformat())))
        last_ts = _parse_dt(items[-1].get("ts", now.isoformat()))
        recency_days = max(0, (now - last_ts).days)
        frequency = len(items)
        monetary_cents = sum(int(i.get("value_cents", 0) or 0) for i in items)
        segment = _classify_segment(recency_days, frequency, monetary_cents)
        out[cid] = {
            "recency_days": recency_days,
            "frequency": frequency,
            "monetary_cents": monetary_cents,
            "segment": segment,
        }
    return out


def _classify_segment(recency: int, frequency: int, monetary_cents: int) -> str:
    """Assign an RFM segment label."""
    high_value = monetary_cents >= 10_000
    if recency <= 30 and frequency >= 5 and high_value:
        return "champions"
    if recency <= 60 and frequency >= 3:
        return "loyal"
    if 30 < recency <= 120 and frequency >= 1:
        return "at_risk"
    if recency > 120:
        return "hibernating"
    if recency <= 30 and frequency <= 2:
        return "new"
    return "regular"


# ---- funnel analysis ----

def funnel(events: List[Dict[str, Any]], steps: List[str]) -> List[Dict[str, Any]]:
    """Compute a funnel from a list of events.

    ``events`` items are {user_id, step}. Returns one entry per step with
    count and conversion rate from the previous step.
    """
    users_by_step: Dict[str, set] = {s: set() for s in steps}
    for e in events:
        s = e.get("step")
        uid = e.get("user_id")
        if s in users_by_step and uid is not None:
            users_by_step[s].add(uid)
    rows: List[Dict[str, Any]] = []
    previous = None
    for s in steps:
        count = len(users_by_step[s])
        if previous is None or previous == 0:
            conversion = 1.0
        else:
            conversion = count / previous
        rows.append({"step": s, "count": count, "conversion_rate": round(conversion, 4)})
        previous = count
    return rows


# ---- cohort retention ----

def cohort_retention(
    orders: List[Dict[str, Any]],
    cohort_period: str = "month",
) -> Dict[str, Dict[str, float]]:
    """Compute cohort retention.

    ``orders`` items are {customer_id, ts, value_cents}. ``cohort_period``
    is "day" | "week" | "month". Returns
    {cohort_label: {period_offset: retention_rate}}.
    """
    if not orders:
        return {}
    bucket_size = {"day": 1, "week": 7, "month": 30}.get(cohort_period, 30)
    cohorts: Dict[str, set] = defaultdict(set)
    activity: Dict[Tuple[str, int], set] = defaultdict(set)
    for o in orders:
        cid = str(o.get("customer_id", ""))
        if not cid:
            continue
        ts = _parse_dt(o.get("ts"))
        cohort = _cohort_label(ts, bucket_size)
        offset = max(0, (ts - _cohort_start(ts, bucket_size)).days // bucket_size)
        cohorts[cohort].add(cid)
        activity[(cohort, offset)].add(cid)
    out: Dict[str, Dict[str, float]] = {}
    for cohort, members in cohorts.items():
        n = len(members)
        if n == 0:
            continue
        series: Dict[str, float] = {}
        for offset in sorted({k[1] for k in activity if k[0] == cohort}):
            retained = len(activity[(cohort, offset)])
            series[f"period_{offset}"] = round(retained / n, 4)
        out[cohort] = series
    return out


def _cohort_start(ts: datetime, bucket_size: int) -> datetime:
    return datetime(ts.year, ts.month, ts.day, tzinfo=timezone.utc)


def _cohort_label(ts: datetime, bucket_size: int) -> str:
    if bucket_size == 1:
        return ts.strftime("%Y-%m-%d")
    if bucket_size == 7:
        # ISO week
        year, week, _ = ts.isocalendar()
        return f"{year}-W{week:02d}"
    return ts.strftime("%Y-%m")


# ---- moving average & anomaly detection ----

def moving_average(values: List[float], window: int) -> List[float]:
    """Simple moving average. Returns one value per position from `window-1`."""
    if window <= 0:
        raise ValueError("window must be positive")
    if not values:
        return []
    out: List[float] = []
    for i in range(len(values)):
        if i + 1 < window:
            out.append(float("nan"))
            continue
        seg = values[i + 1 - window:i + 1]
        out.append(sum(seg) / window)
    return out


def detect_anomalies(values: List[float], threshold_sigma: float = 3.0) -> List[int]:
    """Return indices of values that are ``threshold_sigma`` from the mean."""
    if len(values) < 2:
        return []
    mean = statistics.mean(values)
    sd = statistics.pstdev(values) or 1e-9
    return [i for i, v in enumerate(values) if abs(v - mean) >= threshold_sigma * sd]
