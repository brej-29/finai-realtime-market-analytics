from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from http import HTTPStatus
from typing import Iterable, Mapping

import httpx

from app.core.errors import ProviderError
from app.core.logging import get_logger
from app.db.models import AssetType
from app.schemas.common import HistoricalBar, Quote
from app.services.market_data.base import MarketDataProvider, SupportsAssetType
from app.services.market_data.cache import InMemoryCache
from app.services.market_data.rate_limiter import RateLimitGuard

logger = get_logger("app.services.market_data")

_RETRY_STATUS_CODES = {
    HTTPStatus.TOO_MANY_REQUESTS,
    HTTPStatus.INTERNAL_SERVER_ERROR,
    HTTPStatus.BAD_GATEWAY,
    HTTPStatus.SERVICE_UNAVAILABLE,
    HTTPStatus.GATEWAY_TIMEOUT,
}
_MAX_RETRIES = 3


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

    async def _request_with_backoff(
        self,
        url: str,
        params: Mapping[str, str],
        context: str,
    ) -> httpx.Response:
        """Perform an HTTP GET with exponential backoff on transient errors."""
        backoff = 1.0
        last_error: Exception | None = None

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(url, params=params)
            except httpx.HTTPError as exc:
                last_error = exc
                logger.warning(
                    "Twelve Data %s request failed",
                    extra={"context": context, "attempt": attempt, "error": str(exc)},
                )
            else:
                if response.status_code == HTTPStatus.OK:
                    return response

                if response.status_code not in _RETRY_STATUS_CODES or attempt == _MAX_RETRIES:
                    logger.warning(
                        "Twelve Data %s non-success response",
                        extra={
                            "context": context,
                            "status_code": response.status_code,
                            "body": response.text[:200],
                            "attempt": attempt,
                        },
                    )
                    break

                logger.warning(
                    "Twelve Data %s returned retryable status; backing off",
                    extra={
                        "context": context,
                        "status_code": response.status_code,
                        "attempt": attempt,
                    },
                )

            await asyncio.sleep(backoff)
            backoff *= 2

        if last_error is not None:
            raise ProviderError("Error calling Twelve Data.") from last_error
        raise ProviderError("Twelve Data returned an error response.")

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

        response = await self._request_with_backoff(url, params, context="quote")

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

        response = await self._request_with_backoff(url, params, context="history")

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


# Ticker symbol -> CoinGecko coin id for commonly traded assets. CoinGecko's
# API is keyed by coin id (e.g. "bitcoin"), not ticker ("btc"). Symbols not in
# this map are passed through unchanged, since some coin ids match their ticker.
_COINGECKO_IDS: dict[str, str] = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "usdt": "tether",
    "bnb": "binancecoin",
    "sol": "solana",
    "usdc": "usd-coin",
    "xrp": "ripple",
    "doge": "dogecoin",
    "ada": "cardano",
    "trx": "tron",
    "avax": "avalanche-2",
    "shib": "shiba-inu",
    "dot": "polkadot",
    "link": "chainlink",
    "matic": "matic-network",
    "ltc": "litecoin",
    "uni": "uniswap",
    "atom": "cosmos",
    "xlm": "stellar",
    "near": "near",
}


def _coingecko_id(symbol: str) -> str:
    normalized = symbol.lower()
    return _COINGECKO_IDS.get(normalized, normalized)


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

    async def _request_with_backoff(
        self,
        url: str,
        params: Mapping[str, str],
        context: str,
    ) -> httpx.Response:
        """Perform an HTTP GET with exponential backoff on transient errors."""
        backoff = 1.0
        last_error: Exception | None = None

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(url, params=params)
            except httpx.HTTPError as exc:
                last_error = exc
                logger.warning(
                    "CoinGecko %s request failed",
                    extra={"context": context, "attempt": attempt, "error": str(exc)},
                )
            else:
                if response.status_code == HTTPStatus.OK:
                    return response

                if response.status_code not in _RETRY_STATUS_CODES or attempt == _MAX_RETRIES:
                    logger.warning(
                        "CoinGecko %s non-success response",
                        extra={
                            "context": context,
                            "status_code": response.status_code,
                            "body": response.text[:200],
                            "attempt": attempt,
                        },
                    )
                    break

                logger.warning(
                    "CoinGecko %s returned retryable status; backing off",
                    extra={
                        "context": context,
                        "status_code": response.status_code,
                        "attempt": attempt,
                    },
                )

            await asyncio.sleep(backoff)
            backoff *= 2

        if last_error is not None:
            raise ProviderError("Error calling CoinGecko.") from last_error
        raise ProviderError("CoinGecko returned an error response.")

    async def get_quotes(self, symbols: Iterable[str]) -> list[Quote]:
        symbol_list = [s.lower() for s in symbols]
        if not symbol_list:
            return []

        self.rate_limit_guard.acquire()

        id_by_symbol = {symbol: _coingecko_id(symbol) for symbol in symbol_list}
        params: dict[str, str] = {
            "ids": ",".join(id_by_symbol.values()),
            "vs_currencies": "usd",
            "include_24hr_change": "true",
        }
        url = f"{self.base_url}/simple/price"

        response = await self._request_with_backoff(url, params, context="quote")

        data = response.json()
        now = datetime.now(timezone.utc)
        quotes: list[Quote] = []

        for symbol in symbol_list:
            payload = data.get(id_by_symbol[symbol])
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
        url = f"{self.base_url}/coins/{_coingecko_id(symbol)}/market_chart"

        response = await self._request_with_backoff(url, params, context="history")

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