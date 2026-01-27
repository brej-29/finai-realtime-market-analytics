from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.db.models import AlertDirection, AlertEventStatus, AssetType


class AlertCreate(BaseModel):
    symbol: str
    asset_type: AssetType
    direction: AlertDirection
    threshold: float


class AlertRead(BaseModel):
    id: int
    symbol: str
    asset_type: AssetType
    direction: AlertDirection
    threshold: float
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AlertEvaluationResult(BaseModel):
    alert_id: int
    triggered: bool
    current_price: float | None = None


class AlertEventRead(BaseModel):
    id: int
    alert_id: int
    symbol: str
    asset_type: AssetType
    direction: AlertDirection
    message: str
    fired_at: datetime
    status: AlertEventStatus
    payload: dict[str, Any] | None = None