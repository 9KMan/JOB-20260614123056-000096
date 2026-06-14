"""Status endpoints — read delivery attempts."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from shared.common.db import session_scope

from app.models.orm import DeliveryAttempt

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["status"])


@router.get("/messages/{message_id}")
async def get_message(message_id: str) -> dict:
    async with session_scope() as session:
        stmt = select(DeliveryAttempt).where(DeliveryAttempt.message_id == message_id)
        rows = list((await session.execute(stmt)).scalars().all())
    if not rows:
        raise HTTPException(status_code=404, detail="message not found")
    return {
        "items": [
            {
                "id": r.id, "message_id": r.message_id, "dedupe_id": r.dedupe_id,
                "account_id": r.account_id, "channel": r.channel,
                "destination": r.destination, "status": r.status,
                "http_status": r.http_status, "error": r.error,
                "attempts": r.attempts, "last_attempt_at": r.last_attempt_at,
                "created_at": r.created_at, "updated_at": r.updated_at,
            }
            for r in rows
        ],
    }


@router.get("/messages")
async def list_messages(
    limit: int = Query(50, ge=1, le=500),
    status: Optional[str] = None,
    destination: Optional[str] = None,
) -> dict:
    async with session_scope() as session:
        stmt = select(DeliveryAttempt)
        if status:
            stmt = stmt.where(DeliveryAttempt.status == status)
        if destination:
            stmt = stmt.where(DeliveryAttempt.destination == destination)
        stmt = stmt.order_by(DeliveryAttempt.created_at.desc()).limit(limit)
        rows = list((await session.execute(stmt)).scalars().all())
    return {
        "items": [
            {
                "id": r.id, "message_id": r.message_id, "dedupe_id": r.dedupe_id,
                "account_id": r.account_id, "channel": r.channel,
                "destination": r.destination, "status": r.status,
                "http_status": r.http_status, "attempts": r.attempts,
                "last_attempt_at": r.last_attempt_at, "created_at": r.created_at,
            }
            for r in rows
        ],
        "total": len(rows),
    }
