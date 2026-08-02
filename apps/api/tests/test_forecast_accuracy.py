from __future__ import annotations

import math
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
from app.services.ml.forecast_eval import evaluate_forecast


def _trending_bars(n: int, start: float = 100.0, step: float = 0.5) -> list[HistoricalBar]:
    """A steadily rising synthetic series - easy for a linear model to fit."""
    base_ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return [
        HistoricalBar(
            ts=base_ts + timedelta(days=i),
            open=start + i * step,
            high=start + i * step + 1,
            low=start + i * step - 1,
            close=start + i * step,
            volume=1000.0,
        )
        for i in range(n)
    ]


def test_evaluate_forecast_on_trending_series() -> None:
    bars = _trending_bars(120)
    result = evaluate_forecast(bars, horizon=7, n_lags=5, max_evaluations=60)

    assert result.evaluations > 0
    for value in (
        result.mae,
        result.rmse,
        result.mape_pct,
        result.directional_accuracy_pct,
        result.band_coverage_pct,
        result.baseline_mae,
        result.skill_vs_baseline_pct,
    ):
        assert math.isfinite(value)
    assert len(result.points) == result.evaluations


def test_evaluate_forecast_no_lookahead() -> None:
    """Altering bars beyond the last evaluated target must not change the metrics.

    With max_evaluations=10 and 120 trending bars, the walk-forward stride
    leaves the final `horizon` bars unused by any fit or actual-comparison -
    see forecast_eval.evaluate_forecast for the t_start/t_end/stride math.
    Crashing those trailing bars must not move a single metric.
    """
    horizon = 7
    bars_a = _trending_bars(120)
    result_a = evaluate_forecast(bars_a, horizon=horizon, n_lags=5, max_evaluations=10)

    # Sanity: the last actual comparison point must sit before the crashed tail.
    last_evaluated_ts = datetime.fromisoformat(result_a.points[-1].date)
    crash_start_ts = bars_a[-horizon].ts
    assert last_evaluated_ts < crash_start_ts

    bars_b = _trending_bars(120)
    for i in range(len(bars_b) - horizon, len(bars_b)):
        bars_b[i] = HistoricalBar(
            ts=bars_b[i].ts,
            open=1.0,
            high=1.0,
            low=1.0,
            close=1.0,
            volume=1000.0,
        )
    result_b = evaluate_forecast(bars_b, horizon=horizon, n_lags=5, max_evaluations=10)

    assert result_b.evaluations == result_a.evaluations
    assert result_b.mae == pytest.approx(result_a.mae)
    assert result_b.rmse == pytest.approx(result_a.rmse)
    assert result_b.mape_pct == pytest.approx(result_a.mape_pct)
    assert result_b.directional_accuracy_pct == pytest.approx(result_a.directional_accuracy_pct)
    assert result_b.band_coverage_pct == pytest.approx(result_a.band_coverage_pct)
    assert result_b.baseline_mae == pytest.approx(result_a.baseline_mae)
    assert result_b.skill_vs_baseline_pct == pytest.approx(result_a.skill_vs_baseline_pct)
    assert result_b.points == result_a.points


def test_evaluate_forecast_insufficient_history_raises() -> None:
    bars = _trending_bars(10)
    with pytest.raises(ValueError):
        evaluate_forecast(bars, horizon=7, n_lags=5)


class _TrendingMarketDataService:
    """Stub returning a synthetic trending series, enough for a walk-forward eval."""

    async def get_quotes(self, asset_type: AssetType, symbols: Iterable[str]) -> list[Quote]:
        now = datetime.now(timezone.utc)
        return [
            Quote(symbol=s.upper(), asset_type=asset_type, price=100.0, ts=now, is_stale=False)
            for s in symbols
        ]

    async def get_history(
        self,
        asset_type: AssetType,
        symbol: str,
        interval: str,
        range_: str,
    ) -> list[HistoricalBar]:
        return _trending_bars(120)


class _SparseMarketDataService:
    """Stub returning too few bars for any walk-forward evaluation point."""

    async def get_quotes(self, asset_type: AssetType, symbols: Iterable[str]) -> list[Quote]:
        now = datetime.now(timezone.utc)
        return [
            Quote(symbol=s.upper(), asset_type=asset_type, price=100.0, ts=now, is_stale=False)
            for s in symbols
        ]

    async def get_history(
        self,
        asset_type: AssetType,
        symbol: str,
        interval: str,
        range_: str,
    ) -> list[HistoricalBar]:
        return _trending_bars(10)


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    try:
        yield TestClient(app, base_url="https://testserver")
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


def test_forecast_accuracy_endpoint_shape(client: TestClient) -> None:
    app.dependency_overrides[get_market_data_service] = lambda: _TrendingMarketDataService()

    resp = client.get(
        "/api/v1/ai/forecast-accuracy?symbol=AAPL&asset_type=stock&horizon=7"
    )
    assert resp.status_code == 200
    data = resp.json()

    expected_keys = {
        "symbol",
        "asset_type",
        "horizon_days",
        "evaluations",
        "mae",
        "rmse",
        "mape_pct",
        "directional_accuracy_pct",
        "band_coverage_pct",
        "baseline_mae",
        "skill_vs_baseline_pct",
        "points",
    }
    assert expected_keys == set(data.keys())
    assert data["symbol"] == "AAPL"
    assert data["asset_type"] == "stock"
    assert data["horizon_days"] == 7
    assert data["evaluations"] > 0
    assert len(data["points"]) == data["evaluations"]
    for point in data["points"]:
        assert {"date", "predicted", "actual", "lower", "upper"} == set(point.keys())


def test_forecast_accuracy_endpoint_insufficient_data(client: TestClient) -> None:
    app.dependency_overrides[get_market_data_service] = lambda: _SparseMarketDataService()

    resp = client.get(
        "/api/v1/ai/forecast-accuracy?symbol=AAPL&asset_type=stock&horizon=7"
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "bad_request"
