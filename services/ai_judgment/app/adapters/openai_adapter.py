"""OpenAI adapter — uses openai>=1.0 async SDK."""

from __future__ import annotations

import asyncio
import json
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


class OpenAIAdapter(ModelAdapter):
    """Adapter for OpenAI's hosted models (also works with vLLM OpenAI-compat)."""

    name = "openai"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        timeout: float = 30.0,
        max_retries: int = 3,
        base_url: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_url = base_url
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazy import and instantiate the OpenAI async client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError as e:  # pragma: no cover
                raise RuntimeError("openai package is required for OpenAIAdapter") from e
            kwargs: Dict[str, Any] = {"api_key": self.api_key, "timeout": self.timeout}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = AsyncOpenAI(**kwargs)
        return self._client

    def set_model(self, model: str) -> None:
        """Switch model at runtime."""
        self.model = model

    async def _chat(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int,
        temperature: float,
        json_mode: bool,
    ) -> AdapterResponse:
        """Single chat completion call with retries."""
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY not set for OpenAIAdapter")
        client = self._get_client()
        start = time.monotonic()
        last_exc: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                kwargs: Dict[str, Any] = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                }
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}
                resp = await client.chat.completions.create(**kwargs)
                duration_ms = int((time.monotonic() - start) * 1000)
                content = (resp.choices[0].message.content or "").strip()
                usage = getattr(resp, "usage", None)
                tokens_in = getattr(usage, "prompt_tokens", 0) or 0
                tokens_out = getattr(usage, "completion_tokens", 0) or 0
                parsed = parse_json_output(content) if json_mode else None
                return AdapterResponse(
                    content=content,
                    model=self.model,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    duration_ms=duration_ms,
                    parsed=parsed,
                    raw=None,
                )
            except Exception as e:  # noqa: BLE001
                last_exc = e
                logger.warning("OpenAI call failed (attempt %d): %s", attempt, e)
                if attempt < self.max_retries:
                    await asyncio.sleep(min(2 ** attempt, 8))
        raise RuntimeError(f"OpenAI call failed after {self.max_retries} attempts: {last_exc}")

    async def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 800,
        temperature: float = 0.2,
        json_mode: bool = False,
    ) -> AdapterResponse:
        return await self._chat(
            system=system, user=user, max_tokens=max_tokens,
            temperature=temperature, json_mode=json_mode,
        )

    async def classify(
        self, *, system: str, user: str, labels: List[str]
    ) -> AdapterClassifyResponse:
        # Reinforce the label set in the system prompt — defensive.
        labels_csv = ", ".join(labels)
        system = f"{system}\nAllowed labels: {labels_csv}\nRespond with JSON: {{\"label\": <one of the allowed labels>, \"confidence\": <float 0..1>}}"
        resp = await self._chat(
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
            content=resp.content,
            model=resp.model,
            tokens_in=resp.tokens_in,
            tokens_out=resp.tokens_out,
            duration_ms=resp.duration_ms,
            parsed=parsed,
            label=label,
            confidence=confidence,
        )

    async def extract(
        self, *, system: str, user: str, fields: List[str]
    ) -> AdapterExtractResponse:
        fields_csv = ", ".join(fields)
        system = f"{system}\nExtract these fields: {fields_csv}.\nRespond with JSON: {{<field>: <value>, ...}}"
        resp = await self._chat(
            system=system, user=user, max_tokens=600, temperature=0.0, json_mode=True
        )
        parsed = resp.parsed or {}
        # Defensive: only return requested fields
        extracted = {f: parsed.get(f) for f in fields}
        return AdapterExtractResponse(
            content=resp.content,
            model=resp.model,
            tokens_in=resp.tokens_in,
            tokens_out=resp.tokens_out,
            duration_ms=resp.duration_ms,
            parsed=parsed,
            extracted=extracted,
        )

    async def summarize(
        self, *, system: str, user: str, max_words: int = 120
    ) -> AdapterSummarizeResponse:
        system = f"{system}\nKeep the summary under {max_words} words."
        resp = await self._chat(
            system=system, user=user, max_tokens=400, temperature=0.3, json_mode=False
        )
        return AdapterSummarizeResponse(
            content=resp.content,
            model=resp.model,
            tokens_in=resp.tokens_in,
            tokens_out=resp.tokens_out,
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
