"""vLLM adapter — STUB.

vLLM exposes an OpenAI-compatible HTTP server. Once you have a vLLM
endpoint running, point ``VLLM_BASE_URL`` at it and this adapter will
work without business-logic changes.

Migration path:
  1. Stand up vLLM with your model of choice
  2. Set KMAN_AI_PROVIDER=vllm and VLLM_BASE_URL=http://vllm:8000/v1
  3. Restart this service
  4. No code changes required — the same factory and contract apply
"""

from __future__ import annotations

import logging
from typing import List

from .base import (
    AdapterClassifyResponse,
    AdapterExtractResponse,
    AdapterResponse,
    AdapterSummarizeResponse,
    ModelAdapter,
)

logger = logging.getLogger(__name__)


class VllmAdapter(ModelAdapter):
    """vLLM adapter — uses OpenAI-compatible HTTP API.

    For most use cases, you can use the OpenAIAdapter with a custom
    base_url. This class is a thin dedicated wrapper so configuration
    and metrics for self-hosted models are clearly separated.
    """

    name = "vllm"

    def __init__(self, base_url: str = "", model: str = "meta-llama/Llama-3.3-70B-Instruct", api_key: str = "EMPTY"):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        # TODO: instantiate an AsyncOpenAI client pointed at self.base_url
        # from openai import AsyncOpenAI
        # self._client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    async def complete(self, *, system: str, user: str, max_tokens: int = 800, temperature: float = 0.2, json_mode: bool = False) -> AdapterResponse:
        # TODO: implement using the AsyncOpenAI client
        raise NotImplementedError(
            "VllmAdapter is a stub. Set KMAN_AI_PROVIDER=openai with OPENAI_BASE_URL pointing at your vLLM endpoint for now."
        )

    async def classify(self, *, system: str, user: str, labels: List[str]) -> AdapterClassifyResponse:
        raise NotImplementedError("VllmAdapter.classify not yet implemented")

    async def extract(self, *, system: str, user: str, fields: List[str]) -> AdapterExtractResponse:
        raise NotImplementedError("VllmAdapter.extract not yet implemented")

    async def summarize(self, *, system: str, user: str, max_words: int = 120) -> AdapterSummarizeResponse:
        raise NotImplementedError("VllmAdapter.summarize not yet implemented")
