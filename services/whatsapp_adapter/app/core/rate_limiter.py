"""Token-bucket rate limiter implemented on Redis.

Uses an atomic Lua script for the check-and-decrement so that
multiple adapter instances see the same limit. Default:
  - 5 tokens per destination (capacity)
  - refills at 0.5 tokens/second (one message every 2s)
"""

from __future__ import annotations

import logging
from typing import Optional

import redis.asyncio as aioredis

from shared.common.config import get_settings
from shared.messaging.queue_contract import get_redis

logger = logging.getLogger(__name__)

# KEYS[1] = bucket key
# ARGV[1] = capacity
# ARGV[2] = refill rate per second
# ARGV[3] = current time (ms)
# Returns: {allowed (0/1), remaining_tokens, retry_after_ms}
_LUA_SCRIPT = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill = tonumber(ARGV[2])
local now_ms = tonumber(ARGV[3])

local data = redis.call('HMGET', key, 'tokens', 'updated')
local tokens = tonumber(data[1])
local updated = tonumber(data[2])
if tokens == nil then
  tokens = capacity
  updated = now_ms
end

local elapsed_ms = math.max(0, now_ms - updated)
local refill_amount = (elapsed_ms / 1000.0) * refill
tokens = math.min(capacity, tokens + refill_amount)

local allowed = 0
local retry_after = 0
if tokens >= 1.0 then
  tokens = tokens - 1.0
  allowed = 1
else
  retry_after = math.ceil((1.0 - tokens) / refill * 1000)
end

redis.call('HMSET', key, 'tokens', tokens, 'updated', now_ms)
redis.call('EXPIRE', key, 3600)
return {allowed, math.floor(tokens), retry_after}
"""


class RateLimiter:
    """Per-destination token-bucket rate limiter."""

    def __init__(
        self,
        capacity: int = 5,
        refill_per_second: float = 0.5,
    ) -> None:
        self.capacity = capacity
        self.refill_per_second = refill_per_second
        self._script_sha: Optional[str] = None

    async def _ensure_loaded(self) -> str:
        r = get_redis()
        if self._script_sha is None:
            self._script_sha = await r.script_load(_LUA_SCRIPT)
        return self._script_sha

    async def acquire(self, key: str) -> tuple[bool, int, int]:
        """Try to consume a token. Returns (allowed, remaining, retry_after_ms)."""
        r = get_redis()
        try:
            sha = await self._ensure_loaded()
            import time
            now_ms = int(time.time() * 1000)
            res = await r.evalsha(
                sha, 1, f"kman:rate:{key}",
                self.capacity, self.refill_per_second, now_ms,
            )
            return bool(int(res[0])), int(res[1]), int(res[2])
        except aioredis.ResponseError as e:
            if "NOSCRIPT" in str(e):
                self._script_sha = None
                return await self.acquire(key)
            raise
        except Exception as exc:  # noqa: BLE001
            # Fail-open on Redis issues — better to deliver than to drop
            logger.warning("rate limiter unavailable, allowing: %s", exc)
            return True, self.capacity, 0


_singleton: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Return the process-wide RateLimiter singleton."""
    global _singleton
    if _singleton is None:
        settings = get_settings()
        capacity = 5
        refill = 0.5
        try:
            capacity = int(getattr(settings, "whatsapp_rate_capacity", 5))
            refill = float(getattr(settings, "whatsapp_rate_refill", 0.5))
        except Exception:  # noqa: BLE001
            pass
        _singleton = RateLimiter(capacity=capacity, refill_per_second=refill)
    return _singleton
