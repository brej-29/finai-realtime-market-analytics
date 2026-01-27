from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Sequence, Tuple

import httpx

from app.core.config import AppSettings
from app.core.logging import get_logger
from app.db.models import AssetType
from app.schemas.news import NewsArticle, SentimentScore
from app.services.market_data.cache import InMemoryCache
from app.services.news.sentiment import HeadlineSentimentAnalyzer

logger = get_logger("app.services.news.gdelt")


@dataclass
class NewsResult:
    items: List[NewsArticle]
    fetched_at: datetime


def _score_headline(self, title: str) -> SentimentScore:
        return self._sentiment.score(title)


class GDELTClient:
    """Lightweight client for the GDELT Doc 2.0 API.

    This client is intentionally conservative:
    - No API key is required.
    - Requests are cached per (symbol, asset_type) with a configurable TTL.
    """

    def __init__(
        self,
        base_url: str,
        cache: InMemoryCache,
        settings: AppSettings,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.cache = cache
        self.settings = settings
        self._sentiment = HeadlineSentimentAnalyzer()

    def _cache_key(self, symbol: str, asset_type: AssetType) -> Tuple[str, str, str]:
        return ("gdelt", symbol.upper(), asset_type.value)

    async def get_news(self, symbol: str, asset_type: AssetType) -> NewsResult:
        symbol = symbol.upper()
        cache_key = self._cache_key(symbol, asset_type)
        cached = self.cache.get(cache_key)
        if cached is not None:
            result, is_stale = cached
            if isinstance(result, NewsResult) and not is_stale:
                return result

        items = await self._fetch_from_gdelt(symbol, asset_type)
        result = NewsResult(items=items, fetched_at=datetime.now(timezone.utc))
        self.cache.set(cache_key, result, ttl_seconds=self.settings.news_ttl_seconds)
        return result

    async def _fetch_from_gdelt(
        self,
        symbol: str,
        asset_type: AssetType,
    ) -> List[NewsArticle]:
        # Query the last few hours of news mentioning the symbol.
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=8)

        start_str = start.strftime("%Y%m%d%H%M%S")
        end_str = end.strftime("%Y%m%d%H%M%S")

        # Basic keyword search; for equities this will often be the ticker.
        query = symbol

        params = {
            "query": query,
            "mode": "ArtList",
            "format": "json",
            "maxrecords": "20",
            "sort": "DateDesc",
            "startdatetime": start_str,
            "enddatetime": end_str,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.base_url, params=params)
        except httpx.HTTPError as exc:
            logger.warning(
                "GDELT request failed",
                extra={"symbol": symbol, "asset_type": asset_type.value, "error": str(exc)},
            )
            return []

        if response.status_code != 200:
            logger.warning(
                "GDELT non-200 response",
                extra={
                    "status_code": response.status_code,
                    "body": response.text[:200],
                    "symbol": symbol,
                },
            )
            return []

        try:
            data = response.json()
        except ValueError as exc:
            logger.warning(
                "GDELT returned non-JSON payload",
                extra={"symbol": symbol, "error": str(exc)},
            )
            return []

        articles = data.get("articles")
        if not isinstance(articles, Sequence):
            return []

        results: List[NewsArticle] = []
        for raw in articles:
            if not isinstance(raw, dict):
                continue

            title = str(raw.get("title") or "").strip()
            url = str(raw.get("url") or "").strip()
            if not title or not url:
                continue

            language = str(raw.get("language") or "")
            if language and language.lower() != "english":
                # Restrict to English for VADER-based sentiment.
                continue

            seendate = str(raw.get("seendate") or "")
            published_at = _parse_seendate(seendate)

            sentiment = self._score_headline(title)
            results.append(
                NewsArticle(
                    title=title,
                    url=url,
                    published_at=published_at,
                    source=raw.get("domain") or None,
                    language=language or None,
                    sentiment=sentiment,
                )
            )

        return results


def _parse_seendate(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)