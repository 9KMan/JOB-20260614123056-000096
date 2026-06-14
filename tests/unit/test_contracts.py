"""Tests for the shared contracts and queue contract (round-trip)."""
import os
import sys
import json

# Put the workspace on sys.path so we can import `shared`.
_HERE = os.path.dirname(os.path.abspath(__file__))
_WORKSPACE = os.path.abspath(os.path.join(_HERE, "..", ".."))
if _WORKSPACE not in sys.path:
    sys.path.insert(0, _WORKSPACE)

from shared.contracts.whatsapp_contract import (
    WhatsAppDeliveryRequest,
    WhatsAppDeliveryResponse,
    WhatsAppMessage,
    WhatsappChannel,
)
from shared.contracts.automation_contract import (
    OrderCheckRequest,
    OrderCheckResult,
    OrderStatus,
    DelayCheckRequest,
    DelayCheckResult,
    CompensationDecision,
    DisputeTriageRequest,
    DisputeTriageResult,
    DisputeVerdict,
    StockCheckRequest,
    StockCheckResult,
)
from shared.contracts.ai_contract import (
    AIJudgmentRequest,
    AIJudgmentResult,
    AITask,
    AIClassifyRequest,
    AIClassifyResult,
    AIExtractRequest,
    AIExtractResult,
)
from shared.messaging.events import (
    OrderChecked,
    OrderDelayed,
    DisputeTriaged,
    StockAlert,
    ReportReady,
)
from shared.messaging.queue_contract import QueueMessage


def test_whatsapp_request_round_trip():
    req = WhatsAppDeliveryRequest(
        account_id="acct-1",
        messages=[WhatsAppMessage(to="+15551234567", body="Hello")],
        channel=WhatsappChannel.WHATSAPP,
    )
    body = req.model_dump(mode="json")
    req2 = WhatsAppDeliveryRequest.model_validate(body)
    assert req2.messages[0].to == "+15551234567"
    assert req2.channel is WhatsappChannel.WHATSAPP


def test_whatsapp_request_empty_messages_accepted():
    req = WhatsAppDeliveryRequest(account_id="a", messages=[])
    assert req.messages == []


def test_order_check_result_status():
    r = OrderCheckResult(order_id="X", status=OrderStatus.SHIPPED, needs_action=False)
    assert r.status is OrderStatus.SHIPPED


def test_delay_check_result():
    r = DelayCheckResult(order_id="X", delay_days=5, is_delayed=True, threshold_days=3)
    assert r.is_delayed is True
    assert r.compensation_eligible is False


def test_compensation_decision_decision_field():
    d = CompensationDecision(order_id="X", decision="refund_full", amount_cents=1000)
    assert d.decision == "refund_full"
    assert d.amount_cents == 1000


def test_dispute_triage_verdict():
    r = DisputeTriageResult(dispute_id="D1", verdict=DisputeVerdict.ESCALATE, confidence=0.9)
    assert r.verdict is DisputeVerdict.ESCALATE


def test_ai_judgment_request_default_task():
    req = AIJudgmentRequest(task=AITask.JUDGE, prompt="x")
    assert req.task is AITask.JUDGE
    assert req.temperature == 0.2


def test_ai_classify_request_requires_labels():
    req = AIClassifyRequest(prompt="x", labels=["a", "b"])
    assert req.task is AITask.CLASSIFY
    assert req.labels == ["a", "b"]


def test_ai_extract_result_parses_dict():
    r = AIExtractResult(id="x", task=AITask.EXTRACT, content="{}", parsed={"k": "v"}, extracted={"k": "v"})
    assert r.parsed == {"k": "v"}


def test_order_checked_event_serialization():
    e = OrderChecked(order_id="X", status="shipped", needs_action=False, reason="ok")
    body = json.loads(e.to_json())
    assert body["event_type"] == "order.checked"
    assert body["order_id"] == "X"


def test_order_delayed_event_serialization():
    e = OrderDelayed(order_id="X", delay_days=5, threshold_days=3, compensation_eligible=True)
    body = json.loads(e.to_json())
    assert body["event_type"] == "order.delayed"
    assert body["delay_days"] == 5


def test_dispute_triaged_event():
    e = DisputeTriaged(dispute_id="D1", verdict="escalate", confidence=0.9)
    body = json.loads(e.to_json())
    assert body["event_type"] == "dispute.triaged"


def test_stock_alert_event():
    e = StockAlert(sku="A", warehouse="default", current_qty=0, threshold=5, trend="dropping")
    body = json.loads(e.to_json())
    assert body["event_type"] == "stock.alert"


def test_report_ready_event():
    e = ReportReady(report_id="R1", report_type="daily_order_summary", period="2026-06-14", artifact_uri="s3://x")
    body = json.loads(e.to_json())
    assert body["event_type"] == "report.ready"


def test_queue_message_round_trip():
    msg = QueueMessage(queue="kman:queue:test", payload={"k": "v"})
    raw = msg.to_json()
    msg2 = QueueMessage.from_json("kman:queue:test", raw)
    assert msg2.queue == "kman:queue:test"
    assert msg2.payload == {"k": "v"}
    assert msg2.dedupe_id == msg.dedupe_id
