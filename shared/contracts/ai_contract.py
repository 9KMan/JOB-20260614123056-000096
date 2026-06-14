"""AI service contract.

The AI Judgment Service accepts these payloads and returns these
results. Internal services never call the hosted AI API directly —
they go through the adapter layer in ``services/ai_judgment``.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from shared.common.ids import new_uuid
from shared.common.time import utcnow


class AITask(str, Enum):
    """Task families the AI Judgment Service supports."""

    CLASSIFY = "classify"  # map text → label
    EXTRACT = "extract"  # map text → structured fields
    SUMMARIZE = "summarize"  # map text → short summary
    JUDGE = "judge"  # free-form judgment call
    DRAFT = "draft"  # generate a draft response


class AIJudgmentRequest(BaseModel):
    """Generic AI judgment request.

    The ``schema_hint`` field constrains the output structure when
    relevant (e.g. dispute triage should return verdict+confidence).
    """

    id: str = Field(default_factory=new_uuid)
    task: AITask
    prompt: str
    context: Dict[str, Any] = Field(default_factory=dict)
    schema_hint: Optional[Dict[str, Any]] = None
    max_tokens: int = 800
    temperature: float = 0.2


class AIJudgmentResult(BaseModel):
    id: str
    task: AITask
    content: str
    parsed: Optional[Dict[str, Any]] = None
    model: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    cost_cents: float = 0.0
    duration_ms: int = 0
    completed_at: str = Field(default_factory=lambda: utcnow().isoformat())


class AIClassifyRequest(AIJudgmentRequest):
    labels: List[str] = Field(default_factory=list)
    task: AITask = AITask.CLASSIFY


class AIClassifyResult(AIJudgmentResult):
    label: str = ""
    confidence: float = 0.0
    task: AITask = AITask.CLASSIFY


class AIExtractRequest(AIJudgmentRequest):
    fields: List[str] = Field(default_factory=list)
    task: AITask = AITask.EXTRACT


class AIExtractResult(AIJudgmentResult):
    extracted: Dict[str, Any] = Field(default_factory=dict)
    task: AITask = AITask.EXTRACT


class AISummarizeRequest(AIJudgmentRequest):
    max_words: int = 120
    task: AITask = AITask.SUMMARIZE


class AISummarizeResult(AIJudgmentResult):
    summary: str = ""
    task: AITask = AITask.SUMMARIZE


__all__ = [
    "AITask",
    "AIJudgmentRequest",
    "AIJudgmentResult",
    "AIClassifyRequest",
    "AIClassifyResult",
    "AIExtractRequest",
    "AIExtractResult",
    "AISummarizeRequest",
    "AISummarizeResult",
]
