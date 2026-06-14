"""Background retry worker — retries failed/rate-limited deliveries."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select

from shared.common.db import session_scope
from shared.common.time import utcnow
from shared.contracts.whatsapp_contract import WhatsAppDeliveryRequest, WhatsAppMessage

from app.models.orm import DeliveryAttempt, DeliveryStatusEnum
from app.services.delivery_service import get_delivery_service

logger = logging.getLogger(__name__)


MAX_ATTEMPTS = 5
BASE_BACKOFF_SECONDS = 2.0


def backoff_for(attempts: int) -> float:
    """Exponential backoff: 2, 4, 8, 16, 32 seconds (capped at 60)."""
    return min(60.0, BASE_BACKOFF_SECONDS * (2 ** max(0, attempts - 1)))


class RetryWorker:
    """Periodically retries failed and rate-limited deliveries."""

    def __init__(self, interval_seconds: float = 30.0) -> None:
        self.interval_seconds = interval_seconds
        self._stop_event: Optional[asyncio.Event] = None
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        if self._task is not None:
            return
        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._loop(), name="whatsapp-retry-worker")

    async def stop(self) -> None:
        if self._stop_event is not None:
            self._stop_event.set()
        if self._task is not None:
            try:
                await asyncio.wait_for(self._task, timeout=5.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                self._task.cancel()
        self._task = None
        self._stop_event = None

    async def _loop(self) -> None:
        assert self._stop_event is not None
        while not self._stop_event.is_set():
            try:
                await self._scan_once()
            except Exception as exc:  # noqa: BLE001
                logger.exception("retry worker loop error: %s", exc)
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.interval_seconds)
            except asyncio.TimeoutError:
                pass

    async def _scan_once(self) -> None:
        now = utcnow()
        async with session_scope() as session:
            stmt = select(DeliveryAttempt).where(
                DeliveryAttempt.status.in_([
                    DeliveryStatusEnum.FAILED.value,
                    DeliveryStatusEnum.RATE_LIMITED.value,
                ])
            )
            rows = list((await session.execute(stmt)).scalars().all())
        for row in rows:
            if row.attempts >= MAX_ATTEMPTS:
                continue
            if not row.last_attempt_at:
                continue
            try:
                last = datetime.fromisoformat(row.last_attempt_at.replace("Z", "+00:00"))
            except ValueError:
                continue
            next_at = last + timedelta(seconds=backoff_for(row.attempts + 1))
            if datetime.now(timezone.utc) < next_at:
                continue
            await self._retry(row)

    async def _retry(self, row: DeliveryAttempt) -> None:
        # Rebuild a single-message request and re-deliver
        msg = WhatsAppMessage(id=row.dedupe_id, to=row.destination, body="(retry)")
        req = WhatsAppDeliveryRequest(
            id=row.message_id, account_id=row.account_id, messages=[msg],
        )
        svc = get_delivery_service()
        result = await svc.deliver(req)
        logger.info("retry for %s result=%s", row.dedupe_id, result)
