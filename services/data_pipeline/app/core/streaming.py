"""Streaming file readers — never load a whole file into memory."""

from __future__ import annotations

import csv
import json
import os
from typing import Any, AsyncIterator, Dict, Iterator, Optional


def iter_csv_rows(file_path: str) -> Iterator[Dict[str, Any]]:
    """Yield rows from a CSV file as dicts, one at a time."""
    with open(file_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield {k: v for k, v in row.items() if k is not None}


def iter_jsonl(file_path: str) -> Iterator[Dict[str, Any]]:
    """Yield objects from a JSON-Lines file, one at a time."""
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


async def async_iter_chunks(file_path: str, chunk_size_mb: int = 64) -> AsyncIterator[bytes]:
    """Async-iterate over a file in fixed-size byte chunks.

    Useful for streaming large files to/from S3-compatible storage.
    """
    chunk_size = chunk_size_mb * 1024 * 1024
    if not os.path.exists(file_path):
        return
    loop = __import__("asyncio").get_event_loop()
    with open(file_path, "rb") as f:
        while True:
            data = await loop.run_in_executor(None, f.read, chunk_size)
            if not data:
                break
            yield data


def file_size_mb(file_path: str) -> float:
    """Return file size in megabytes."""
    return os.path.getsize(file_path) / (1024 * 1024)
