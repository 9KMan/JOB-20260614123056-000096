"""Unit tests for the Automation Engine's rule engine.

Pure-function tests — no I/O, no async. The point of these is to lock
down the business rules so they don't drift as the code evolves.
"""
import os
import sys

# Put the automation_engine service on sys.path FIRST so its `app`
# package wins over the other services' `app` packages.
_HERE = os.path.dirname(os.path.abspath(__file__))
_SERVICE_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "services", "automation_engine"))
if _SERVICE_ROOT not in sys.path:
    sys.path.insert(0, _SERVICE_ROOT)

from datetime import datetime, timedelta, timezone

from app.core.rules import (
    detect_delay,
    is_compensation_eligible,
    decide_compensation,
    is_low_stock,
    compute_stock_trend,
    pre_screen_dispute,
    days_between,
)


NOW = datetime(2026, 6, 14, 12, 0, 0, tzinfo=timezone.utc)


def test_days_between_basic():
    assert days_between(NOW, NOW - timedelta(days=3)) == 3


def test_days_between_zero_when_earlier_is_later():
    assert days_between(NOW, NOW + timedelta(days=3)) == 0


def test_detect_delay_not_yet_due():
    expected = (NOW + timedelta(days=2)).isoformat()
    assert detect_delay(NOW.isoformat(), expected, now=NOW) == 0


def test_detect_delay_overdue():
    expected = (NOW - timedelta(days=5)).isoformat()
    assert detect_delay(NOW.isoformat(), expected, now=NOW) == 5


def test_is_compensation_eligible_below_threshold():
    assert is_compensation_eligible(delay_days=1, order_value_cents=50000) is False


def test_is_compensation_eligible_moderate_high_value():
    assert is_compensation_eligible(delay_days=3, order_value_cents=5000) is True


def test_is_compensation_eligible_moderate_low_value():
    assert is_compensation_eligible(delay_days=3, order_value_cents=1000) is False


def test_is_compensation_eligible_vip_tier():
    assert is_compensation_eligible(delay_days=2, order_value_cents=500, customer_tier="vip") is True


def test_is_compensation_eligible_severe_delay():
    assert is_compensation_eligible(delay_days=10, order_value_cents=100, customer_tier="standard") is True


def test_decide_compensation_reject_small_delay():
    d = decide_compensation("ORD-1", delay_days=1, order_value_cents=50000)
    assert d.decision == "reject"
    assert d.amount_cents == 0


def test_decide_compensation_coupon_for_mild_delay():
    # Mild delay (3 days) with order value above the 2000-cent threshold
    # — eligible for compensation, falls into the coupon branch
    d = decide_compensation("ORD-1", delay_days=3, order_value_cents=3000)
    assert d.decision == "coupon"
    assert d.coupon_code is not None


def test_decide_compensation_partial_refund():
    d = decide_compensation("ORD-1", delay_days=6, order_value_cents=10000)
    assert d.decision == "refund_partial"
    assert d.amount_cents > 0


def test_decide_compensation_full_refund():
    d = decide_compensation("ORD-1", delay_days=15, order_value_cents=10000)
    assert d.decision == "refund_full"
    assert d.amount_cents == 10000


def test_is_low_stock_at_threshold():
    assert is_low_stock(current_qty=5, threshold=5) is True


def test_is_low_stock_below():
    assert is_low_stock(current_qty=0, threshold=5) is True


def test_is_low_stock_above():
    assert is_low_stock(current_qty=10, threshold=5) is False


def test_compute_stock_trend_dropping():
    history = [{"qty": 100}, {"qty": 95}, {"qty": 90}, {"qty": 50}, {"qty": 30}, {"qty": 20}]
    assert compute_stock_trend(history) == "dropping"


def test_compute_stock_trend_rising():
    history = [{"qty": 10}, {"qty": 12}, {"qty": 20}, {"qty": 30}, {"qty": 50}, {"qty": 100}]
    assert compute_stock_trend(history) == "rising"


def test_compute_stock_trend_stable():
    history = [{"qty": 50}, {"qty": 51}, {"qty": 50}, {"qty": 49}, {"qty": 50}, {"qty": 51}]
    assert compute_stock_trend(history) == "stable"


def test_compute_stock_trend_too_few():
    assert compute_stock_trend([{"qty": 5}]) == "stable"


def test_pre_screen_dispute_flags_legal():
    flags = pre_screen_dispute("I will take you to court. This is a scam.")
    assert flags["mentions_legal"] is True
    assert flags["aggressive_tone"] is True


def test_pre_screen_dispute_flags_refund():
    flags = pre_screen_dispute("I want a refund, this product is broken.")
    assert flags["refund_requested"] is True
    assert flags["aggressive_tone"] is False
    assert flags["mentions_legal"] is False


def test_pre_screen_dispute_empty():
    flags = pre_screen_dispute("")
    assert flags["aggressive_tone"] is False
    assert flags["refund_requested"] is False
    assert flags["mentions_legal"] is False
    assert flags["word_count"] == 0


def test_pre_screen_dispute_all_caps():
    flags = pre_screen_dispute("WHERE IS MY ORDER")
    assert flags["all_caps_ratio"] > 0.5
