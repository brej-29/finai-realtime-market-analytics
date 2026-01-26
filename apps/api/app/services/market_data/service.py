from __future__ import annotations

from typing import Iterable, List

from app.core.config import AppSettings
from app.core.errors import ProviderError
from app.core.logging import get_logger
from app.db.models import AssetType
from app.schemas.common import HistoricalBar, Quote
from app.services.market_data.cache import InMemoryCache
from app.services.market_data.providers import CoinGeckoProvider, TwelveDataProvider

logger = get_logger("app.services.market_data.service")


class MarketDataService:
    """High-level orchestration of market data providers + cache."""

    def __init__(
        self,
        twelve_data_provider: TwelveDataProvider,
        coingecko_provider: CoinGeckoProvider,
        cache: InMemoryCache,
        settings: AppSettings,
    ) -> None:
        self.twelve_data_provider = twelve_data_provider
        self.coingecko_provider = coingecko_provider
        self.cache = cache
        self.settings = settings

    async def get_quotes(
        self,
        asset_type: AssetType,
        symbols: Iterable[str],
    ) -> List[Quote]:
        symbol_list = [s.upper() for s in symbols if s]
        if not symbol_list:
            return []

        cache_key = ("quotes", asset_type.value, tuple(sorted(symbol_list)))
        cached = self.cache.get(cache_key)
        if cached is not None:
            quotes, is_stale = cached
            if isinstance(quotes, list) and quotes:
                # Mark staleness depending on TTL
                if is_stale:
                    for q in quotes:
                        q.is_stale = True
                return quotes

        provider = self._get_provider(asset_type)

        try:
            quotes = await provider.get_quotes(symbol_list)
            self.cache.set(cache_key, quotes, ttl_seconds=self.settings.quotes_ttl_seconds)
            return quotes
        except ProviderError as exc:
            logger.warning(
                "Provider error when fetching quotes; attempting to use stale cache",
                extra={"asset_type": asset_type.value, "symbols": symbol_list, "error": str(exc)},
            )
            cached = self.cache.get(cache_key)
            if cached is not None:
                quotes, _ = cached
                if isinstance(quotes, list):
                    for q in quotes:
                        q.is_stale = True
                    return quotes
            raise

    async def get_history(
        self,
        asset_type: AssetType,
        symbol: str,
        interval: str,
        range_: str,
    ) -> list[HistoricalBar]:
        symbol = symbol.upper()
        cache_key = ("history", asset_type.value, symbol, interval, range_)
        cached = self.cache.get(cache_key)
        if cached is not None:
            bars, _ = cached
            if isinstance(bars, list):
                return bars

        provider = self._get_provider(asset_type)

        bars = await provider.get_history(symbol=symbol, interval=interval, range_=range_)
        self.cache.set(cache_key, bars, ttl_seconds=self.settings.history_ttl_seconds)
        return bars

    def _get_provider(self, asset_type: AssetType):
        if asset_type is AssetType.STOCK:
            return self.twelve_data_provider
        if asset_type is AssetType.CRYPTO:
            return self.coingecko_provider
        raise ProviderError(f"No provider configured for asset_type={asset_type}.")