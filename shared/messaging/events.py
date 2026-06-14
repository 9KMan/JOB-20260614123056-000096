"""Domain events — typed payloads emitted on the event bus.

Each event is a frozen dataclass that serializes to/from JSON for
pub/sub and audit logging.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from shared.common.ids import new_uuid
from shared.common.time import utcnow


@dataclass
class DomainEvent:
    """Base class for all domain events."""

    event_type: str = "domain.event"
    event_id: str = field(default_factory=new_uuid)
    occurred_at: str = field(default_factory=lambda: utcnow().isoformat())
    correlation_id: str = ""
    actor: str = "system"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)


@dataclass
class OrderChecked(DomainEvent):
    order_id: str = ""
    status: str = ""
    needs_action: bool = False
    reason: str = ""
    event_type: str = "order.checked"


@dataclass
class OrderDelayed(DomainEvent):
    order_id: str = ""
    delay_days: int = 0
    threshold_days: int = 0
    compensation_eligible: bool = False
    event_type: str = "order.delayed"


@dataclass
class DisputeTriaged(DomainEvent):
    dispute_id: str = ""
    verdict: str = ""  # escalate | auto_resolve | needs_human
    confidence: float = 0.0
    rationale: str = ""
    event_type: str = "dispute.triaged"


@dataclass
class StockAlert(DomainEvent):
    sku: str = ""
    warehouse: str = ""
    current_qty: int = 0
    threshold: int = 0
    trend: str = ""  # dropping | stable | rising
    event_type: str = "stock.alert"


@dataclass
class ReportReady(DomainEvent):
    report_id: str = ""
    report_type: str = ""
    period: str = ""
    artifact_uri: str = ""
    event_type: str = "report.ready"


EVENT_REGISTRY = {
    "order.checked": OrderChecked,
    "order.delayed": OrderDelayed,
    "dispute.triaged": DisputeTriaged,
    "stock.alert": StockAlert,
    "report.ready": ReportReady,
}


def event_from_dict(data: Dict[str, Any]) -> DomainEvent:
    """Reconstruct an event from a dict (best-effort)."""
    cls = EVENT_REGISTRY.get(data.get("event_type", ""), DomainEvent)
    return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
