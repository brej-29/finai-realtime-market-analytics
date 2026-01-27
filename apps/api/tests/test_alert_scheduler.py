from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List

import pytest

from app.core.config import AppSettings
from app.db.base import Base
from app.db.models import Alert, AlertDirection, AlertEvent, AssetType
from app.db.session import SessionLocal, engine
from app.schemas.common import HistoricalBar, Quote
from app.services.alerts.scheduler import AlertScheduler
from app.services.market_data.service import MarketDataService
from app.services.realtime.manager import RealtimeManager


class DummyMarketDataService(MarketDataService):
    def __init__(self, price: float = 100.0) -> None:
        self.price = price


    async def get_quotes(
        self,
        asset_type: AssetType,
        symbols: Iterable[str],
    ) -> List[Quote]:
        now = datetime.now(timezone.utc)
        return [
            Quote(
                symbol=s.upper(),
                asset_type=asset_type,
                price=self.price,
                change_24h=0.0,
                ts=now,
                is_stale=False,
            )
            for s in symbols
        ]

    async def get_history(
        self,
        asset_type: AssetType,
        symbol: str,
        interval: str,
        range_: str,
    ) -> List[HistoricalBar]:
        now = datetime.now(timezone.utc)
        # Simple synthetic history for RSI / MA; prices ramp from 90 to 110.
        bars: List[HistoricalBar] = []
        for i in range(30):
            ts = now.replace(microsecond=0)  # not important for test
            price = 90.0 + i * (20.0 / 29.0)
            bars.append(
                HistoricalBar(
                    ts=ts,
                    open=price,
                    high=price,
                    low=price,
                    close=price,
                    volume=1000.0,
                )
            )
        return bars


class DummyRealtimeManager(RealtimeManager):
    def __init__(self) -> None:
        super().__init__()
        self.sent: List[Dict[str, Any]] = []

    async def broadcast_alert(self, payload: Dict[str, Any]) -> None:  # type: ignore[override]
        self.sent.append(payload)


@pytest.mark.asyncio
async def test_alert_scheduler_creates_events() -> None:
    # Ensure a clean schema.
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        alert = Alert(
            symbol="AAPL",
            asset_type=AssetType.STOCK,
            direction=AlertDirection.PRICE_ABOVE,
            threshold=95.0,
            is_active=True,
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
    finally:
        db.close()

    settings = AppSettings()
    market_data = DummyMarketDataService(price=100.0)
    realtime = DummyRealtimeManager()
    scheduler = AlertScheduler(
        market_data_service=market_data,
        realtime_manager=realtime,
        settings=settings,
    )

    await scheduler.evaluate_alerts()

    db = SessionLocal()
    try:
        events = db.query(AlertEvent).all()
        assert len(events) == 1
        event = events[0]
        assert event.alert_id == alert.id
        assert "AAPL" in event.message
    finally:
        db.close()

    assert len(realtime.sent) == 1
    payload = realtime.sent[0]
    assert payload["type"] == "alert"
    assert payload["alertId"] == alert.id