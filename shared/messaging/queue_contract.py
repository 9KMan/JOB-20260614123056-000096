"""Queue names and a thin wrapper around the Redis client.

We use Redis lists as the queue substrate — Celery-compatible, no extra
broker to operate. Each service owns its consumer; producers enqueue
JSON-serialized messages with a deduplication ID for idempotent retry.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

import redis.asyncio as aioredis

from shared.common.config import get_settings
from shared.common.ids import new_correlation_id, new_uuid
from shared.common.time import utcnow


# Canonical queue names — referenced by both producers and consumers
QUEUE_ORDER_CHECKS = "kman:queue:order_checks"
QUEUE_DELAY_HANDLER = "kman:queue:delay_handler"
QUEUE_DISPUTES = "kman:queue:disputes"
QUEUE_STOCK_MONITOR = "kman:queue:stock_monitor"
QUEUE_REPORTING = "kman:queue:reporting"

ALL_QUEUES: List[str] = [
    QUEUE_ORDER_CHECKS,
    QUEUE_DELAY_HANDLER,
    QUEUE_DISPUTES,
    QUEUE_STOCK_MONITOR,
    QUEUE_REPORTING,
]


@dataclass
class QueueMessage:
    """A message enqueued on a queue.

    ``dedupe_id`` is used for idempotent processing: if a consumer
    sees the same id within the dedupe window, it skips the work.
    """

    queue: str
    payload: Dict[str, Any]
    dedupe_id: str = field(default_factory=new_uuid)
    correlation_id: str = field(default_factory=new_correlation_id)
    enqueued_at: str = field(default_factory=lambda: utcnow().isoformat())

    def to_json(self) -> str:
        return json.dumps(
            {
                "dedupe_id": self.dedupe_id,
                "correlation_id": self.correlation_id,
                "enqueued_at": self.enqueued_at,
                "payload": self.payload,
            }
        )

    @classmethod
    def from_json(cls, queue: str, raw: str) -> "QueueMessage":
        data = json.loads(raw)
        return cls(
            queue=queue,
            payload=data["payload"],
            dedupe_id=data.get("dedupe_id") or new_uuid(),
            correlation_id=data.get("correlation_id") or new_correlation_id(),
            enqueued_at=data.get("enqueued_at") or utcnow().isoformat(),
        )


_redis: Optional[aioredis.Redis] = None


def get_redis() -> aioredis.Redis:
    """Return cached async Redis client (lazy)."""
    global _redis
    if _redis is None:
        settings = get_settings()
        _redis = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis


async def close_redis() -> None:
    """Close cached Redis client (for shutdown)."""
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


async def enqueue_message(message: QueueMessage) -> str:
    """Enqueue a message and return its dedupe id.

    If a message with the same dedupe id is already pending, this is a
    no-op (returns the existing id) so retries are idempotent.
    """
    r = get_redis()
    dedupe_key = f"kman:dedupe:{message.dedupe_id}"
    # SET NX with TTL — atomic check-and-claim
    claimed = await r.set(dedupe_key, "1", nx=True, ex=60 * 60 * 24)
    if not claimed:
        return message.dedupe_id
    await r.lpush(message.queue, message.to_json())
    return message.dedupe_id


async def dequeue_message(
    queue: str,
    *,
    timeout: int = 5,
) -> Optional[QueueMessage]:
    """Block-pop a single message from the queue.

    Returns ``None`` on timeout.
    """
    r = get_redis()
    raw = await r.brpop(queue, timeout=timeout)
    if raw is None:
        return None
    _, body = raw
    return QueueMessage.from_json(queue, body)


async def publish(channel: str, payload: Dict[str, Any]) -> int:
    """Publish a pub/sub message. Returns subscriber count."""
    r = get_redis()
    return await r.publish(channel, json.dumps(payload, default=str))


HandlerFn = Callable[[QueueMessage], Awaitable[None]]


async def consume(
    queue: str,
    handler: HandlerFn,
    *,
    stop_event: Optional[Any] = None,
) -> None:
    """Continuously consume ``queue`` and dispatch to ``handler``.

    On exception, the message is re-enqueued (with the same dedupe id)
    after a short backoff, so a transient error does not lose work.
    """
    import asyncio

    while stop_event is None or not stop_event.is_set():
        try:
            msg = await dequeue_message(queue, timeout=2)
        except Exception:
            await asyncio.sleep(1.0)
            continue
        if msg is None:
            continue
        try:
            await handler(msg)
        except Exception as exc:  # noqa: BLE001
            import logging
            logging.getLogger(queue).exception("handler failed: %s", exc)
            # Re-enqueue for retry
            await enqueue_message(msg)
            await asyncio.sleep(2.0)
