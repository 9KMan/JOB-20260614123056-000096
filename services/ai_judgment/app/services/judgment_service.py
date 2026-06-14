"""Judgment service — orchestrates adapter + prompts + cost + audit."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from shared.contracts.ai_contract import (
    AIJudgmentRequest,
    AIJudgmentResult,
    AITask,
)
from shared.common.time import utcnow

from app.adapters.base import ModelAdapter
from app.adapters.factory import get_adapter
from app.core import cost, prompts

logger = logging.getLogger(__name__)


class JudgmentService:
    """High-level orchestration for AI judgment calls.

    Owns:
      - prompt construction per task
      - adapter invocation
      - cost calculation
      - audit log emission
    """

    def __init__(self, adapter: Optional[ModelAdapter] = None) -> None:
        self.adapter = adapter or get_adapter()

    async def judge(self, req: AIJudgmentRequest) -> AIJudgmentResult:
        """Run a judgment call for any AITask family."""
        if req.task is AITask.CLASSIFY:
            return await self.classify(
                prompt=req.prompt,
                labels=(req.context or {}).get("labels", []),
                context=req.context,
                max_tokens=req.max_tokens,
                temperature=req.temperature,
                schema_hint=req.schema_hint,
            )
        if req.task is AITask.EXTRACT:
            return await self.extract(
                prompt=req.prompt,
                fields=(req.context or {}).get("fields", []),
                context=req.context,
                max_tokens=req.max_tokens,
                temperature=req.temperature,
                schema_hint=req.schema_hint,
            )
        if req.task is AITask.SUMMARIZE:
            return await self.summarize(
                prompt=req.prompt,
                max_words=(req.context or {}).get("max_words", 120),
                context=req.context,
                max_tokens=req.max_tokens,
                temperature=req.temperature,
                schema_hint=req.schema_hint,
            )
        if req.task is AITask.DRAFT:
            return await self.draft(
                prompt=req.prompt,
                context=req.context,
                max_tokens=req.max_tokens,
                temperature=req.temperature,
            )
        # Default: free-form JUDGE
        return await self._freeform_judge(req)

    async def _freeform_judge(self, req: AIJudgmentRequest) -> AIJudgmentResult:
        system, user = prompts.judge_prompt(
            content=req.prompt,
            schema_hint=req.schema_hint,
            context=req.context,
        )
        resp = await self.adapter.complete(
            system=system, user=user,
            max_tokens=req.max_tokens, temperature=req.temperature,
            json_mode=req.schema_hint is not None,
        )
        return self._to_result(req, resp)

    async def classify(
        self,
        *,
        prompt: str,
        labels: List[str],
        context: Optional[Dict[str, Any]] = None,
        max_tokens: int = 200,
        temperature: float = 0.0,
        schema_hint: Optional[Dict[str, Any]] = None,
    ) -> AIJudgmentResult:
        """Classification."""
        system, user = prompts.classify_prompt(content=prompt, labels=labels, context=context)
        resp = await self.adapter.classify(system=system, user=user, labels=labels)
        result = self._to_result_classify(req=None, resp=resp)
        return result

    async def extract(
        self,
        *,
        prompt: str,
        fields: List[str],
        context: Optional[Dict[str, Any]] = None,
        max_tokens: int = 600,
        temperature: float = 0.0,
        schema_hint: Optional[Dict[str, Any]] = None,
    ) -> AIJudgmentResult:
        """Structured extraction."""
        system, user = prompts.extract_prompt(content=prompt, fields=fields, context=context)
        resp = await self.adapter.extract(system=system, user=user, fields=fields)
        return self._to_result_extract(resp=resp, fields=fields)

    async def summarize(
        self,
        *,
        prompt: str,
        max_words: int = 120,
        context: Optional[Dict[str, Any]] = None,
        max_tokens: int = 400,
        temperature: float = 0.3,
        schema_hint: Optional[Dict[str, Any]] = None,
    ) -> AIJudgmentResult:
        """Summarization."""
        system, user = prompts.summarize_prompt(content=prompt, max_words=max_words, context=context)
        resp = await self.adapter.summarize(system=system, user=user, max_words=max_words)
        return self._to_result_summarize(resp=resp)

    async def draft(
        self,
        *,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        max_tokens: int = 400,
        temperature: float = 0.5,
    ) -> AIJudgmentResult:
        """Draft a response message."""
        system, user = prompts.draft_prompt(
            content=prompt, context=context, max_words=max(50, max_tokens // 2)
        )
        resp = await self.adapter.complete(
            system=system, user=user, max_tokens=max_tokens, temperature=temperature, json_mode=False
        )
        return self._to_result(None, resp)

    # ---- helpers ----

    def _to_result(self, req: Optional[AIJudgmentRequest], resp) -> AIJudgmentResult:
        cost_cents = cost.estimate_cost_cents(resp.model, resp.tokens_in, resp.tokens_out)
        return AIJudgmentResult(
            id=req.id if req else "",
            task=req.task if req else AITask.JUDGE,
            content=resp.content,
            parsed=resp.parsed,
            model=resp.model,
            tokens_in=resp.tokens_in,
            tokens_out=resp.tokens_out,
            cost_cents=round(cost_cents, 4),
            duration_ms=resp.duration_ms,
            completed_at=utcnow().isoformat(),
        )

    def _to_result_classify(self, req: Optional[AIJudgmentRequest], resp) -> AIJudgmentResult:
        cost_cents = cost.estimate_cost_cents(resp.model, resp.tokens_in, resp.tokens_out)
        return AIJudgmentResult(
            id=req.id if req else "",
            task=AITask.CLASSIFY,
            content=resp.content,
            parsed={"label": resp.label, "confidence": resp.confidence, **(resp.parsed or {})},
            model=resp.model,
            tokens_in=resp.tokens_in,
            tokens_out=resp.tokens_out,
            cost_cents=round(cost_cents, 4),
            duration_ms=resp.duration_ms,
        )

    def _to_result_extract(self, resp, fields: List[str]) -> AIJudgmentResult:
        cost_cents = cost.estimate_cost_cents(resp.model, resp.tokens_in, resp.tokens_out)
        return AIJudgmentResult(
            task=AITask.EXTRACT,
            content=resp.content,
            parsed=resp.extracted,
            model=resp.model,
            tokens_in=resp.tokens_in,
            tokens_out=resp.tokens_out,
            cost_cents=round(cost_cents, 4),
            duration_ms=resp.duration_ms,
        )

    def _to_result_summarize(self, resp) -> AIJudgmentResult:
        cost_cents = cost.estimate_cost_cents(resp.model, resp.tokens_in, resp.tokens_out)
        return AIJudgmentResult(
            task=AITask.SUMMARIZE,
            content=resp.content,
            parsed={"summary": resp.summary},
            model=resp.model,
            tokens_in=resp.tokens_in,
            tokens_out=resp.tokens_out,
            cost_cents=round(cost_cents, 4),
            duration_ms=resp.duration_ms,
        )
