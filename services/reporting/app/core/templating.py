"""Templating — Jinja2-based report templates.

Templates live as inline strings in this module. Each template declares
its required data and output formats.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from jinja2 import Environment, BaseLoader, select_autoescape


@dataclass
class TemplateInfo:
    name: str
    description: str
    schedule: str
    required_data: List[str]
    output_formats: List[str] = field(default_factory=lambda: ["json", "markdown"])
    template_str: str = ""


# --- template strings (Jinja2) ---

DAILY_ORDER_SUMMARY = """# Daily Order Summary — {{ period }}

**Order count:** {{ data.order_count }}
**Total value:** ${{ '%.2f' | format(data.total_value_cents / 100) }}

## Orders by status
| Status | Count |
|--------|-------|
{% for status, count in data.by_status.items() -%}
| {{ status }} | {{ count }} |
{% endfor %}

## Top 10 SKUs
| SKU | Count |
|-----|-------|
{% for row in data.top_skus -%}
| {{ row.sku }} | {{ row.count }} |
{% endfor %}
"""

WEEKLY_COMPENSATION = """# Weekly Compensation Report — {{ period }}

**Decisions:** {{ data.count }}
**Total amount:** ${{ '%.2f' | format(data.total_amount_cents / 100) }}

## By decision
| Decision | Count | Amount |
|----------|-------|--------|
{% for k, count in data.by_decision.items() -%}
| {{ k }} | {{ count }} | ${{ '%.2f' | format((data.by_decision_amount_cents[k] or 0) / 100) }} |
{% endfor %}
"""

WEEKLY_DISPUTE = """# Weekly Dispute Summary — {{ period }}

**Total:** {{ data.count }}
**Avg confidence:** {{ data.avg_confidence }}

## By verdict
| Verdict | Count |
|---------|-------|
{% for v, c in data.by_verdict.items() -%}
| {{ v }} | {{ c }} |
{% endfor %}
"""

STOCK_COVERAGE = """# Stock Coverage — {{ period }}

**SKUs:** {{ data.total_skus }}
**Total qty:** {{ data.total_qty }}
**Low-stock count:** {{ data.low_stock_count }}

{% if data.low_stock_skus -%}
## Low stock SKUs
{% for sku in data.low_stock_skus -%}
- {{ sku }}
{% endfor %}
{% endif %}
"""

EXECUTIVE_DASHBOARD = """# Executive Dashboard — {{ period }}

## Orders
- Count: {{ orders.order_count }}
- Value: ${{ '%.2f' | format(orders.total_value_cents / 100) }}

## Disputes
- Count: {{ disputes.count }}
- Avg confidence: {{ disputes.avg_confidence }}

## Compensations
- Count: {{ comp.count }}
- Total: ${{ '%.2f' | format(comp.total_amount_cents / 100) }}

## Stock
- SKUs: {{ stock.total_skus }}
- Low stock: {{ stock.low_stock_count }}
"""


# --- registry ---

TEMPLATES: Dict[str, TemplateInfo] = {
    "daily_order_summary": TemplateInfo(
        name="daily_order_summary",
        description="Daily snapshot of orders, status breakdown, top SKUs.",
        schedule="0 8 * * *",
        required_data=["orders"],
        output_formats=["json", "markdown"],
        template_str=DAILY_ORDER_SUMMARY,
    ),
    "weekly_compensation": TemplateInfo(
        name="weekly_compensation",
        description="Weekly compensation spend by decision type.",
        schedule="0 9 * * MON",
        required_data=["compensations"],
        output_formats=["json", "markdown"],
        template_str=WEEKLY_COMPENSATION,
    ),
    "weekly_dispute_summary": TemplateInfo(
        name="weekly_dispute_summary",
        description="Weekly dispute resolution summary.",
        schedule="0 10 * * MON",
        required_data=["disputes"],
        output_formats=["json", "markdown"],
        template_str=WEEKLY_DISPUTE,
    ),
    "stock_coverage": TemplateInfo(
        name="stock_coverage",
        description="Stock coverage and low-stock alerts.",
        schedule="0 7 * * *",
        required_data=["stock"],
        output_formats=["json", "markdown"],
        template_str=STOCK_COVERAGE,
    ),
    "executive_dashboard": TemplateInfo(
        name="executive_dashboard",
        description="One-page digest combining all key metrics.",
        schedule="0 8 * * *",
        required_data=["orders", "disputes", "compensations", "stock"],
        output_formats=["markdown"],
        template_str=EXECUTIVE_DASHBOARD,
    ),
}


_env = Environment(loader=BaseLoader(), autoescape=select_autoescape())


def list_templates() -> List[Dict[str, Any]]:
    """List template info as dicts."""
    return [
        {
            "name": t.name,
            "description": t.description,
            "schedule": t.schedule,
            "required_data": t.required_data,
            "output_formats": t.output_formats,
        }
        for t in TEMPLATES.values()
    ]


def render_template(name: str, data: Dict[str, Any], *, period: str = "current") -> str:
    """Render a template by name with the given data context."""
    tpl = TEMPLATES.get(name)
    if tpl is None:
        raise ValueError(f"unknown template: {name}")
    template = _env.from_string(tpl.template_str)
    return template.render(period=period, **data)
