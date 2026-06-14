"""Ollama adapter — STUB.

Ollama exposes a /api/generate HTTP endpoint. Wire it in here when
you have a local Ollama instance running.

Migration path:
  1. Run Ollama locally with your model: `ollama run llama3.2`
  2. Set KMAN_AI_PROVIDER=ollama and OLLAMA_BASE_URL=http://localhost:11434
  3. Restart this service
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


class OllamaAdapter(ModelAdapter):
    """Ollama adapter — uses /api/generate."""

    name = "ollama"

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2"):
        self.base_url = base_url.rstrip("/")
        self.model = model
        # TODO: instantiate an httpx.AsyncClient

    async def complete(self, *, system: str, user: str, max_tokens: int = 800, temperature: float = 0.2, json_mode: bool = False) -> AdapterResponse:
        # TODO: POST to {self.base_url}/api/generate with {model, prompt, system, options}
        raise NotImplementedError(
            "OllamaAdapter is a stub. Use OpenAIAdapter with OPENAI_BASE_URL pointing at an OpenAI-compatible Ollama proxy for now."
        )

    async def classify(self, *, system: str, user: str, labels: List[str]) -> AdapterClassifyResponse:
        raise NotImplementedError("OllamaAdapter.classify not yet implemented")

    async def extract(self, *, system: str, user: str, fields: List[str]) -> AdapterExtractResponse:
        raise NotImplementedError("OllamaAdapter.extract not yet implemented")

    async def summarize(self, *, system: str, user: str, max_words: int = 120) -> AdapterSummarizeResponse:
        raise NotImplementedError("OllamaAdapter.summarize not yet implemented")
