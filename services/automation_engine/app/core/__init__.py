"""Core domain logic — rule engine."""

from .rules import (
    detect_delay,
    is_compensation_eligible,
    decide_compensation,
    is_low_stock,
    compute_stock_trend,
    pre_screen_dispute,
    days_between,
)

__all__ = [
    "detect_delay",
    "is_compensation_eligible",
    "decide_compensation",
    "is_low_stock",
    "compute_stock_trend",
    "pre_screen_dispute",
    "days_between",
]
