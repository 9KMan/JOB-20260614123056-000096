"""Adapter layer — abstracts over hosted and self-hosted AI providers.

This is the key seam for the "hosted → self-hosted" migration path.
All business logic in this service uses ``get_adapter()`` and never
touches a provider SDK directly.
"""

from .base import (
    ModelAdapter,
    AdapterResponse,
    AdapterClassifyResponse,
    AdapterExtractResponse,
    AdapterSummarizeResponse,
)
from .factory import get_adapter

__all__ = [
    "ModelAdapter",
    "AdapterResponse",
    "AdapterClassifyResponse",
    "AdapterExtractResponse",
    "AdapterSummarizeResponse",
    "get_adapter",
]
