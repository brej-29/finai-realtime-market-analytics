from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

from app.core.deps import get_news_client
from app.db.models import AssetType
from app.schemas.news import NewsResponse
from app.services.news.gdelt_client import GDELTClient

router = APIRouter()


@router.get("", response_model=NewsResponse)
async def get_news(
    symbol: str = Query(..., description="Symbol, e.g. AAPL or BTC."),
    asset_type: AssetType = Query(..., description="Asset type: stock or crypto."),
    client: GDELTClient = Depends(get_news_client),
) -> NewsResponse:
    """Return recent news articles and sentiment for the given symbol."""
    result = await client.get_news(symbol=symbol, asset_type=asset_type)
    return NewsResponse(
        symbol=symbol.upper(),
        asset_type=asset_type,
        last_updated=result.fetched_at,
        items=result.items,
    )