from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import get_market_data_service
from app.core.errors import BadRequestError
from app.schemas.backtest import (
    BacktestParams,
    BacktestRequest,
    BacktestResult,
    EquityPoint as EquityPointSchema,
)
from app.services.backtest.engine import run_backtest
from app.services.market_data.service import MarketDataService

router = APIRouter()

_MIN_LOOKBACK_BUFFER = 10


@router.post("", response_model=BacktestResult)
async def run_backtest_endpoint(
    request: BacktestRequest,
    market_data: MarketDataService = Depends(get_market_data_service),
) -> BacktestResult:
    """Backtest a strategy for a symbol over daily history and return metrics
    plus an equity curve. See `app.services.backtest.engine` for the strategy
    definitions and modeling assumptions (long-only, no costs, no lookahead)."""
    params = request.params or BacktestParams()
    fast_window = params.fast_window if params.fast_window is not None else 10
    slow_window = params.slow_window if params.slow_window is not None else 30
    rsi_period = params.rsi_period if params.rsi_period is not None else 14
    oversold = params.oversold if params.oversold is not None else 30.0
    overbought = params.overbought if params.overbought is not None else 70.0

    # The minimum lookback differs per strategy (slow_window for sma_cross,
    # rsi_period for rsi_reversion); either way we require a small warmup
    # buffer on top so signals have settled before the reported period starts.
    min_lookback = slow_window if request.strategy == "sma_cross" else rsi_period
    min_bars_required = min_lookback + _MIN_LOOKBACK_BUFFER

    bars = await market_data.get_history(
        asset_type=request.asset_type,
        symbol=request.symbol,
        interval="1d",
        range_=request.range,
    )

    if len(bars) < min_bars_required:
        raise BadRequestError(
            f"Not enough daily history for {request.symbol.upper()}: got {len(bars)} bars, "
            f"need at least {min_bars_required} for strategy={request.strategy}."
        )

    outcome = run_backtest(
        bars=bars,
        strategy=request.strategy,
        fast_window=fast_window,
        slow_window=slow_window,
        rsi_period=rsi_period,
        oversold=oversold,
        overbought=overbought,
    )

    return BacktestResult(
        symbol=request.symbol.upper(),
        asset_type=request.asset_type,
        strategy=request.strategy,
        range=request.range,
        bars_used=len(bars),
        total_return_pct=outcome.total_return_pct,
        buy_hold_return_pct=outcome.buy_hold_return_pct,
        cagr_pct=outcome.cagr_pct,
        sharpe=outcome.sharpe,
        max_drawdown_pct=outcome.max_drawdown_pct,
        win_rate_pct=outcome.win_rate_pct,
        num_trades=outcome.num_trades,
        equity_curve=[
            EquityPointSchema(date=p.date, strategy=p.strategy, buy_hold=p.buy_hold)
            for p in outcome.equity_curve
        ],
    )
