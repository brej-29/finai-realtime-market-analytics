from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.db.models import AssetType


class WatchlistCreate(BaseModel):
    name: str


class WatchlistItemCreate(BaseModel):
    symbol: str
    asset_type: AssetType


class WatchlistItemRead(BaseModel):
    id: int
    symbol: str
    asset_type: AssetType
    created_at: datetime

    class Config:
        from_attributes = True


class WatchlistRead(BaseModel):
    id: int
    name: str
    created_at: datetime
    items: list[WatchlistItemRead] = []

    class Config:
        from_attributes = True


class WatchlistItemDeleteResult(BaseModel):
    success: bool
    deleted_item_id: Optional[int] = None