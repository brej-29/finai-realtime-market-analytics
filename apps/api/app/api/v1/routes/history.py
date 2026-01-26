from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.deps import get_market_data_service
from app.db.models import AssetType
from app.schemas.common import HistoryResponse
from app.services.market_data.service import MarketDataService

router = APIRouter()


@router.get("", response_model=HistoryResponse)
async def get_history(
    symbol: str = Query(..., description="Symbol, e.g. AAPL or BTC."),
    asset_type: AssetType = Query(..., description="Asset type: stock or crypto."),
    interval: str = Query("1h", description="Chart interval, e.g. 1min, 5min, 1h."),
    range: str = Query("1d", alias="range", description="Range, e.g. 1d, 5d, 1mo."),
    market_data: MarketDataService = Depends(get_market_data_service),
) -> HistoryResponse:
    bars = await market_data.get_history(
        asset_type=asset_type,
        symbol=symbol,
        interval=interval,
        range_=range,
    )
    return HistoryResponse(symbol=symbol.upper(), asset_type=asset_type, interval=interval, bars=bars)