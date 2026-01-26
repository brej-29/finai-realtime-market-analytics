from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.db.models import AlertDirection, AssetType


class Quote(BaseModel):
    symbol: str
    asset_type: AssetType
    price: float
    change_24h: Optional[float] = Field(
        default=None,
        description="24h percent change, when available from provider.",
    )
    ts: datetime
    is_stale: bool = Field(
        default=False,
        description="True if the quote came from cache and may be stale.",
    )


class HistoricalBar(BaseModel):
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None


class QuotesResponse(BaseModel):
    quotes: list[Quote]


class HistoryResponse(BaseModel):
    symbol: str
    asset_type: AssetType
    interval: str
    bars: list[HistoricalBar]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    message: str = "healthy"
    timestamp: datetime


__all__ = [
    "AssetType",
    "AlertDirection",
    "Quote",
    "HistoricalBar",
    "QuotesResponse",
    "HistoryResponse",
    "HealthResponse",
]