"""Pydantic I/O DTOs for the Automation Engine API."""

from __future__ import annotations

from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

from shared.common.time import utcnow

T = TypeVar("T")


class ListResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    next_offset: Optional[int] = None
    generated_at: str = Field(default_factory=lambda: utcnow().isoformat())


class HealthDto(BaseModel):
    status: str = "ok"
    service: str = "automation-engine"
    version: str = "0.1.0"
    timestamp: str = Field(default_factory=lambda: utcnow().isoformat())


class ScheduleInfoDto(BaseModel):
    name: str
    interval_seconds: int
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None
    enabled: bool = True
