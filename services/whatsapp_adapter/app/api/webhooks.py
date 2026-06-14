"""Inbound webhooks — receive messages from the WhatsApp workspace."""

import json
import logging
import os
from typing import Any, Dict

from fastapi import APIRouter, Header, HTTPException, Request

from app.services.inbound_service import handle_inbound

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


@router.post("/incoming")
async def incoming(
    request: Request,
    x_kman_signature: str = Header(default=""),
) -> Dict[str, Any]:
    """Receive an inbound message from the WhatsApp workspace.

    Verifies HMAC signature when secret is configured. Publishes to
    Redis pub/sub channel ``kman:inbound`` for downstream services to
    subscribe. Returns 202 Accepted.
    """
    body = await request.body()
    secret = os.environ.get("KMAN_WORKSPACE_WEBHOOK_SECRET", "")
    try:
        payload = json.loads(body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="invalid json")
    try:
        result = await handle_inbound(payload, signature=x_kman_signature, secret=secret)
    except PermissionError as e:
        raise HTTPException(status_code=401, detail=str(e))
    return result
