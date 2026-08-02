from __future__ import annotations

from collections.abc import Generator, Iterable
from datetime import datetime, timezone

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
    """Provide a TestClient with a stubbed MarketDataService and clean DB."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    dummy_service = DummyMarketDataService()

    def override_market_data_service() -> DummyMarketDataService:
        return dummy_service  # type: ignore[return-value]

    app.dependency_overrides[get_market_data_service] = override_market_data_service
    # base_url must be https: the workspace cookie is Secure-flagged, and
    # httpx's cookie jar silently drops Secure cookies on http:// requests.
    test_client = TestClient(app, base_url="https://testserver")
    try:
        yield test_client  # type: ignore[misc]
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


@pytest.mark.parametrize(
    "path",
    [
        "/health",
        "/api/v1/quotes?symbols=AAPL&asset_type=stock",
        "/api/v1/history?symbol=AAPL&asset_type=stock&interval=1h&range=1d",
    ],
)
def test_basic_endpoints_respond(client: TestClient, path: str) -> None:
    response = client.get(path)
    assert response.status_code in {200, 400, 502}


def test_health_response_shape(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "timestamp" in data


def test_watchlists_crud(client: TestClient) -> None:
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


def test_default_watchlist_get_or_create(client: TestClient) -> None:
    # First call creates the default watchlist; the new workspace also
    # auto-seeds demo data (see get_workspace_id), so items is pre-populated.
    resp = client.get("/api/v1/watchlists/default")
    assert resp.status_code == 200
    first = resp.json()
    assert first["name"] == "Default"
    seeded_count = len(first["items"])

    # Second call returns the same watchlist instead of creating another
    resp = client.get("/api/v1/watchlists/default")
    assert resp.status_code == 200
    assert resp.json()["id"] == first["id"]

    # Items added to it show up on subsequent fetches (SOL is not part of
    # the demo seed, so it is unambiguously the newly added item).
    resp = client.post(
        f"/api/v1/watchlists/{first['id']}/items",
        json={"symbol": "SOL", "asset_type": "crypto"},
    )
    assert resp.status_code == 201
    resp = client.get("/api/v1/watchlists/default")
    items = resp.json()["items"]
    assert len(items) == seeded_count + 1
    assert any(i["symbol"] == "SOL" and i["asset_type"] == "crypto" for i in items)


def test_seed_demo_data_is_idempotent(client: TestClient) -> None:
    from app.db.seed import seed_demo_data
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        assert seed_demo_data(db) is True
        # Second run must be a no-op
        assert seed_demo_data(db) is False
    finally:
        db.close()

    resp = client.get("/api/v1/watchlists/default")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Default"
    assert len(data["items"]) == 5

    resp = client.get("/api/v1/holdings")
    assert resp.status_code == 200
    assert len(resp.json()) == 5

    resp = client.get("/api/v1/alerts")
    assert resp.status_code == 200
    assert len(resp.json()) == 3


def test_alerts_create_and_list(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/alerts",
        json={
            "symbol": "AAPL",
            "asset_type": "stock",
            "direction": "price_above",
            "threshold": 100.0,
        },
    )
    assert resp.status_code == 201
    alert = resp.json()
    assert alert["symbol"] == "AAPL"

    resp = client.get("/api/v1/alerts")
    assert resp.status_code == 200
    alerts = resp.json()
    assert isinstance(alerts, list)
    assert any(a["symbol"] == "AAPL" for a in alerts)

    # Events endpoint should respond even if no events yet
    resp = client.get("/api/v1/alerts/events")
    assert resp.status_code == 200
    events = resp.json()
    assert isinstance(events, list)


def test_holdings_and_portfolio_summary(client: TestClient) -> None:
    # Baseline: the workspace auto-seeds demo holdings on its first request,
    # so compare against a delta rather than an absolute total.
    baseline = client.get("/api/v1/portfolio/summary").json()

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
    assert data["total_cost_basis"] == pytest.approx(baseline["total_cost_basis"] + 900.0)
    # Dummy price is 100.0
    assert data["total_market_value"] == pytest.approx(baseline["total_market_value"] + 1000.0)
    assert data["total_unrealized_pnl"] == pytest.approx(baseline["total_unrealized_pnl"] + 100.0)


def test_holding_create_and_delete(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/holdings",
        json={
            "symbol": "MSFT",
            "asset_type": "stock",
            "quantity": 5,
            "average_price": 300.0,
        },
    )
    assert resp.status_code == 201
    holding_id = resp.json()["id"]

    resp = client.delete(f"/api/v1/holdings/{holding_id}")
    assert resp.status_code == 200
    assert resp.json()["success"] is True
    assert resp.json()["deleted_holding_id"] == holding_id

    resp = client.get("/api/v1/holdings")
    assert resp.status_code == 200
    assert all(h["id"] != holding_id for h in resp.json())


def test_holding_delete_missing_returns_404(client: TestClient) -> None:
    resp = client.delete("/api/v1/holdings/999999")
    assert resp.status_code == 404


def test_holdings_isolated_between_workspaces(client: TestClient) -> None:
    """Two visitors (separate cookie jars) only see their own holdings.

    Uses symbols outside the demo-seed list (AAPL/MSFT/NVDA/BTC/ETH) since
    each workspace auto-seeds demo data on its first request.
    """
    client_b = TestClient(app, base_url="https://testserver")

    resp = client.post(
        "/api/v1/holdings",
        json={"symbol": "GOOG", "asset_type": "stock", "quantity": 1, "average_price": 100.0},
    )
    assert resp.status_code == 201

    resp = client_b.post(
        "/api/v1/holdings",
        json={"symbol": "TSLA", "asset_type": "stock", "quantity": 2, "average_price": 200.0},
    )
    assert resp.status_code == 201

    symbols_a = {h["symbol"] for h in client.get("/api/v1/holdings").json()}
    symbols_b = {h["symbol"] for h in client_b.get("/api/v1/holdings").json()}

    assert "TSLA" in symbols_b
    assert "TSLA" not in symbols_a
    assert "GOOG" in symbols_a
    assert "GOOG" not in symbols_b


def test_holding_delete_other_workspace_returns_404(client: TestClient) -> None:
    """Deleting a holding that belongs to a different workspace 404s, not deletes."""
    client_b = TestClient(app, base_url="https://testserver")

    resp = client.post(
        "/api/v1/holdings",
        json={"symbol": "GOOG", "asset_type": "stock", "quantity": 1, "average_price": 100.0},
    )
    assert resp.status_code == 201
    holding_id = resp.json()["id"]

    resp = client_b.delete(f"/api/v1/holdings/{holding_id}")
    assert resp.status_code == 404

    resp = client.get("/api/v1/holdings")
    assert any(h["id"] == holding_id for h in resp.json())


def test_alert_create_and_delete(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/alerts",
        json={
            "symbol": "MSFT",
            "asset_type": "stock",
            "direction": "price_below",
            "threshold": 50.0,
        },
    )
    assert resp.status_code == 201
    alert_id = resp.json()["id"]

    resp = client.delete(f"/api/v1/alerts/{alert_id}")
    assert resp.status_code == 200
    assert resp.json()["success"] is True
    assert resp.json()["deleted_alert_id"] == alert_id

    resp = client.get("/api/v1/alerts")
    assert resp.status_code == 200
    assert all(a["id"] != alert_id for a in resp.json())


def test_alert_delete_missing_returns_404(client: TestClient) -> None:
    resp = client.delete("/api/v1/alerts/999999")
    assert resp.status_code == 404


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