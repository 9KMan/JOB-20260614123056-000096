"""Dedupe store — backed by Redis. SETNX with TTL."""

from __future__ import annotations

import logging
from typing import Optional

from shared.messaging.queue_contract import get_redis

logger = logging.getLogger(__name__)


class DedupeStore:
    """Idempotency guard: claim a dedupe_id with a TTL."""

    def __init__(self, default_ttl_seconds: int = 86_400) -> None:
        self.default_ttl = default_ttl_seconds

    async def claim(self, dedupe_id: str, ttl_seconds: Optional[int] = None) -> bool:
        """Return True if newly claimed, False if already claimed."""
        r = get_redis()
        ttl = ttl_seconds or self.default_ttl
        key = f"kman:dedupe:wa:{dedupe_id}"
        result = await r.set(key, "1", nx=True, ex=ttl)
        return bool(result)

    async def release(self, dedupe_id: str) -> None:
        """Explicit release of a previously-claimed dedupe id."""
        r = get_redis()
        await r.delete(f"kman:dedupe:wa:{dedupe_id}")


_singleton: Optional[DedupeStore] = None


def get_dedupe_store() -> DedupeStore:
    """Return the process-wide DedupeStore singleton."""
    global _singleton
    if _singleton is None:
        _singleton = DedupeStore()
    return _singleton
