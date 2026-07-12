from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.db.models import AssetType, ResearchStatus


class ResearchRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20, description="Ticker, e.g. AAPL or BTC.")
    asset_type: AssetType = AssetType.STOCK


class ResearchReportRead(BaseModel):
    id: int
    symbol: str
    asset_type: AssetType
    status: ResearchStatus
    model: str
    report_markdown: Optional[str] = None
    sections: Optional[list[dict[str, Any]]] = None
    error: Optional[str] = None
    input_tokens: int
    output_tokens: int
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ResearchReportSummary(BaseModel):
    """List view without the full report body."""

    id: int
    symbol: str
    asset_type: AssetType
    status: ResearchStatus
    model: str
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
