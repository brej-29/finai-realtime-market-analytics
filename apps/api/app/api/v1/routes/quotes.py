from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Query

from app.core.deps import get_market_data_service
from app.db.models import AssetType
from app.schemas.common import QuotesResponse
from app.services.market_data.service import MarketDataService

router = APIRouter()


@router.get("", response_model=QuotesResponse)
async def get_quotes(
    symbols: List[str] = Query(..., description="List of symbols, e.g. AAPL,MSFT or BTC,ETH."),
    asset_type: AssetType = Query(..., description="Asset type: stock or crypto."),
    market_data: MarketDataService = Depends(get_market_data_service),
) -> QuotesResponse:
    quotes = await market_data.get_quotes(asset_type=asset_type, symbols=symbols)
    return QuotesResponse(quotes=quotes)