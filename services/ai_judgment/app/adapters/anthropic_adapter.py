"""Anthropic adapter — uses anthropic>=0.30 async SDK."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, Dict, List, Optional

from .base import (
    AdapterClassifyResponse,
    AdapterExtractResponse,
    AdapterResponse,
    AdapterSummarizeResponse,
    ModelAdapter,
)
from app.core.parsers import parse_json_output

logger = logging.getLogger(__name__)


class AnthropicAdapter(ModelAdapter):
    """Adapter for Anthropic's Claude hosted models."""

    name = "anthropic"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-5-sonnet-20241022",
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from anthropic import AsyncAnthropic
            except ImportError as e:  # pragma: no cover
                raise RuntimeError("anthropic package is required for AnthropicAdapter") from e
            self._client = AsyncAnthropic(api_key=self.api_key, timeout=self.timeout)
        return self._client

    def set_model(self, model: str) -> None:
        self.model = model

    async def _messages(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int,
        temperature: float,
        json_mode: bool,
    ) -> AdapterResponse:
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set for AnthropicAdapter")
        client = self._get_client()
        start = time.monotonic()
        last_exc: Optional[Exception] = None
        # Anthropic system prompt is a top-level field
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = await client.messages.create(**kwargs)
                duration_ms = int((time.monotonic() - start) * 1000)
                # Extract text content from response.content blocks
                content = ""
                for block in getattr(resp, "content", []):
                    if getattr(block, "type", "") == "text":
                        content = getattr(block, "text", "")
                        break
                usage = getattr(resp, "usage", None)
                tokens_in = getattr(usage, "input_tokens", 0) or 0
                tokens_out = getattr(usage, "output_tokens", 0) or 0
                parsed = parse_json_output(content) if json_mode else None
                return AdapterResponse(
                    content=content,
                    model=self.model,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    duration_ms=duration_ms,
                    parsed=parsed,
                )
            except Exception as e:  # noqa: BLE001
                last_exc = e
                logger.warning("Anthropic call failed (attempt %d): %s", attempt, e)
                if attempt < self.max_retries:
                    await asyncio.sleep(min(2 ** attempt, 8))
        raise RuntimeError(f"Anthropic call failed after {self.max_retries} attempts: {last_exc}")

    async def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 800,
        temperature: float = 0.2,
        json_mode: bool = False,
    ) -> AdapterResponse:
        return await self._messages(
            system=system, user=user, max_tokens=max_tokens,
            temperature=temperature, json_mode=json_mode,
        )

    async def classify(
        self, *, system: str, user: str, labels: List[str]
    ) -> AdapterClassifyResponse:
        labels_csv = ", ".join(labels)
        system = f"{system}\nAllowed labels: {labels_csv}.\nRespond with JSON only: {{\"label\": <one of the allowed labels>, \"confidence\": <float 0..1>}}"
        resp = await self._messages(
            system=system, user=user, max_tokens=200, temperature=0.0, json_mode=True
        )
        parsed = resp.parsed or {}
        label = str(parsed.get("label", "")).strip()
        if label not in labels:
            label = labels[0] if labels else ""
        try:
            confidence = float(parsed.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        return AdapterClassifyResponse(
            content=resp.content, model=resp.model,
            tokens_in=resp.tokens_in, tokens_out=resp.tokens_out,
            duration_ms=resp.duration_ms, parsed=parsed,
            label=label, confidence=confidence,
        )

    async def extract(
        self, *, system: str, user: str, fields: List[str]
    ) -> AdapterExtractResponse:
        fields_csv = ", ".join(fields)
        system = f"{system}\nExtract these fields: {fields_csv}.\nRespond with JSON only."
        resp = await self._messages(
            system=system, user=user, max_tokens=600, temperature=0.0, json_mode=True
        )
        parsed = resp.parsed or {}
        extracted = {f: parsed.get(f) for f in fields}
        return AdapterExtractResponse(
            content=resp.content, model=resp.model,
            tokens_in=resp.tokens_in, tokens_out=resp.tokens_out,
            duration_ms=resp.duration_ms, parsed=parsed,
            extracted=extracted,
        )

    async def summarize(
        self, *, system: str, user: str, max_words: int = 120
    ) -> AdapterSummarizeResponse:
        system = f"{system}\nKeep the summary under {max_words} words."
        resp = await self._messages(
            system=system, user=user, max_tokens=400, temperature=0.3, json_mode=False
        )
        return AdapterSummarizeResponse(
            content=resp.content, model=resp.model,
            tokens_in=resp.tokens_in, tokens_out=resp.tokens_out,
            duration_ms=resp.duration_ms,
            summary=resp.content.strip(),
        )

    async def aclose(self) -> None:
        if self._client is not None:
            try:
                await self._client.close()
            except Exception:  # noqa: BLE001
                pass
            self._client = None
