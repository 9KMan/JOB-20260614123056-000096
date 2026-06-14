"""Pure rule functions for the Automation Engine.

All functions here are deterministic, side-effect-free, and unit-testable.
Business logic lives here, NOT in the API layer.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from shared.common.ids import new_uuid
from shared.common.time import utcnow
from shared.contracts.automation_contract import CompensationDecision


# ---- time helpers ----

def days_between(later: datetime, earlier: datetime) -> int:
    """Whole days between two datetimes (later - earlier, floored)."""
    delta = later - earlier
    return max(0, delta.days)


def _parse_iso(value: str) -> datetime:
    """Parse an ISO-8601 string, assuming UTC if naive."""
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


# ---- delay detection ----

def detect_delay(
    dispatched_at: str,
    expected_delivery: str,
    now: Optional[datetime] = None,
) -> int:
    """Return how many days the order is past its expected delivery."""
    expected = _parse_iso(expected_at(expected_delivery))
    reference = now or utcnow()
    if reference < expected:
        return 0
    return days_between(reference, expected)


def expected_at(value: str) -> str:
    """Pass-through helper for clarity at call sites."""
    return value


def is_compensation_eligible(
    delay_days: int,
    order_value_cents: int,
    customer_tier: str = "standard",
) -> bool:
    """Decide whether a delayed order is eligible for compensation.

    Rules:
      - <2 days delay: never eligible
      - 2-4 days: eligible if order_value_cents >= 2000
      - 5+ days: always eligible
      - "vip" tier: always eligible if delay >= 2 days
    """
    if delay_days < 2:
        return False
    if customer_tier == "vip":
        return True
    if delay_days >= 5:
        return True
    return order_value_cents >= 2000


def decide_compensation(
    order_id: str,
    delay_days: int,
    order_value_cents: int,
    customer_tier: str = "standard",
) -> CompensationDecision:
    """Decide what kind of compensation to offer for a delayed order."""
    if not is_compensation_eligible(delay_days, order_value_cents, customer_tier):
        return CompensationDecision(
            order_id=order_id,
            decision="reject",
            amount_cents=0,
            rationale=f"Delay of {delay_days} day(s) below compensation threshold.",
        )
    if delay_days >= 10:
        return CompensationDecision(
            order_id=order_id,
            decision="refund_full",
            amount_cents=order_value_cents,
            rationale=f"Delay of {delay_days} days — full refund warranted.",
        )
    if delay_days >= 5 or order_value_cents >= 10_000:
        return CompensationDecision(
            order_id=order_id,
            decision="refund_partial",
            amount_cents=min(order_value_cents, max(1000, order_value_cents // 5)),
            rationale=f"Delay of {delay_days} days — partial refund (~20%).",
        )
    # Mild delay, modest order: coupon is enough
    return CompensationDecision(
        order_id=order_id,
        decision="coupon",
        amount_cents=0,
        coupon_code=f"KMAN-D{delay_days}-{new_uuid()[:6].upper()}",
        rationale=f"Delay of {delay_days} days — 10% discount coupon offered.",
    )


# ---- stock control ----

def is_low_stock(current_qty: int, threshold: int) -> bool:
    """True if the SKU is at or below its reorder threshold."""
    return current_qty <= threshold


def compute_stock_trend(history: List[Dict[str, Any]]) -> str:
    """Return 'dropping', 'stable', or 'rising' based on a stock history.

    ``history`` is a list of {qty: int, ts: str} entries, ordered oldest
    to newest. We compare the mean of the first half vs the second half.
    """
    if len(history) < 2:
        return "stable"
    qtys = [int(h.get("qty", 0)) for h in history]
    midpoint = len(qtys) // 2
    first_mean = sum(qtys[:midpoint]) / max(1, midpoint)
    second_mean = sum(qtys[midpoint:]) / max(1, len(qtys) - midpoint)
    delta_pct = (second_mean - first_mean) / max(1.0, first_mean)
    if delta_pct <= -0.1:
        return "dropping"
    if delta_pct >= 0.1:
        return "rising"
    return "stable"


# ---- dispute pre-screen ----

_AGGRESSIVE_PATTERNS = [
    r"\b(scam|fraud|thieves|criminals|stealing)\b",
    r"\b(rage|furious|outrageous|disgusting)\b",
    r"!{2,}",
    r"\b(lawyer|sue|legal action|court|small claims)\b",
]
_REFUND_PATTERNS = [
    r"\brefund\b",
    r"\bmoney back\b",
    r"\breturn\b",
    r"\bchargeback\b",
]
_LEGAL_PATTERNS = [
    r"\b(lawyer|attorney|sue|court|legal action|small claims)\b",
]


def _has_any(text: str, patterns: List[str]) -> bool:
    lowered = text.lower()
    return any(re.search(p, lowered) for p in patterns)


def pre_screen_dispute(message: str) -> Dict[str, Any]:
    """Pre-screen a customer dispute message with deterministic flags.

    The AI judgment service does the nuanced tone/context analysis. This
    function flags obvious signals that the rule layer can act on
    immediately (legal threats, refund requests, etc.).
    """
    text = message or ""
    return {
        "aggressive_tone": _has_any(text, _AGGRESSIVE_PATTERNS),
        "refund_requested": _has_any(text, _REFUND_PATTERNS),
        "mentions_legal": _has_any(text, _LEGAL_PATTERNS),
        "word_count": len(text.split()),
        "all_caps_ratio": _all_caps_ratio(text),
    }


def _all_caps_ratio(text: str) -> float:
    """Ratio of uppercase letters to total letters, ignoring non-letters."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for c in letters if c.isupper()) / len(letters)
