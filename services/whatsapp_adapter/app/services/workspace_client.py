"""Workspace client — the HTTP client that calls the other developer's webhook.

Uses shared.common.http.ServiceClient (which has a circuit breaker) and
adds HMAC signature headers when a secret is configured.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from typing import Any, Dict, Optional

import httpx

from shared.common.http import ServiceClient
from shared.contracts.whatsapp_contract import (
    WhatsAppDeliveryRequest,
    WhatsAppDeliveryResponse,
)

logger = logging.getLogger(__name__)


class WorkspaceClient:
    """HTTP client for the WhatsApp workspace webhook."""

    def __init__(
        self,
        base_url: str,
        secret: str = "",
        timeout: float = 10.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.secret = secret
        self.timeout = timeout
        self._client: Optional[ServiceClient] = None
        self._raw: Optional[httpx.AsyncClient] = None

    def _service_client(self) -> ServiceClient:
        if self._client is None:
            self._client = ServiceClient(self.base_url, name="whatsapp-workspace", timeout=self.timeout)
        return self._client

    def _sign(self, body: bytes) -> str:
        return hmac.new(self.secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

    async def deliver(self, request: WhatsAppDeliveryRequest) -> WhatsAppDeliveryResponse:
        """POST a delivery request to the workspace webhook."""
        body = json.dumps(request.model_dump(mode="json"), default=str).encode("utf-8")
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self.secret:
            headers["X-KMan-Signature"] = self._sign(body)
        sc = self._service_client()
        # We use the lower-level httpx call here so we can sign the exact body
        if self._raw is None:
            self._raw = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)
        async def _do() -> httpx.Response:
            last_exc: Optional[Exception] = None
            for attempt in range(sc.max_retries):
                try:
                    resp = await self._raw.post("/api/v1/workspace/deliver", content=body, headers=headers)
                    if resp.status_code >= 500 and attempt < sc.max_retries - 1:
                        import asyncio
                        await asyncio.sleep(min(2 ** attempt, 8))
                        continue
                    return resp
                except httpx.HTTPError as e:
                    last_exc = e
                    if attempt < sc.max_retries - 1:
                        import asyncio
                        await asyncio.sleep(min(2 ** attempt, 8))
                        continue
                    raise
            raise RuntimeError(f"unreachable: {last_exc}")
        resp = await sc.breaker.call(_do)
        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After", "5")
            raise RateLimitedError(int(retry_after))
        if resp.status_code >= 500:
            raise WorkspaceUnavailableError(f"workspace returned {resp.status_code}")
        if resp.status_code >= 400:
            raise WorkspaceRejectedError(f"workspace rejected: {resp.status_code} {resp.text}")
        body_resp = resp.json()
        return WhatsAppDeliveryResponse.model_validate(body_resp)

    async def aclose(self) -> None:
        if self._raw is not None:
            await self._raw.aclose()
            self._raw = None
        if self._client is not None:
            await self._client.close()
            self._client = None


class RateLimitedError(RuntimeError):
    """Workspace returned 429."""

    def __init__(self, retry_after_seconds: int = 5) -> None:
        super().__init__(f"rate limited, retry after {retry_after_seconds}s")
        self.retry_after_seconds = retry_after_seconds


class WorkspaceUnavailableError(RuntimeError):
    """Workspace returned 5xx."""


class WorkspaceRejectedError(RuntimeError):
    """Workspace returned 4xx (validation error)."""


_singleton: Optional[WorkspaceClient] = None


def get_workspace_client() -> WorkspaceClient:
    """Return the process-wide WorkspaceClient singleton."""
    global _singleton
    if _singleton is None:
        base_url = os.environ.get("KMAN_WORKSPACE_WEBHOOK_URL", "http://whatsapp-workspace:8000")
        secret = os.environ.get("KMAN_WORKSPACE_WEBHOOK_SECRET", "")
        _singleton = WorkspaceClient(base_url=base_url, secret=secret)
    return _singleton
