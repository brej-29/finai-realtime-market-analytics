from __future__ import annotations

from datetime import datetime, timezone
from collections.abc import Generator, Iterable

import pytest
from fastapi.testclient import TestClient

from app.core.deps import get_market_data_service
from app.db.base import Base
from app.db.models import AlertDirection, AssetType
from app.db.session import engine
from app.main import app
from app.schemas.common import HistoricalBar, Quote


class DummyMarketDataService:
    """Simple stub implementation for tests."""

    async def get_quotes(
        self,
        asset_type: AssetType,
        symbols: Iterable[str],
    ) -> list[Quote]:
        now = datetime.now(timezone.utc)
        return [
            Quote(
                symbol=s.upper(),
                asset_type=asset_type,
                price=100.0,
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
    ) -> list[HistoricalBar]:
        now = datetime.now(timezone.utc)
        return [
            HistoricalBar(ts=now, open=100, high=110, low=90, close=105, volume=1000.0),
        ]


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    # Ensure a clean schema for each test run
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    dummy_service = DummyMarketDataService()

    def override_market_data_service() -> DummyMarketDataService:
        return dummy_service  # type: ignore[return-value]

    app.dependency_overrides[get_market_data_service] = override_market_data_service
    test_client = TestClient(app)
    try:
        yield test_client  # type: ignore[misc]
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


def test_watchlist_crud(client: TestClient) -> None:
    # Create watchlist
    resp = client.post("/api/v1/watchlists", json={"name": "My Watchlist"})
    assert resp.status_code == 201
    watchlist = resp.json()
    watchlist_id = watchlist["id"]

    # Add item
    resp = client.post(
        f"/api/v1/watchlists/{watchlist_id}/items",
        json={"symbol": "AAPL", "asset_type": "stock"},
    )
    assert resp.status_code == 201
    item = resp.json()
    item_id = item["id"]

    # Get watchlist with item
    resp = client.get(f"/api/v1/watchlists/{watchlist_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "My Watchlist"
    assert len(data["items"]) == 1

    # Delete item
    resp = client.delete(f"/api/v1/watchlists/{watchlist_id}/items/{item_id}")
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_holdings_and_portfolio_summary(client: TestClient) -> None:
    # Create holding
    resp = client.post(
        "/api/v1/holdings",
        json={
            "symbol": "AAPL",
            "asset_type": "stock",
            "quantity": 10,
            "average_price": 90.0,
        },
    )
    assert resp.status_code == 201

    # Get summary
    resp = client.get("/api/v1/portfolio/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_cost_basis"] == pytest.approx(900.0)
    # Dummy price is 100.0
    assert data["total_market_value"] == pytest.approx(1000.0)
    assert data["total_unrealized_pnl"] == pytest.approx(100.0)


def test_alert_create_and_evaluate(client: TestClient) -> None:
    # Create alert
    resp = client.post(
        "/api/v1/alerts",
        json={
            "symbol": "AAPL",
            "asset_type": "stock",
            "direction": AlertDirection.PRICE_ABOVE.value,
            "threshold": 95.0,
        },
    )
    assert resp.status_code == 201
    alert_id = resp.json()["id"]

    # Evaluate alert immediately using cached/dummy quote
    resp = client.post(f"/api/v1/alerts/{alert_id}/test-evaluate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["alert_id"] == alert_id
    assert data["triggered"] is True
    assert data["current_price"] == pytest.approx(100.0)