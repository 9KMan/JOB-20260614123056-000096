"""Analytics endpoints — RFM, funnel, cohort, anomalies."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body
from pydantic import BaseModel, Field

from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


class RangeDto(BaseModel):
    since: Optional[str] = None
    until: Optional[str] = None


class FunnelDto(BaseModel):
    steps: List[str] = Field(default_factory=lambda: ["paid", "shipped", "delivered"])
    since: Optional[str] = None
    until: Optional[str] = None


class CohortDto(BaseModel):
    cohort_period: str = "month"
    since: Optional[str] = None
    until: Optional[str] = None


class AnomaliesDto(BaseModel):
    series: List[float]
    threshold_sigma: float = 3.0


@router.post("/rfm")
async def rfm(req: RangeDto) -> Dict[str, Any]:
    svc = AnalyticsService()
    try:
        return await svc.compute_rfm(since=req.since, until=req.until)
    finally:
        await svc.aclose()


@router.post("/funnel")
async def funnel(req: FunnelDto) -> List[Dict[str, Any]]:
    svc = AnalyticsService()
    try:
        return await svc.compute_funnel(steps=req.steps, since=req.since, until=req.until)
    finally:
        await svc.aclose()


@router.post("/cohort")
async def cohort(req: CohortDto) -> Dict[str, Any]:
    svc = AnalyticsService()
    try:
        return await svc.compute_cohort(
            cohort_period=req.cohort_period, since=req.since, until=req.until,
        )
    finally:
        await svc.aclose()


@router.post("/anomalies")
async def anomalies(req: AnomaliesDto) -> Dict[str, Any]:
    svc = AnalyticsService()
    try:
        return await svc.compute_anomalies(req.series, req.threshold_sigma)
    finally:
        await svc.aclose()
