from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

import pytest

from app.core.config import AppSettings
from app.db.models import AssetType
from app.schemas.news import NewsArticle
from app.services.market_data.cache import InMemoryCache
from app.services.news.gdelt_client import GDELTClient, NewsResult
from app.services.news.sentiment import HeadlineSentimentAnalyzer


class DummyResponse:
    def __init__(self, json_data: Dict[str, Any], status_code: int = 200) -> None:
        self._json_data = json_data
        self.status_code = status_code
        self.text = "dummy"

    def json(self) -> Dict[str, Any]:
        return self._json_data


class DummyAsyncClient:
    def __init__(self, response: DummyResponse) -> None:
        self._response = response

    async def __aenter__(self) -> "DummyAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        return None

    async def get(self, url: str, params: Dict[str, Any] | None = None) -> DummyResponse:
        return self._response


@pytest.mark.asyncio
async def test_gdelt_client_parses_articles(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "articles": [
            {
                "url": "https://example.com/a1",
                "title": "Stock rallies on strong earnings",
                "seendate": "20260127T040000Z",
                "language": "English",
                "domain": "example.com",
            },
            {
                # Non-English article should be skipped.
                "url": "https://example.com/a2",
                "title": "Titre en français",
                "seendate": "20260127T040000Z",
                "language": "French",
                "domain": "example.com",
            },
        ]
    }
    dummy_response = DummyResponse(payload)

    def async_client_factory(*args, **kwargs):  # type: ignore[override]
        return DummyAsyncClient(dummy_response)

    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", async_client_factory)  # type: ignore[arg-type]

    settings = AppSettings()
    cache = InMemoryCache()
    client = GDELTClient(
        base_url="https://api.gdeltproject.org/api/v2/doc/doc",
        cache=cache,
        settings=settings,
    )

    result: NewsResult = await client.get_news(symbol="AAPL", asset_type=AssetType.STOCK)
    assert isinstance(result.items, list)
    assert len(result.items) == 1
    article = result.items[0]
    assert isinstance(article, NewsArticle)
    assert article.title.startswith("Stock rallies")
    assert article.url == "https://example.com/a1"
    assert article.source == "example.com"
    assert article.language == "English"
    assert article.published_at <= datetime.now(timezone.utc)


def test_headline_sentiment_analyzer() -> None:
    analyzer = HeadlineSentimentAnalyzer()
    positive = analyzer.score("Stock surges on record profits and strong demand")
    negative = analyzer.score("Shares plunge after major loss and weak outlook")

    assert positive.score > 0
    assert negative.score < 0
    assert positive.label in {"positive", "neutral", "negative"}
    assert "Positive" in positive.explanation or "Negative" in positive.explanation