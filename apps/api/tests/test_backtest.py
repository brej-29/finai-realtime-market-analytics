from __future__ import annotations

from collections.abc import Generator, Iterable
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.core.deps import get_market_data_service
from app.db.base import Base
from app.db.models import AssetType
from app.db.session import engine
from app.main import app
from app.schemas.common import HistoricalBar, Quote
from app.services.backtest.engine import run_backtest


def _make_bars(closes: list[float], start: datetime | None = None) -> list[HistoricalBar]:
    start = start or datetime(2025, 1, 1, tzinfo=timezone.utc)
    bars: list[HistoricalBar] = []
    for i, close in enumerate(closes):
        bars.append(
            HistoricalBar(
                ts=start + timedelta(days=i),
                open=close,
                high=close,
                low=close,
                close=close,
                volume=1000.0,
            )
        )
    return bars


# ---------------------------------------------------------------------------
# Engine unit tests
# ---------------------------------------------------------------------------


def test_sma_cross_uptrend_yields_positive_return_and_trades() -> None:
    closes = [100.0 + i for i in range(60)]  # monotonic uptrend
    bars = _make_bars(closes)

    outcome = run_backtest(bars, strategy="sma_cross")

    assert outcome.total_return_pct > 0
    assert outcome.num_trades >= 1
    assert outcome.equity_curve[0].strategy == pytest.approx(100.0)
    assert outcome.equity_curve[0].buy_hold == pytest.approx(100.0)
    assert len(outcome.equity_curve) == len(bars)


def test_sma_cross_flat_series_yields_no_lookahead_crash_and_zero_return() -> None:
    closes = [100.0 for _ in range(60)]  # perfectly flat
    bars = _make_bars(closes)

    outcome = run_backtest(bars, strategy="sma_cross")

    assert outcome.total_return_pct == pytest.approx(0.0)
    assert outcome.buy_hold_return_pct == pytest.approx(0.0)
    assert outcome.num_trades == 0
    assert outcome.win_rate_pct is None


def test_rsi_reversion_flat_series_does_not_crash() -> None:
    closes = [100.0 for _ in range(60)]
    bars = _make_bars(closes)

    outcome = run_backtest(bars, strategy="rsi_reversion")

    assert outcome.total_return_pct == pytest.approx(0.0)
    assert outcome.num_trades == 0


def test_rsi_reversion_enters_on_dip_and_can_trade() -> None:
    # Flat, then a sharp multi-day drop (pushes RSI below the oversold
    # threshold), then a recovery back up (pushes RSI back above overbought).
    closes = [100.0] * 20 + [100.0 - i * 3 for i in range(1, 11)] + [70.0 + i * 4 for i in range(1, 16)]
    bars = _make_bars(closes)

    outcome = run_backtest(bars, strategy="rsi_reversion")

    assert outcome.num_trades >= 1
    assert isinstance(outcome.sharpe, float)


def test_run_backtest_rejects_too_few_bars() -> None:
    bars = _make_bars([100.0, 101.0])
    with pytest.raises(ValueError):
        run_backtest(bars[:1], strategy="sma_cross")


# ---------------------------------------------------------------------------
# API tests (stubbed MarketDataService, following tests/test_api_endpoints.py)
# ---------------------------------------------------------------------------


class DummyMarketDataService:
    """Stub returning a long, deterministic uptrend series for backtesting."""

    def __init__(self, num_bars: int = 260) -> None:
        self.num_bars = num_bars

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
        closes = [100.0 + 0.1 * i for i in range(self.num_bars)]
        return _make_bars(closes)


class TooFewBarsMarketDataService(DummyMarketDataService):
    def __init__(self) -> None:
        super().__init__(num_bars=5)


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
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


def test_backtest_endpoint_sma_cross(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/backtest",
        json={"symbol": "AAPL", "asset_type": "stock", "strategy": "sma_cross", "range": "1y"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "AAPL"
    assert data["strategy"] == "sma_cross"
    assert data["num_trades"] >= 1
    assert data["total_return_pct"] > 0
    assert len(data["equity_curve"]) == 260
    assert data["equity_curve"][0]["strategy"] == pytest.approx(100.0)


def test_backtest_endpoint_rsi_reversion(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/backtest",
        json={"symbol": "AAPL", "asset_type": "stock", "strategy": "rsi_reversion", "range": "1y"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["strategy"] == "rsi_reversion"
    assert "sharpe" in data
    assert "max_drawdown_pct" in data


def test_backtest_endpoint_insufficient_data_returns_400() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    too_few_service = TooFewBarsMarketDataService()

    def override_market_data_service() -> TooFewBarsMarketDataService:
        return too_few_service  # type: ignore[return-value]

    app.dependency_overrides[get_market_data_service] = override_market_data_service
    test_client = TestClient(app)
    try:
        resp = test_client.post(
            "/api/v1/backtest",
            json={"symbol": "AAPL", "asset_type": "stock", "strategy": "sma_cross", "range": "6mo"},
        )
        assert resp.status_code == 400
        body = resp.json()
        assert "not enough" in body["message"].lower()
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


def test_backtest_endpoint_rejects_bad_params(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/backtest",
        json={
            "symbol": "AAPL",
            "asset_type": "stock",
            "strategy": "sma_cross",
            "range": "1y",
            "params": {"fast_window": 30, "slow_window": 10},
        },
    )
    assert resp.status_code == 422
