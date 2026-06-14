"""Delivery service — orchestrates dedupe → rate limit → POST → persist."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List

from shared.common.db import session_scope
from shared.common.ids import new_uuid
from shared.common.time import utcnow
from shared.contracts.whatsapp_contract import (
    WhatsAppDeliveryRequest,
    WhatsAppDeliveryResponse,
    WhatsAppMessage,
    WhatsappChannel,
)
from sqlalchemy import select

from app.core.dedupe import DedupeStore, get_dedupe_store
from app.core.rate_limiter import RateLimiter, get_rate_limiter
from app.models.orm import DeliveryAttempt, DeliveryStatusEnum
from app.services.workspace_client import (
    RateLimitedError,
    WorkspaceClient,
    WorkspaceRejectedError,
    WorkspaceUnavailableError,
    get_workspace_client,
)

logger = logging.getLogger(__name__)


class DeliveryService:
    """Orchestrates end-to-end delivery for a WhatsAppDeliveryRequest."""

    def __init__(
        self,
        workspace: WorkspaceClient | None = None,
        dedupe: DedupeStore | None = None,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        self.workspace = workspace or get_workspace_client()
        self.dedupe = dedupe or get_dedupe_store()
        self.rate_limiter = rate_limiter or get_rate_limiter()

    async def deliver(self, request: WhatsAppDeliveryRequest) -> Dict[str, Any]:
        """Deliver the request, returning an aggregate result.

        Per-message outcomes are persisted as DeliveryAttempt rows. The
        aggregate result reports accepted, rejected, retried, errors.
        """
        accepted = 0
        rejected = 0
        retried = 0
        rate_limited = 0
        errors: List[str] = []

        for msg in request.messages:
            outcome = await self._deliver_one(request, msg)
            if outcome == "sent":
                accepted += 1
            elif outcome == "rate_limited":
                rate_limited += 1
                retried += 1
            elif outcome == "rejected":
                rejected += 1
            else:
                errors.append(f"unknown outcome for message {msg.id}: {outcome}")
        return {
            "id": request.id,
            "channel": request.channel.value,
            "account_id": request.account_id,
            "accepted": accepted,
            "rejected": rejected,
            "rate_limited": rate_limited,
            "retried": retried,
            "errors": errors,
            "delivered_at": utcnow().isoformat(),
        }

    async def _deliver_one(self, request: WhatsAppDeliveryRequest, msg: WhatsAppMessage) -> str:
        # Per-message dedupe
        if not await self.dedupe.claim(msg.id):
            logger.info("dedupe hit for message %s — skipping", msg.id)
            return "skipped"
        # Per-destination rate limit
        allowed, remaining, retry_ms = await self.rate_limiter.acquire(msg.to)
        if not allowed:
            await self._persist_attempt(
                request=request, msg=msg,
                status=DeliveryStatusEnum.RATE_LIMITED, http_status=429,
                error=f"rate limited; retry after {retry_ms}ms", attempts=1,
            )
            logger.info("rate limited for %s (retry %dms)", msg.to, retry_ms)
            return "rate_limited"
        # POST
        try:
            # Build a single-message request to the workspace
            single = WhatsAppDeliveryRequest(
                id=str(uuid.uuid4()),
                account_id=request.account_id,
                channel=request.channel,
                correlation_id=request.correlation_id,
                messages=[msg],
            )
            await self.workspace.deliver(single)
            await self._persist_attempt(
                request=request, msg=msg,
                status=DeliveryStatusEnum.SENT, http_status=200,
                error=None, attempts=1,
            )
            return "sent"
        except RateLimitedError as e:
            await self._persist_attempt(
                request=request, msg=msg,
                status=DeliveryStatusEnum.RATE_LIMITED, http_status=429,
                error=str(e), attempts=1,
            )
            return "rate_limited"
        except WorkspaceRejectedError as e:
            await self._persist_attempt(
                request=request, msg=msg,
                status=DeliveryStatusEnum.REJECTED, http_status=400,
                error=str(e), attempts=1,
            )
            return "rejected"
        except WorkspaceUnavailableError as e:
            await self._persist_attempt(
                request=request, msg=msg,
                status=DeliveryStatusEnum.FAILED, http_status=503,
                error=str(e), attempts=1,
            )
            return "failed"
        except Exception as e:  # noqa: BLE001
            await self._persist_attempt(
                request=request, msg=msg,
                status=DeliveryStatusEnum.FAILED, http_status=None,
                error=str(e), attempts=1,
            )
            return "failed"

    async def _persist_attempt(
        self,
        *,
        request: WhatsAppDeliveryRequest,
        msg: WhatsAppMessage,
        status: DeliveryStatusEnum,
        http_status: int | None,
        error: str | None,
        attempts: int,
    ) -> None:
        async with session_scope() as session:
            row = DeliveryAttempt(
                message_id=msg.id,
                dedupe_id=msg.id,
                account_id=request.account_id,
                channel=request.channel.value,
                destination=msg.to,
                status=status.value,
                http_status=http_status,
                error=error,
                attempts=attempts,
                last_attempt_at=utcnow().isoformat(),
            )
            session.add(row)
            await session.flush()


_singleton: DeliveryService | None = None


def get_delivery_service() -> DeliveryService:
    global _singleton
    if _singleton is None:
        _singleton = DeliveryService()
    return _singleton
