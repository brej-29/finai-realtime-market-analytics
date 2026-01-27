from __future__ import annotations

import asyncio
from typing import Optional

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models import AssetType
from app.services.market_data.service import MarketDataService
from app.services.realtime.manager import RealtimeManager

logger = get_logger("app.services.realtime.streamer")


class RealtimeStreamer:
    """Background task that polls providers and broadcasts ticks."""

    def __init__(
        self,
        manager: RealtimeManager,
        market_data_service: MarketDataService,
    ) -> None:
        self.manager = manager
        self.market_data_service = market_data_service
        self._task: Optional[asyncio.Task[None]] = None
        self._stop_event = asyncio.Event()
        self._settings = get_settings()

    async def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run_loop(), name="realtime-streamer")

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            await self._task

    async def _run_loop(self) -> None:
        interval = self._settings.websocket_stream_interval_seconds
        logger.info("Starting realtime streamer loop", extra={"interval_seconds": interval})
        try:
            while not self._stop_event.is_set():
                await self._tick()
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=interval)
                except asyncio.TimeoutError:
                    continue
        finally:
            logger.info("Realtime streamer loop stopped")

    async def _tick(self) -> None:
        keys = await self.manager.get_all_subscription_keys()
        if not keys:
            return

        # Group symbols by asset type for efficient provider calls.
        stock_symbols: set[str] = set()
        crypto_symbols: set[str] = set()

        for symbol, asset_type in keys:
            if asset_type is AssetType.STOCK:
                stock_symbols.add(symbol)
            elif asset_type is AssetType.CRYPTO:
                crypto_symbols.add(symbol)

        tasks = []
        if stock_symbols:
            tasks.append(self._fetch_and_broadcast(AssetType.STOCK, stock_symbols))
        if crypto_symbols:
            tasks.append(self._fetch_and_broadcast(AssetType.CRYPTO, crypto_symbols))

        if tasks:
            await asyncio.gather(*tasks)

    async def _fetch_and_broadcast(
        self,
        asset_type: AssetType,
        symbols: set[str],
    ) -> None:
        try:
            quotes = await self.market_data_service.get_quotes(asset_type=asset_type, symbols=symbols)
        except Exception as exc:
            logger.warning(
                "Error fetching quotes in realtime streamer",
                extra={"asset_type": asset_type.value, "error": str(exc)},
            )
            return

        for quote in quotes:
            await self.manager.broadcast_tick(quote)


async def create_streamer(manager: RealtimeManager, market_data_service: MarketDataService) -> RealtimeStreamer:
    return RealtimeStreamer(manager=manager, market_data_service=market_data_service)