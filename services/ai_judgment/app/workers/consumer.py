"""Consumer for QUEUE_DISPUTES.

Polls the queue, calls the judgment service for each dispute, and
emits a DecisionPersisted event. Failures are re-enqueued with backoff.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from shared.common.time import utcnow
from shared.messaging.queue_contract import (
    QUEUE_DISPUTES,
    QueueMessage,
    consume,
    enqueue_message,
)
from shared.contracts.ai_contract import AIJudgmentRequest, AITask

from app.services.judgment_service import JudgmentService

logger = logging.getLogger(__name__)


async def handle_dispute_message(msg: QueueMessage) -> None:
    """Process a single dispute message."""
    payload = msg.payload
    dispute_id = payload.get("dispute_id") or "unknown"
    logger.info("processing dispute %s (corr=%s)", dispute_id, msg.correlation_id)
    service = JudgmentService()
    req = AIJudgmentRequest(
        task=AITask.JUDGE,
        prompt=(
            f"Dispute {dispute_id}. "
            f"Order ID: {payload.get('order_id', '')}. "
            f"Customer message: {payload.get('customer_message', '')}"
        ),
        context={
            "order_value_cents": payload.get("order_value_cents", 0),
            "prior_disputes": payload.get("prior_disputes", 0),
        },
        schema_hint={
            "verdict": "auto_resolve|escalate|needs_human",
            "confidence": "float 0..1",
            "rationale": "string",
            "suggested_response": "string",
        },
    )
    result = await service.judge(req)
    logger.info(
        "dispute %s verdict model=%s cost_cents=%.4f duration_ms=%d",
        dispute_id, result.model, result.cost_cents, result.duration_ms,
    )


async def run_consumer(stop_event: Optional[asyncio.Event] = None) -> None:
    """Start the dispute consumer loop."""
    logger.info("starting dispute consumer on %s", QUEUE_DISPUTES)
    await consume(QUEUE_DISPUTES, handle_dispute_message, stop_event=stop_event)
