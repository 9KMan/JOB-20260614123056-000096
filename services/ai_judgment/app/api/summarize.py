"""Summarization endpoint."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, Optional

from shared.contracts.ai_contract import AIJudgmentResult, AITask
from app.services.judgment_service import JudgmentService
from app.services.audit_service import log_ai_call

router = APIRouter(prefix="/api/v1/summarize", tags=["summarize"])


class SummarizeDto(BaseModel):
    content: str
    max_words: int = 120
    context: Optional[Dict[str, Any]] = None


@router.post("", response_model=AIJudgmentResult)
async def summarize(req: SummarizeDto) -> AIJudgmentResult:
    """Summarize text into a short paragraph."""
    service = JudgmentService()
    result = await service.summarize(
        prompt=req.content, max_words=req.max_words, context=req.context
    )
    log_ai_call(
        task=AITask.SUMMARIZE.value, model=result.model,
        tokens_in=result.tokens_in, tokens_out=result.tokens_out,
        cost_cents=result.cost_cents, duration_ms=result.duration_ms,
        parsed=result.parsed,
    )
    return result
