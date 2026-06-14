"""Classification endpoint."""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from shared.contracts.ai_contract import AIJudgmentResult, AITask
from app.services.judgment_service import JudgmentService
from app.services.audit_service import log_ai_call

router = APIRouter(prefix="/api/v1/classify", tags=["classify"])


class ClassifyDto(BaseModel):
    content: str
    labels: List[str] = Field(default_factory=list)
    context: Optional[Dict[str, Any]] = None


@router.post("", response_model=AIJudgmentResult)
async def classify(req: ClassifyDto) -> AIJudgmentResult:
    """Classify text into one of the given labels."""
    service = JudgmentService()
    result = await service.classify(
        prompt=req.content, labels=req.labels, context=req.context
    )
    log_ai_call(
        task=AITask.CLASSIFY.value, model=result.model,
        tokens_in=result.tokens_in, tokens_out=result.tokens_out,
        cost_cents=result.cost_cents, duration_ms=result.duration_ms,
        parsed=result.parsed,
    )
    return result
