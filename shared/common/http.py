"""HTTP client with retries, circuit breaker, and correlation IDs.

Used by services that call each other over REST. The same client
underpins the WhatsApp adapter.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, Optional

import httpx

from shared.common.config import get_settings
from shared.common.ids import new_correlation_id

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    """Simple circuit breaker.

    After ``failure_threshold`` consecutive failures, the circuit opens
    and fast-fails for ``reset_timeout`` seconds. After reset, a single
    trial call moves the circuit to half-open; success closes it,
    failure re-opens.
    """

    failure_threshold: int = 5
    reset_timeout: float = 60.0
    _failures: int = 0
    _state: CircuitState = CircuitState.CLOSED
    _opened_at: float = 0.0
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def call(self, fn: Callable[[], Awaitable[Any]]) -> Any:
        """Invoke ``fn`` under the breaker."""
        async with self._lock:
            if self._state is CircuitState.OPEN:
                if time.monotonic() - self._opened_at >= self.reset_timeout:
                    self._state = CircuitState.HALF_OPEN
                else:
                    raise CircuitOpenError("circuit breaker is open")
        try:
            result = await fn()
        except Exception as e:
            await self._on_failure()
            raise
        else:
            await self._on_success()
            return result

    async def _on_failure(self) -> None:
        async with self._lock:
            self._failures += 1
            if self._failures >= self.failure_threshold:
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()
                logger.warning("circuit breaker opened after %d failures", self._failures)

    async def _on_success(self) -> None:
        async with self._lock:
            self._failures = 0
            if self._state is CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED
                logger.info("circuit breaker closed after recovery")

    @property
    def state(self) -> CircuitState:
        return self._state


class CircuitOpenError(RuntimeError):
    pass


class ServiceClient:
    """Async HTTP client with retries and a circuit breaker.

    Each remote service should have one client instance — the breaker
    protects the whole service, not individual endpoints.
    """

    def __init__(
        self,
        base_url: str,
        name: str = "remote",
        timeout: float = 10.0,
        max_retries: int = 3,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.name = name
        self.timeout = timeout
        self.max_retries = max_retries
        self.breaker = CircuitBreaker()
        self._client: Optional[httpx.AsyncClient] = None

    async def _ensure(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """Make an HTTP request with retries and circuit breaker."""
        url = path if path.startswith("/") else f"/{path}"
        full_headers = {
            "X-Correlation-Id": new_correlation_id(),
            "X-Client": "kman-automation",
            "Content-Type": "application/json",
        }
        if headers:
            full_headers.update(headers)
        client = await self._ensure()

        async def _do() -> httpx.Response:
            last_exc: Optional[Exception] = None
            for attempt in range(1, self.max_retries + 1):
                try:
                    resp = await client.request(
                        method,
                        url,
                        json=json,
                        params=params,
                        headers=full_headers,
                    )
                    if resp.status_code >= 500 and attempt < self.max_retries:
                        await asyncio.sleep(min(2 ** attempt, 8))
                        continue
                    return resp
                except httpx.HTTPError as e:
                    last_exc = e
                    if attempt < self.max_retries:
                        await asyncio.sleep(min(2 ** attempt, 8))
                        continue
                    raise
            raise RuntimeError(f"unreachable: {last_exc}")

        return await self.breaker.call(_do)


def get_default_timeout() -> float:
    settings = get_settings()
    return float(settings.ai_request_timeout_seconds)
