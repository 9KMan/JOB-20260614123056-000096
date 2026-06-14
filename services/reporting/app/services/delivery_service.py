"""Delivery service — hands off a finished report to the WhatsApp workspace.

Wraps the call in try/except — failure to deliver does NOT fail the
report. The report summary will show ``delivered=false`` if delivery
failed, so an operator can investigate.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

from shared.contracts.whatsapp_contract import (
    WhatsAppDeliveryRequest,
    WhatsAppMessage,
    WhatsappChannel,
)

logger = logging.getLogger(__name__)

WHATSAPP_ADAPTER_URL = os.environ.get("KMAN_WHATSAPP_URL", "http://whatsapp_adapter:8005")


async def deliver_report(
    *,
    report_name: str,
    period: str,
    body: str,
    recipients: List[str],
    artifact_uri: Optional[str] = None,
) -> Dict[str, Any]:
    """Deliver a finished report to the WhatsApp adapter.

    Returns a small dict describing the outcome — never raises.
    """
    if not recipients:
        return {"delivered": False, "reason": "no recipients"}
    if not body:
        return {"delivered": False, "reason": "empty body"}
    try:
        msgs: List[WhatsAppMessage] = []
        for r in recipients:
            m = WhatsAppMessage(
                to=r,
                body=body[:1500],  # WhatsApp practical limit
                metadata={"report_name": report_name, "period": period, "artifact_uri": artifact_uri or ""},
            )
            msgs.append(m)
        req = WhatsAppDeliveryRequest(
            account_id=os.environ.get("KMAN_ACCOUNT_ID", "default"),
            messages=msgs,
            channel=WhatsappChannel.WHATSAPP,
        )
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{WHATSAPP_ADAPTER_URL}/api/v1/deliver", json=req.model_dump(mode="json")
            )
        if resp.status_code >= 400:
            logger.warning("whatsapp delivery returned %d: %s", resp.status_code, resp.text)
            return {"delivered": False, "reason": f"http {resp.status_code}", "response": resp.text}
        return {"delivered": True, "response": resp.json()}
    except Exception as exc:  # noqa: BLE001
        logger.warning("whatsapp delivery failed: %s", exc)
        return {"delivered": False, "reason": str(exc)}
