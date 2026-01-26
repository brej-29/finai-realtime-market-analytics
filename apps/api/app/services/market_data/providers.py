from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Mapping, Sequence

import httpx

from app.core.errors import ProviderError
from app.core.logging import get_logger
from app.db.models import AssetType
from app.schemas.common import HistoricalBar, Quote
from app.services.market_data.base import MarketDataProvider, SupportsAssetType
from app.services.market_data.cache import InMemoryCache
from app.services.market_data.rate_limiter import RateLimitGuard

logger = get_logger("app.services.market_data")


class TwelveDataProvider(MarketDataProvider, SupportsAssetType):
    """Market data provider for stock quotes and OHLC using Twelve Data."""

    asset_type = AssetType.STOCK

    def __init__(
        self,
        api_key: str | None,
        base_url: str,
        rate_limit_guard: RateLimitGuard,
        cache: InMemoryCache,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.rate_limit_guard = rate_limit_guard
        self.cache = cache

    async def get_quotes(self, symbols: Iterable[str]) -> list[Quote]:
        symbol_list = list(symbols)
        if not symbol_list:
            return []

        if not self.api_key:
            raise ProviderError("Twelve Data API key is not configured.")

        self.rate_limit_guard.acquire()
        params: dict[str, str] = {
            "symbol": ",".join(symbol_list),
            "apikey": self.api_key,
        }
        url = f"{self.base_url}/quote"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
        except httpx.HTTPError as exc:
            logger.warning("Twelve Data request failed", extra={"error": str(exc)})
            raise ProviderError("Error calling Twelve Data.") from exc

        if response.status_code != 200:
            logger.warning(
                "Twelve Data non-200 response",
                extra={"status_code": response.status_code, "body": response.text[:200]},
            )
            raise ProviderError("Twelve Data returned an error response.")

        data = response.json()

        quotes: list[Quote] = []
        # Twelve Data returns a single object or a dict of objects depending on symbols
        items: list[tuple[str, dict]] = []
        if isinstance(data, dict) and "symbol" in data:
            items = [(data["symbol"], data)]
        elif isinstance(data, dict):
            items = [(k, v) for k, v in data.items() if isinstance(v, dict)]

        now = datetime.now(timezone.utc)
        for symbol, payload in items:
            try:
                price = float(payload["price"])
                change_pct = float(payload.get("percent_change", 0.0))
            except (KeyError, ValueError, TypeError) as exc:
                logger.warning(
                    "Malformed Twelve Data quote",
                    extra={"symbol": symbol, "payload": payload},
                )
                raise ProviderError(f"Malformed quote for symbol {symbol}") from exc

            quotes.append(
                Quote(
                    symbol=symbol.upper(),
                    asset_type=AssetType.STOCK,
                    price=price,
                    change_24h=change_pct,
                    ts=now,
                    is_stale=False,
                )
            )

        return quotes

    async def get_history(
        self,
        symbol: str,
        interval: str,
        range_: str,
    ) -> list[HistoricalBar]:
        if not self.api_key:
            raise ProviderError("Twelve Data API key is not configured.")

        self.rate_limit_guard.acquire()

        # Twelve Data uses outputsize / start_date / end_date; for simplicity, map range_ to outputsize
        outputsize = {
            "1d": 96,
            "5d": 5 * 96,
            "1mo": 30 * 96,
        }.get(range_, 100)

        params: dict[str, str] = {
            "symbol": symbol,
            "interval": interval,
            "outputsize": str(outputsize),
            "apikey": self.api_key,
        }
        url = f"{self.base_url}/time_series"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
        except httpx.HTTPError as exc:
            logger.warning("Twelve Data history request failed", extra={"error": str(exc)})
            raise ProviderError("Error calling Twelve Data for history.") from exc

        if response.status_code != 200:
            logger.warning(
                "Twelve Data history non-200 response",
                extra={"status_code": response.status_code, "body": response.text[:200]},
            )
            raise ProviderError("Twelve Data returned an error response for history.")

        data = response.json()
        values = data.get("values")
        if not isinstance(values, list):
            raise ProviderError("Unexpected Twelve Data history format.")

        bars: list[HistoricalBar] = []
        for item in reversed(values):
            try:
                ts = datetime.fromisoformat(item["datetime"]).replace(tzinfo=timezone.utc)
                bars.append(
                    HistoricalBar(
                        ts=ts,
                        open=float(item["open"]),
                        high=float(item["high"]),
                        low=float(item["low"]),
                        close=float(item["close"]),
                        volume=float(item.get("volume") or 0.0),
                    )
                )
            except (KeyError, ValueError, TypeError) as exc:
                logger.warning(
                    "Malformed Twelve Data history item",
                    extra={"symbol": symbol, "item": item},
                )
                raise ProviderError(f"Malformed history for symbol {symbol}") from exc

        return bars


class CoinGeckoProvider(MarketDataProvider, SupportsAssetType):
    """Market data provider for crypto quotes and charts using CoinGecko."""

    asset_type = AssetType.CRYPTO

    def __init__(
        self,
        base_url: str,
        rate_limit_guard: RateLimitGuard,
        cache: InMemoryCache,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.rate_limit_guard = rate_limit_guard
        self.cache = cache

    async def get_quotes(self, symbols: Iterable[str]) -> list[Quote]:
        symbol_list = [s.lower() for s in symbols]
        if not symbol_list:
            return []

        self.rate_limit_guard.acquire()

        ids = ",".join(symbol_list)
        params: dict[str, str] = {
            "ids": ids,
            "vs_currencies": "usd",
            "include_24hr_change": "true",
        }
        url = f"{self.base_url}/simple/price"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
        except httpx.HTTPError as exc:
            logger.warning("CoinGecko request failed", extra={"error": str(exc)})
            raise ProviderError("Error calling CoinGecko.") from exc

        if response.status_code != 200:
            logger.warning(
                "CoinGecko non-200 response",
                extra={"status_code": response.status_code, "body": response.text[:200]},
            )
            raise ProviderError("CoinGecko returned an error response.")

        data = response.json()
        now = datetime.now(timezone.utc)
        quotes: list[Quote] = []

        for symbol in symbol_list:
            payload = data.get(symbol)
            if not isinstance(payload, dict):
                continue
            try:
                price = float(payload["usd"])
                change_pct = float(payload.get("usd_24h_change", 0.0))
            except (KeyError, ValueError, TypeError) as exc:
                logger.warning(
                    "Malformed CoinGecko quote",
                    extra={"symbol": symbol, "payload": payload},
                )
                raise ProviderError(f"Malformed crypto quote for {symbol}") from exc

            quotes.append(
                Quote(
                    symbol=symbol.upper(),
                    asset_type=AssetType.CRYPTO,
                    price=price,
                    change_24h=change_pct,
                    ts=now,
                    is_stale=False,
                )
            )

        return quotes

    async def get_history(
        self,
        symbol: str,
        interval: str,
        range_: str,
    ) -> list[HistoricalBar]:
        # CoinGecko's market_chart uses days; map range_ to days.
        days = {
            "1d": 1,
            "5d": 5,
            "1mo": 30,
        }.get(range_, 1)

        self.rate_limit_guard.acquire()

        params: dict[str, str] = {
            "vs_currency": "usd",
            "days": str(days),
        }
        url = f"{self.base_url}/coins/{symbol.lower()}/market_chart"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
        except httpx.HTTPError as exc:
            logger.warning("CoinGecko history request failed", extra={"error": str(exc)})
            raise ProviderError("Error calling CoinGecko for history.") from exc

        if response.status_code != 200:
            logger.warning(
                "CoinGecko history non-200 response",
                extra={"status_code": response.status_code, "body": response.text[:200]},
            )
            raise ProviderError("CoinGecko returned an error response for history.")

        data = response.json()
        prices = data.get("prices")
        if not isinstance(prices, list):
            raise ProviderError("Unexpected CoinGecko history format.")

        bars: list[HistoricalBar] = []
        for ts_ms, price in prices:
            try:
                ts = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc)
                bars.append(
                    HistoricalBar(
                        ts=ts,
                        open=float(price),
                        high=float(price),
                        low=float(price),
                        close=float(price),
                        volume=None,
                    )
                )
            except (TypeError, ValueError) as exc:
                logger.warning(
                    "Malformed CoinGecko history item",
                    extra={"symbol": symbol, "item": (ts_ms, price)},
                )
                raise ProviderError(f"Malformed crypto history for {symbol}") from exc

        return bars