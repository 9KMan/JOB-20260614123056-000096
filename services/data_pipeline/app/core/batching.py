"""Batching utilities — partition iterables into fixed-size chunks."""

from __future__ import annotations

import asyncio
import time
from typing import AsyncIterator, Iterator, List, Optional, TypeVar

T = TypeVar("T")


def chunked(iterable, size: int) -> Iterator[list]:
    """Split an iterable into lists of at most ``size`` items each."""
    if size <= 0:
        raise ValueError("size must be positive")
    chunk: list = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) >= size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


class BatchAccumulator:
    """Accumulates items up to ``max_size`` or until ``max_age_seconds`` elapses.

    After either condition is met, ``flush()`` returns the accumulated batch.
    """

    def __init__(self, max_size: int = 1000, max_age_seconds: float = 5.0) -> None:
        self.max_size = max_size
        self.max_age_seconds = max_age_seconds
        self._items: list = []
        self._opened_at: Optional[float] = None

    def add(self, item) -> None:
        if self._opened_at is None:
            self._opened_at = time.monotonic()
        self._items.append(item)

    def is_ready(self) -> bool:
        if not self._items:
            return False
        if len(self._items) >= self.max_size:
            return True
        if self._opened_at and (time.monotonic() - self._opened_at) >= self.max_age_seconds:
            return True
        return False

    def flush(self) -> list:
        items = self._items
        self._items = []
        self._opened_at = None
        return items

    def __len__(self) -> int:
        return len(self._items)
