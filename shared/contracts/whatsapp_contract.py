"""WhatsApp workspace contract.

The other developer's WhatsApp workspace exposes a webhook that
accepts these payloads. Our services call this contract — never
the underlying chat provider API directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from shared.common.ids import new_uuid
from shared.common.time import utcnow


class WhatsappChannel(str, Enum):
    """Where the message is being delivered."""

    WHATSAPP = "whatsapp"
    INTERNAL = "internal"  # account-manager only
    SMS = "sms"


class WhatsAppMessage(BaseModel):
    """A single outbound message."""

    id: str = Field(default_factory=new_uuid)
    to: str  # phone or account-manager handle
    body: str
    media_url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WhatsAppDeliveryRequest(BaseModel):
    """Batch of messages to deliver to the WhatsApp workspace."""

    id: str = Field(default_factory=new_uuid)
    channel: WhatsappChannel = WhatsappChannel.WHATSAPP
    account_id: str
    correlation_id: str = ""
    messages: List[WhatsAppMessage] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: utcnow().isoformat())


class WhatsAppDeliveryResponse(BaseModel):
    """Result returned by the WhatsApp workspace after a delivery."""

    id: str
    accepted: int
    rejected: int
    errors: List[str] = Field(default_factory=list)
    delivered_at: str = Field(default_factory=lambda: utcnow().isoformat())


# Pydantic re-exports for downstream typing
__all__ = [
    "WhatsappChannel",
    "WhatsAppMessage",
    "WhatsAppDeliveryRequest",
    "WhatsAppDeliveryResponse",
]
