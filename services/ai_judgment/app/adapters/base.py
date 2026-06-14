"""Abstract ModelAdapter interface.

All concrete adapters (OpenAI, Anthropic, vLLM, Ollama) implement this
interface. Business code never depends on a specific provider.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AdapterResponse:
    """Generic response from a model adapter."""

    content: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    duration_ms: int = 0
    parsed: Optional[Dict[str, Any]] = None
    raw: Optional[Dict[str, Any]] = field(default=None, repr=False)


@dataclass
class AdapterClassifyResponse(AdapterResponse):
    label: str = ""
    confidence: float = 0.0


@dataclass
class AdapterExtractResponse(AdapterResponse):
    extracted: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AdapterSummarizeResponse(AdapterResponse):
    summary: str = ""


class ModelAdapter(ABC):
    """Abstract base for all model adapters.

    Implementations:
    - OpenAIAdapter: uses openai>=1.0 SDK
    - AnthropicAdapter: uses anthropic>=0.30 SDK
    - VllmAdapter: stub (OpenAI-compatible HTTP, not yet wired)
    - OllamaAdapter: stub (Ollama HTTP, not yet wired)
    """

    name: str = "abstract"

    @abstractmethod
    async def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 800,
        temperature: float = 0.2,
        json_mode: bool = False,
    ) -> AdapterResponse:
        """Generic completion call."""
        raise NotImplementedError

    @abstractmethod
    async def classify(
        self,
        *,
        system: str,
        user: str,
        labels: List[str],
    ) -> AdapterClassifyResponse:
        """Classification: returns label + confidence in [0, 1]."""
        raise NotImplementedError

    @abstractmethod
    async def extract(
        self,
        *,
        system: str,
        user: str,
        fields: List[str],
    ) -> AdapterExtractResponse:
        """Extraction: returns a dict of field -> value."""
        raise NotImplementedError

    @abstractmethod
    async def summarize(
        self,
        *,
        system: str,
        user: str,
        max_words: int = 120,
    ) -> AdapterSummarizeResponse:
        """Summarization: returns a short summary string."""
        raise NotImplementedError

    async def aclose(self) -> None:  # noqa: D401
        """Optional cleanup hook for adapters that own an HTTP client."""
        return None
