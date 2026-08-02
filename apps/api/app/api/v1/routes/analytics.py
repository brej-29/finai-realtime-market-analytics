from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db_session, get_market_data_service, get_workspace_id
from app.db.models import AssetType, Holding
from app.schemas.analytics import (
    BenchmarkAnalyticsResponse,
    PortfolioAnalyticsResponse,
    ReturnPoint,
)
from app.services.market_data.service import MarketDataService

router = APIRouter()


def _compute_returns(values: List[float]) -> List[float]:
    returns: List[float] = []
    for i in range(1, len(values)):
        prev = values[i - 1]
        curr = values[i]
        if prev <= 0:
            returns.append(0.0)
        else:
            returns.append((curr / prev) - 1.0)
    return returns


def _compute_volatility(returns: List[float]) -> float:
    n = len(returns)
    if n < 2:
        return 0.0
    mean = sum(returns) / n
    var = sum((r - mean) ** 2 for r in returns) / (n - 1)
    return var**0.5


def _compute_max_drawdown(values: List[float]) -> float:
    if not values:
        return 0.0
    peak = values[0]
    max_drawdown = 0.0
    for v in values:
        if v > peak:
            peak = v
        if peak > 0:
            drawdown = (v - peak) / peak
            if drawdown < max_drawdown:
                max_drawdown = drawdown
    return abs(max_drawdown)


def _compute_sharpe(returns: List[float]) -> float | None:
    if not returns:
        return None
    vol = _compute_volatility(returns)
    if vol == 0.0:
        return None
    mean = sum(returns) / len(returns)
    return mean / vol


@router.get("/portfolio", response_model=PortfolioAnalyticsResponse)
async def get_portfolio_analytics(
    db: Session = Depends(get_db_session),
    market_data: MarketDataService = Depends(get_market_data_service),
    workspace_id: str = Depends(get_workspace_id),
) -> PortfolioAnalyticsResponse:
    """Compute simple risk metrics and daily returns for the current portfolio."""
    holdings: List[Holding] = (
        db.query(Holding).filter(Holding.workspace_id == workspace_id).all()
    )
    if not holdings:
        return PortfolioAnalyticsResponse(
            volatility=0.0,
            max_drawdown=0.0,
            sharpe_ratio=None,
            daily_returns=[],
        )

    # Fetch history per symbol.
    history_by_symbol: Dict[str, List[float]] = {}
    ts_by_symbol: Dict[str, List[datetime]] = {}

    for holding in holdings:
        bars = await market_data.get_history(
            asset_type=holding.asset_type,
            symbol=holding.symbol,
            interval="1d",
            range_="1mo",
        )
        closes = [b.close for b in bars]
        if len(closes) < 2:
            continue
        history_by_symbol[holding.symbol] = closes
        ts_by_symbol[holding.symbol] = [b.ts for b in bars]

    if not history_by_symbol:
        return PortfolioAnalyticsResponse(
            volatility=0.0,
            max_drawdown=0.0,
            sharpe_ratio=None,
            daily_returns=[],
        )

    # Align by index (simplified; assumes providers return roughly aligned daily bars).
    min_len = min(len(v) for v in history_by_symbol.values())
    symbols = list(history_by_symbol.keys())
    reference_symbol = symbols[0]
    reference_ts = ts_by_symbol[reference_symbol][-min_len:]

    values: List[float] = []
    for idx in range(-min_len, 0):
        portfolio_value = 0.0
        for h in holdings:
            series = history_by_symbol.get(h.symbol)
            if not series or len(series) < -idx:
                continue
            price = series[idx]
            portfolio_value += h.quantity * price
        values.append(portfolio_value)

    returns = _compute_returns(values)
    volatility = _compute_volatility(returns)
    max_drawdown = _compute_max_drawdown(values)
    sharpe_ratio = _compute_sharpe(returns)

    points: List[ReturnPoint] = []
    for i, v in enumerate(values):
        ts = reference_ts[i]
        ret = returns[i - 1] if i > 0 and i - 1 < len(returns) else None
        points.append(ReturnPoint(ts=ts, value=v, return_pct=ret))

    return PortfolioAnalyticsResponse(
        volatility=volatility,
        max_drawdown=max_drawdown,
        sharpe_ratio=sharpe_ratio,
        daily_returns=points,
    )


@router.get("/benchmark", response_model=BenchmarkAnalyticsResponse)
async def get_benchmark_analytics(
    symbol: str = Query(..., description="Benchmark symbol, e.g. SPY or BTC."),
    asset_type: AssetType = Query(
        AssetType.STOCK,
        description="Asset type for the benchmark (stock or crypto).",
    ),
    market_data: MarketDataService = Depends(get_market_data_service),
) -> BenchmarkAnalyticsResponse:
    """Compute simple risk metrics and daily returns for a benchmark symbol."""
    bars = await market_data.get_history(
        asset_type=asset_type,
        symbol=symbol,
        interval="1d",
        range_="1mo",
    )
    closes = [b.close for b in bars]
    if len(closes) < 2:
        now = datetime.now(timezone.utc)
        return BenchmarkAnalyticsResponse(
            symbol=symbol.upper(),
            asset_type=asset_type,
            volatility=0.0,
            max_drawdown=0.0,
            sharpe_ratio=None,
            daily_returns=[ReturnPoint(ts=now, value=0.0, return_pct=None)],
        )

    returns = _compute_returns(closes)
    volatility = _compute_volatility(returns)
    max_drawdown = _compute_max_drawdown(closes)
    sharpe_ratio = _compute_sharpe(returns)

    points: List[ReturnPoint] = []
    for i, bar in enumerate(bars):
        ret = returns[i - 1] if i > 0 and i - 1 < len(returns) else None
        points.append(ReturnPoint(ts=bar.ts, value=bar.close, return_pct=ret))

    return BenchmarkAnalyticsResponse(
        symbol=symbol.upper(),
        asset_type=asset_type,
        volatility=volatility,
        max_drawdown=max_drawdown,
        sharpe_ratio=sharpe_ratio,
        daily_returns=points,
    )