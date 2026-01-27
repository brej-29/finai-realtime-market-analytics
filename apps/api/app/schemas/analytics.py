from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.db.models import AssetType


class ReturnPoint(BaseModel):
    ts: datetime
    value: float
    return_pct: float | None = None


class PortfolioAnalyticsResponse(BaseModel):
    volatility: float
    max_drawdown: float
    sharpe_ratio: float | None
    daily_returns: list[ReturnPoint]


class BenchmarkAnalyticsResponse(BaseModel):
    symbol: str
    asset_type: AssetType
    volatility: float
    max_drawdown: float
    sharpe_ratio: float | None
    daily_returns: list[ReturnPoint]