"""Generic judgment endpoint."""

from fastapi import APIRouter

from shared.contracts.ai_contract import (
    AIJudgmentRequest,
    AIJudgmentResult,
)
from app.services.judgment_service import JudgmentService
from app.services.audit_service import log_ai_call

router = APIRouter(prefix="/api/v1/judgment", tags=["judgment"])


@router.post("", response_model=AIJudgmentResult)
async def judge(req: AIJudgmentRequest) -> AIJudgmentResult:
    """Run a generic judgment call. Task family comes from the request."""
    service = JudgmentService()
    try:
        result = await service.judge(req)
        log_ai_call(
            task=result.task.value,
            model=result.model,
            tokens_in=result.tokens_in,
            tokens_out=result.tokens_out,
            cost_cents=result.cost_cents,
            duration_ms=result.duration_ms,
            parsed=result.parsed,
        )
        return result
    except Exception as exc:
        log_ai_call(
            task=req.task.value, model="", tokens_in=0, tokens_out=0,
            cost_cents=0.0, duration_ms=0, error=str(exc),
        )
        raise
