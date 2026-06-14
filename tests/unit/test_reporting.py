"""Tests for the Reporting aggregations and templating."""
import os
import sys

# Put the reporting service on sys.path FIRST.
_HERE = os.path.dirname(os.path.abspath(__file__))
_SERVICE_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "services", "reporting"))
if _SERVICE_ROOT not in sys.path:
    sys.path.insert(0, _SERVICE_ROOT)

from app.core.aggregations import (
    summarize_orders,
    summarize_compensations,
    summarize_disputes,
    summarize_stock,
)
from app.core.templating import render_template, list_templates


def test_summarize_orders_basic():
    orders = [
        {"order_id": "O1", "status": "shipped", "sku": "A", "value_cents": 1000, "ts": "2026-06-14"},
        {"order_id": "O2", "status": "delivered", "sku": "A", "value_cents": 2000, "ts": "2026-06-14"},
        {"order_id": "O3", "status": "shipped", "sku": "B", "value_cents": 500, "ts": "2026-06-14"},
    ]
    out = summarize_orders(orders)
    assert out["order_count"] == 3
    assert out["total_value_cents"] == 3500
    assert out["by_status"]["shipped"] == 2
    assert out["by_status"]["delivered"] == 1
    assert out["top_skus"][0]["sku"] == "A"
    assert out["top_skus"][0]["count"] == 2


def test_summarize_orders_filters_by_date():
    orders = [
        {"order_id": "O1", "status": "shipped", "sku": "A", "value_cents": 1000, "ts": "2026-06-13"},
        {"order_id": "O2", "status": "shipped", "sku": "A", "value_cents": 2000, "ts": "2026-06-14"},
    ]
    out = summarize_orders(orders, since="2026-06-14", until="2026-06-15")
    assert out["order_count"] == 1
    assert out["total_value_cents"] == 2000


def test_summarize_compensations():
    comps = [
        {"decision": "refund_partial", "amount_cents": 1000, "decided_at": "2026-06-14"},
        {"decision": "refund_partial", "amount_cents": 500, "decided_at": "2026-06-14"},
        {"decision": "coupon", "amount_cents": 0, "decided_at": "2026-06-14"},
    ]
    out = summarize_compensations(comps)
    assert out["count"] == 3
    assert out["total_amount_cents"] == 1500
    assert out["by_decision"]["refund_partial"] == 2


def test_summarize_disputes():
    disputes = [
        {"verdict": "escalate", "confidence": 0.9, "triaged_at": "2026-06-14"},
        {"verdict": "auto_resolve", "confidence": 0.7, "triaged_at": "2026-06-14"},
    ]
    out = summarize_disputes(disputes)
    assert out["count"] == 2
    assert abs(out["avg_confidence"] - 0.8) < 1e-9
    assert out["by_verdict"]["escalate"] == 1


def test_summarize_stock():
    levels = [
        {"sku": "A", "qty": 100, "threshold": 10},
        {"sku": "B", "qty": 5, "threshold": 10},
        {"sku": "C", "qty": 0, "threshold": 5},
    ]
    out = summarize_stock(levels)
    assert out["total_skus"] == 3
    assert out["low_stock_count"] == 2
    assert out["total_qty"] == 105


def test_list_templates_returns_seeded_set():
    templates = list_templates()
    names = {t["name"] for t in templates}
    assert "daily_order_summary" in names
    assert "weekly_compensation" in names
    assert "executive_dashboard" in names


def test_render_daily_order_summary():
    # The daily_order_summary template uses `data.order_count` and
    # `data.by_status` etc., so the data dict needs a 'data' key
    # containing the aggregated stats.
    data = {
        "data": {
            "order_count": 1,
            "total_value_cents": 1000,
            "by_status": {"shipped": 1},
            "top_skus": [{"sku": "A", "count": 1}],
        },
    }
    out = render_template("daily_order_summary", data, period="2026-06-14")
    assert "Daily Order Summary" in out
    assert "shipped" in out


def test_render_unknown_template_raises():
    import pytest
    with pytest.raises(ValueError):
        render_template("does_not_exist", {}, period="x")
