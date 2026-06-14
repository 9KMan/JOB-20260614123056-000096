"""Inbound service — handles messages arriving FROM the WhatsApp workspace.

Persists + publishes to Redis pub/sub. Returns 202 immediately.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Any, Dict, Optional

from shared.common.ids import new_correlation_id
from shared.common.time import utcnow
from shared.messaging.queue_contract import publish

logger = logging.getLogger(__name__)


def verify_signature(body: bytes, signature: str, secret: str) -> bool:
    """Verify the HMAC signature header. Returns True if valid (or no secret set)."""
    if not secret:
        return True
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")


async def handle_inbound(payload: Dict[str, Any], signature: str = "", secret: str = "") -> Dict[str, Any]:
    """Handle an inbound message: validate + publish to pub/sub."""
    if not verify_signature(json.dumps(payload, default=str).encode("utf-8"), signature, secret):
        raise PermissionError("invalid signature")
    correlation_id = new_correlation_id()
    enriched = {**payload, "received_at": utcnow().isoformat(), "correlation_id": correlation_id}
    try:
        await publish("kman:inbound", enriched)
    except Exception as exc:  # noqa: BLE001
        logger.warning("publish inbound failed: %s", exc)
    return {"status": "accepted", "correlation_id": correlation_id}
