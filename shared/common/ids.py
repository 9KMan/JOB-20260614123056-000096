"""ID generation helpers."""

from __future__ import annotations

import uuid


def new_uuid() -> str:
    """Return a new UUID4 string."""
    return str(uuid.uuid4())


def new_correlation_id() -> str:
    """Return a short correlation ID for tracing requests across services."""
    return uuid.uuid4().hex[:16]
