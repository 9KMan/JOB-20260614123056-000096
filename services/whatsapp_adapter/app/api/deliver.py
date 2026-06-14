"""Deliver endpoint — the main internal-facing API."""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from shared.contracts.whatsapp_contract import (
    WhatsAppDeliveryRequest,
    WhatsAppDeliveryResponse,
)
from app.services.delivery_service import get_delivery_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/deliver", tags=["deliver"])


@router.post("")
async def deliver(req: WhatsAppDeliveryRequest) -> dict:
    """Deliver a batch of messages to the WhatsApp workspace.

    Returns an aggregate result. Per-message outcomes are persisted.
    """
    if not req.messages:
        raise HTTPException(status_code=400, detail="messages must not be empty")
    svc = get_delivery_service()
    return await svc.deliver(req)
