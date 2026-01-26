from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict

import pytest

from app.core.errors import ProviderError
from app.db.models import AssetType
from app.schemas.common import Quote
from app.services.market_data.cache import InMemoryCache
from app.services.market_data.providers import CoinGeckoProvider, TwelveDataProvider
from app.services.market_data.rate_limiter import RateLimitGuard


class DummyResponse:
    def __init__(self, json_data: Dict[str, Any], status_code: int = 200) -> None:
        self._json_data = json_data
        self.status_code = status_code
        self.text = json.dumps(json_data)

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
async def test_twelvedata_provider_parses_quote(monkeypatch: pytest.MonkeyPatch) -> None:
    response_payload = {
        "AAPL": {
            "symbol": "AAPL",
            "price": "150.0",
            "percent_change": "1.5",
        }
    }
    dummy_response = DummyResponse(response_payload)

    def async_client_factory(*args, **kwargs):  # type: ignore[override]
        return DummyAsyncClient(dummy_response)

    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", async_client_factory)  # type: ignore[arg-type]

    cache = InMemoryCache()
    guard = RateLimitGuard(capacity=10, refill_per_second=10.0)
    provider = TwelveDataProvider(
        api_key="dummy",
        base_url="https://api.twelvedata.com",
        rate_limit_guard=guard,
        cache=cache,
    )

    quotes = await provider.get_quotes(["AAPL"])
    assert len(quotes) == 1
    quote = quotes[0]
    assert isinstance(quote, Quote)
    assert quote.symbol == "AAPL"
    assert quote.asset_type is AssetType.STOCK
    assert quote.price == 150.0
    assert quote.change_24h == 1.5
    assert quote.ts <= datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_coingecko_provider_parses_quote(monkeypatch: pytest.MonkeyPatch) -> None:
    response_payload = {"bitcoin": {"usd": 30000.0, "usd_24h_change": 2.0}}
    dummy_response = DummyResponse(response_payload)

    def async_client_factory(*args, **kwargs):  # type: ignore[override]
        return DummyAsyncClient(dummy_response)

    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", async_client_factory)  # type: ignore[arg-type]

    cache = InMemoryCache()
    guard = RateLimitGuard(capacity=10, refill_per_second=10.0)
    provider = CoinGeckoProvider(
        base_url="https://api.coingecko.com/api/v3",
        rate_limit_guard=guard,
        cache=cache,
    )

    quotes = await provider.get_quotes(["bitcoin"])
    assert len(quotes) == 1
    quote = quotes[0]
    assert quote.symbol == "BITCOIN"
    assert quote.asset_type is AssetType.CRYPTO
    assert quote.price == 30000.0
    assert quote.change_24h == 2.0


@pytest.mark.asyncio
async def test_twelvedata_provider_requires_api_key() -> None:
    cache = InMemoryCache()
    guard = RateLimitGuard(capacity=10, refill_per_second=10.0)
    provider = TwelveDataProvider(
        api_key=None,
        base_url="https://api.twelvedata.com",
        rate_limit_guard=guard,
        cache=cache,
    )

    with pytest.raises(ProviderError):
        await provider.get_quotes(["AAPL"])