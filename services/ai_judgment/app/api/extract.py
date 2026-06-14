"""Extraction endpoint."""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from shared.contracts.ai_contract import AIJudgmentResult, AITask
from app.services.judgment_service import JudgmentService
from app.services.audit_service import log_ai_call

router = APIRouter(prefix="/api/v1/extract", tags=["extract"])


class ExtractDto(BaseModel):
    content: str
    fields: List[str] = Field(default_factory=list)
    context: Optional[Dict[str, Any]] = None


@router.post("", response_model=AIJudgmentResult)
async def extract(req: ExtractDto) -> AIJudgmentResult:
    """Extract structured fields from text."""
    service = JudgmentService()
    result = await service.extract(
        prompt=req.content, fields=req.fields, context=req.context
    )
    log_ai_call(
        task=AITask.EXTRACT.value, model=result.model,
        tokens_in=result.tokens_in, tokens_out=result.tokens_out,
        cost_cents=result.cost_cents, duration_ms=result.duration_ms,
        parsed=result.parsed,
    )
    return result
