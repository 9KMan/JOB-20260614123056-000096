"""Adapter factory.

Picks the right ModelAdapter based on environment variables. The
business code in this service calls ``get_adapter()`` and never sees
the underlying provider.
"""

from __future__ import annotations

import logging
import os
from threading import Lock
from typing import Optional

from .base import ModelAdapter

logger = logging.getLogger(__name__)

_PROVIDER_ENV = "KMAN_AI_PROVIDER"

_cached: Optional[ModelAdapter] = None
_lock = Lock()


def get_adapter() -> ModelAdapter:
    """Return the singleton adapter for the current provider."""
    global _cached
    if _cached is not None:
        return _cached
    with _lock:
        if _cached is not None:
            return _cached
        provider = (os.environ.get(_PROVIDER_ENV) or "openai").lower()
        if provider == "openai":
            from .openai_adapter import OpenAIAdapter
            model = os.environ.get("KMAN_AI_MODEL") or os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"
            _cached = OpenAIAdapter(model=model)
        elif provider == "anthropic":
            from .anthropic_adapter import AnthropicAdapter
            model = os.environ.get("KMAN_AI_MODEL") or "claude-3-5-sonnet-20241022"
            _cached = AnthropicAdapter(model=model)
        elif provider == "vllm":
            from .vllm_adapter import VllmAdapter
            _cached = VllmAdapter(
                base_url=os.environ.get("VLLM_BASE_URL", ""),
                model=os.environ.get("KMAN_AI_MODEL", "meta-llama/Llama-3.3-70B-Instruct"),
            )
        elif provider == "ollama":
            from .ollama_adapter import OllamaAdapter
            _cached = OllamaAdapter(
                base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
                model=os.environ.get("KMAN_AI_MODEL", "llama3.2"),
            )
        else:
            raise ValueError(f"Unknown KMAN_AI_PROVIDER: {provider}")
        logger.info("AI adapter initialized: %s", _cached.name)
        return _cached


def reset_adapter() -> None:
    """Reset the cached adapter (useful for tests)."""
    global _cached
    with _lock:
        if _cached is not None:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(_cached.aclose())
                else:
                    loop.run_until_complete(_cached.aclose())
            except Exception:  # noqa: BLE001
                pass
        _cached = None
