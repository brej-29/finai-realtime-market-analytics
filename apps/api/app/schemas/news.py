from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.db.models import AssetType


class SentimentScore(BaseModel):
    score: float  # [-1, 1] VADER compound score
    label: Literal["positive", "neutral", "negative"]
    explanation: str


class NewsArticle(BaseModel):
    title: str
    url: str
    published_at: datetime
    source: str | None = None
    language: str | None = None
    sentiment: SentimentScore


class NewsResponse(BaseModel):
    symbol: str
    asset_type: AssetType
    last_updated: datetime
    items: list[NewsArticle]