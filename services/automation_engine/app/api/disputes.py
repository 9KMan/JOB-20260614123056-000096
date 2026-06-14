"""Dispute triage endpoints."""

from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from shared.common.db import session_scope
from shared.contracts.automation_contract import (
    DisputeTriageRequest,
    DisputeTriageResult,
)
from shared.contracts.ai_contract import AIJudgmentRequest, AITask

from app.services import dispute_service

router = APIRouter(prefix="/api/v1/disputes", tags=["disputes"])


class TriageRequestDto(BaseModel):
    """HTTP DTO — wraps the contract with a use_ai flag."""
    dispute_id: str
    order_id: str
    customer_message: str
    order_value_cents: int = 0
    prior_disputes: int = 0
    use_ai: bool = True


@router.post("/triage", response_model=DisputeTriageResult)
async def triage_dispute(req: TriageRequestDto) -> DisputeTriageResult:
    """Triage a dispute (rule-based or AI-assisted)."""
    base = DisputeTriageRequest(
        dispute_id=req.dispute_id,
        order_id=req.order_id,
        customer_message=req.customer_message,
        order_value_cents=req.order_value_cents,
        prior_disputes=req.prior_disputes,
    )
    if req.use_ai:
        result = await dispute_service.ai_assisted_triage(base)
    else:
        result = dispute_service.rule_based_triage(base)
    async with session_scope() as session:
        await dispute_service.persist_triage(
            session, result, req.customer_message, req.order_id
        )
    return result


@router.get("", response_model=ListResponse[dict])
async def list_disputes(limit: int = Query(50, ge=1, le=500)) -> ListResponse[dict]:
    """List recent triaged disputes."""
    from sqlalchemy import select
    from app.models.orm import Dispute
    async with session_scope() as session:
        stmt = select(Dispute).order_by(Dispute.created_at.desc()).limit(limit)
        rows = list((await session.execute(stmt)).scalars().all())
    items = [
        {
            "id": r.id,
            "dispute_id": r.dispute_id,
            "order_id": r.order_id,
            "verdict": r.verdict.value if hasattr(r.verdict, "value") else r.verdict,
            "confidence": r.confidence,
            "rationale": r.rationale,
            "suggested_response": r.suggested_response,
            "triaged_at": r.triaged_at,
        }
        for r in rows
    ]
    return ListResponse[dict](items=items, total=len(items))
