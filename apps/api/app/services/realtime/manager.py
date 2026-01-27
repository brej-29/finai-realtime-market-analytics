from __future__ import annotations

import asyncio
from typing import Any, Dict, Iterable, Set, Tuple

from fastapi import WebSocket

from app.db.models import AssetType
from app.schemas.common import Quote

SubscriptionKey = Tuple[str, AssetType]


class RealtimeManager:
    """Manage WebSocket connections and symbol subscriptions."""

    def __init__(self) -> None:
        self._connections: Set[WebSocket] = set()
        self._subscriptions: Dict[SubscriptionKey, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)
            for subs in self._subscriptions.values():
                subs.discard(websocket)

    async def subscribe(
        self,
        websocket: WebSocket,
        symbols: Iterable[str],
        asset_type: AssetType,
    ) -> None:
        symbol_list = [s.upper() for s in symbols if s]
        async with self._lock:
            for symbol in symbol_list:
                key: SubscriptionKey = (symbol, asset_type)
                subscribers = self._subscriptions.setdefault(key, set())
                subscribers.add(websocket)

    async def unsubscribe_all(self, websocket: WebSocket) -> None:
        async with self._lock:
            for subs in self._subscriptions.values():
                subs.discard(websocket)

    async def broadcast_tick(self, quote: Quote) -> None:
        key: SubscriptionKey = (quote.symbol.upper(), quote.asset_type)
        async with self._lock:
            subscribers = list(self._subscriptions.get(key, set()))

        payload = {
            "type": "tick",
            "symbol": quote.symbol,
            "assetType": quote.asset_type.value,
            "price": quote.price,
            "ts": quote.ts.isoformat(),
            "change24h": quote.change_24h,
            "isStale": quote.is_stale,
        }

        for websocket in subscribers:
            try:
                await websocket.send_json(payload)
            except Exception:
                # Best-effort; cleanup happens on disconnect.
                await self.disconnect(websocket)

    async def broadcast_heartbeat(self) -> None:
        async with self._lock:
            subscribers = list(self._connections)

        for websocket in subscribers:
            try:
                await websocket.send_json({"type": "heartbeat"})
            except Exception:
                await self.disconnect(websocket)

    async def broadcast_alert(self, payload: Dict[str, Any]) -> None:
        """Broadcast an alert event to all connected clients.

        The payload should already be JSON-serializable and include keys like:
        {"type": "alert", "alertId": ..., "symbol": ..., "message": ..., "ts": ...}
        """
        async with self._lock:
            subscribers = list(self._connections)

        for websocket in subscribers:
            try:
                await websocket.send_json(payload)
            except Exception:
                await self.disconnect(websocket)

    async def get_all_subscription_keys(self) -> Set[SubscriptionKey]:
        async with self._lock:
            return set(self._subscriptions.keys())


realtime_manager = RealtimeManager()