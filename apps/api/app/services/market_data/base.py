from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, List

from app.db.models import AssetType
from app.schemas.common import HistoricalBar, Quote


class MarketDataProvider(ABC):
    """Abstract base class for market data providers."""

    @abstractmethod
    async def get_quotes(self, symbols: Iterable[str]) -> List[Quote]:
        """Fetch latest quotes for the given symbols."""

    @abstractmethod
    async def get_history(
        self,
        symbol: str,
        interval: str,
        range_: str,
    ) -> list[HistoricalBar]:
        """Fetch historical OHLC data for the given symbol."""


class SupportsAssetType(ABC):
    """Mixin indicating which asset types a provider can serve."""

    asset_type: AssetType