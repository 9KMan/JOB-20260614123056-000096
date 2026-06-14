"""Audit log — every AI call is logged for compliance + cost tracking."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from shared.common.config import get_settings
from shared.common.ids import new_correlation_id
from shared.common.time import utcnow

logger = logging.getLogger(__name__)


def log_ai_call(
    *,
    task: str,
    model: str,
    tokens_in: int,
    tokens_out: int,
    cost_cents: float,
    duration_ms: int,
    correlation_id: Optional[str] = None,
    actor: str = "system",
    parsed: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
) -> None:
    """Emit a structured audit log line for an AI call.

    In production this also writes to a durable store (e.g. an
    ``ai_audit_log`` table or a managed log sink). For now, JSON log
    line is the source of truth — downstream pipelines can ingest it.
    """
    settings = get_settings()
    record = {
        "ts": utcnow().isoformat(),
        "kind": "ai_call_audit",
        "task": task,
        "model": model,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_cents": cost_cents,
        "duration_ms": duration_ms,
        "correlation_id": correlation_id or new_correlation_id(),
        "actor": actor,
        "service": settings.service_name,
        "parsed": parsed,
        "error": error,
    }
    logger.info(json.dumps(record, default=str))
