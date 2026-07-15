from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.db.models import AssetType


class HoldingCreate(BaseModel):
    symbol: str
    asset_type: AssetType
    quantity: float
    average_price: float


class HoldingRead(BaseModel):
    id: int
    symbol: str
    asset_type: AssetType
    quantity: float
    average_price: float
    created_at: datetime

    class Config:
        from_attributes = True


class PortfolioSummary(BaseModel):
    total_cost_basis: float
    total_market_value: float
    total_unrealized_pnl: float
    by_asset_type: dict[AssetType, "PortfolioSummaryByType"]


class PortfolioSummaryByType(BaseModel):
    asset_type: AssetType
    cost_basis: float
    market_value: float
    unrealized_pnl: float
    weight: Optional[float] = None  # percentage of total portfolio


class HoldingDeleteResult(BaseModel):
    success: bool
    deleted_holding_id: Optional[int] = None