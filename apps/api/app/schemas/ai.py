from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.db.models import AssetType


class TechnicalState(BaseModel):
    rsi: float | None = None
    rsi_label: str | None = None
    macd: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None
    macd_label: str | None = None


class ForecastPoint(BaseModel):
    ts: datetime
    value: float
    lower: float
    upper: float


class ForecastSummary(BaseModel):
    direction: Literal["up", "down", "flat"]
    confidence: float | None = None
    horizon_days: int | None = None
    points: list[ForecastPoint]


class AnomalyPoint(BaseModel):
    ts: datetime
    value: float
    score: float
    is_anomaly: bool


class AIInsightsResponse(BaseModel):
    symbol: str
    asset_type: AssetType
    technical_summary: TechnicalState
    forecast_summary: ForecastSummary | None
    anomalies: list[AnomalyPoint]
    disclaimer: str