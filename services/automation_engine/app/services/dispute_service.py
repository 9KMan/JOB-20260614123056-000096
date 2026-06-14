"""Dispute service — pre-screen disputes with rule-based flags.

For nuanced judgment, this service optionally calls the AI Judgment
Service. Failure to reach the AI service does NOT block the rule-based
path — we still return a pre-screen verdict with confidence=0.0 and a
note that the AI call failed.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.common.http import ServiceClient
from shared.common.ids import new_correlation_id
from shared.contracts.ai_contract import (
    AIJudgmentRequest,
    AIJudgmentResult,
    AITask,
)
from shared.contracts.automation_contract import (
    DisputeTriageRequest,
    DisputeTriageResult,
    DisputeVerdict,
)
from shared.messaging.events import DisputeTriaged
from shared.messaging.queue_contract import (
    QUEUE_DISPUTES,
    QueueMessage,
    enqueue_message,
)

from app.core.rules import pre_screen_dispute
from app.models.orm import Dispute

logger = logging.getLogger(__name__)

AI_SERVICE_URL = os.environ.get("KMAN_AI_URL", "http://ai_judgment:8002")
AI_TIMEOUT = float(os.environ.get("KMAN_AI_TIMEOUT", "8.0"))

# When AI confidence is below this threshold, escalate to a human
ESCALATE_BELOW_CONFIDENCE = 0.6


def rule_based_triage(req: DisputeTriageRequest) -> DisputeTriageResult:
    """Triage a dispute with rule-based pre-screen only."""
    flags = pre_screen_dispute(req.customer_message)
    if flags["mentions_legal"]:
        verdict = DisputeVerdict.ESCALATE
        rationale = "Customer mentioned legal action — escalates immediately."
        confidence = 0.95
    elif flags["aggressive_tone"] and req.order_value_cents >= 10_000:
        verdict = DisputeVerdict.ESCALATE
        rationale = "Aggressive tone on a high-value order — escalates."
        confidence = 0.8
    elif flags["refund_requested"] and req.prior_disputes == 0:
        verdict = DisputeVerdict.AUTO_RESOLVE
        rationale = "First-time refund request — eligible for auto-resolve."
        confidence = 0.7
    else:
        verdict = DisputeVerdict.NEEDS_HUMAN
        rationale = "Pre-screen inconclusive — human review required."
        confidence = 0.0
    return DisputeTriageResult(
        dispute_id=req.dispute_id,
        verdict=verdict,
        confidence=confidence,
        rationale=rationale,
        suggested_response="",
    )


async def ai_assisted_triage(
    req: DisputeTriageRequest,
) -> DisputeTriageResult:
    """Call the AI Judgment Service for nuanced dispute triage.

    Falls back to rule-based triage if the AI call fails.
    """
    base = rule_based_triage(req)
    client = ServiceClient(AI_SERVICE_URL, name="ai_judgment", timeout=AI_TIMEOUT)
    ai_req = AIJudgmentRequest(
        task=AITask.JUDGE,
        prompt=(
            f"Dispute {req.dispute_id} for order {req.order_id}.\n"
            f"Order value: {req.order_value_cents / 100:.2f}.\n"
            f"Prior disputes on file: {req.prior_disputes}.\n"
            f"Customer message: {req.customer_message!r}\n\n"
            "Triage: respond with JSON containing verdict "
            "(auto_resolve|escalate|needs_human), confidence (0..1), "
            "rationale, and a one-paragraph suggested_response."
        ),
        context={
            "order_value_cents": req.order_value_cents,
            "prior_disputes": req.prior_disputes,
        },
        schema_hint={
            "verdict": "auto_resolve|escalate|needs_human",
            "confidence": "float 0..1",
            "rationale": "string",
            "suggested_response": "string",
        },
    )
    try:
        resp = await client.request("POST", "/api/v1/judgment", json=ai_req.model_dump(mode="json"))
        if resp.status_code != 200:
            logger.warning("AI judgment returned %d: %s", resp.status_code, resp.text)
            await client.close()
            return base
        body = resp.json()
        ai_result = AIJudgmentResult.model_validate(body)
        parsed = ai_result.parsed or {}
        verdict_raw = str(parsed.get("verdict", "")).lower()
        try:
            verdict = DisputeVerdict(verdict_raw)
        except ValueError:
            verdict = base.verdict
        confidence = float(parsed.get("confidence", base.confidence) or 0.0)
        if confidence < ESCALATE_BELOW_CONFIDENCE:
            verdict = DisputeVerdict.NEEDS_HUMAN
        result = DisputeTriageResult(
            dispute_id=req.dispute_id,
            verdict=verdict,
            confidence=confidence,
            rationale=str(parsed.get("rationale") or base.rationale),
            suggested_response=str(parsed.get("suggested_response") or ""),
        )
        await client.close()
        return result
    except Exception as exc:  # noqa: BLE001
        logger.warning("AI judgment failed, falling back to rule-based: %s", exc)
        await client.close()
        return base


async def persist_triage(
    session: AsyncSession,
    result: DisputeTriageResult,
    customer_message: str,
    order_id: str,
) -> DisputeTriaged:
    """Persist the triage decision and emit the DisputeTriaged event."""
    stmt = select(Dispute).where(Dispute.dispute_id == result.dispute_id)
    dispute = (await session.execute(stmt)).scalar_one_or_none()
    if dispute is None:
        dispute = Dispute(
            dispute_id=result.dispute_id,
            order_id=order_id,
            customer_message=customer_message,
        )
        session.add(dispute)
    dispute.verdict = result.verdict
    dispute.confidence = result.confidence
    dispute.rationale = result.rationale
    dispute.suggested_response = result.suggested_response
    await session.flush()
    return DisputeTriaged(
        dispute_id=result.dispute_id,
        verdict=result.verdict.value,
        confidence=result.confidence,
        rationale=result.rationale,
        correlation_id=new_correlation_id(),
    )


async def enqueue_dispute_triage(dispute_id: str) -> str:
    msg = QueueMessage(
        queue=QUEUE_DISPUTES,
        payload={"dispute_id": dispute_id},
    )
    return await enqueue_message(msg)
