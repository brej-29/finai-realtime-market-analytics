from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.db.models import AssetType

StrategyName = Literal["sma_cross", "rsi_reversion"]

# Only ranges long enough to backtest against are exposed here (35 daily bars
# for "1mo" is too thin once a slow_window/rsi_period + warmup is applied).
BacktestRange = Literal["6mo", "1y"]


class BacktestParams(BaseModel):
    """Strategy parameters. Only the fields relevant to the chosen `strategy`
    are used; any left unset fall back to that strategy's documented default
    (see `app.services.backtest.engine.run_backtest`)."""

    fast_window: int | None = Field(
        default=None, ge=2, le=100, description="SMA fast window, for sma_cross (default 10)."
    )
    slow_window: int | None = Field(
        default=None, ge=3, le=300, description="SMA slow window, for sma_cross (default 30)."
    )
    rsi_period: int | None = Field(
        default=None, ge=2, le=50, description="RSI lookback period, for rsi_reversion (default 14)."
    )
    oversold: float | None = Field(
        default=None,
        ge=1.0,
        le=49.0,
        description="RSI oversold entry threshold, for rsi_reversion (default 30).",
    )
    overbought: float | None = Field(
        default=None,
        ge=51.0,
        le=99.0,
        description="RSI overbought exit threshold, for rsi_reversion (default 70).",
    )

    @model_validator(mode="after")
    def _check_relative_bounds(self) -> "BacktestParams":
        if (
            self.fast_window is not None
            and self.slow_window is not None
            and self.fast_window >= self.slow_window
        ):
            raise ValueError("fast_window must be less than slow_window.")
        if (
            self.oversold is not None
            and self.overbought is not None
            and self.oversold >= self.overbought
        ):
            raise ValueError("oversold must be less than overbought.")
        return self


class BacktestRequest(BaseModel):
    symbol: str = Field(..., min_length=1, description="Ticker, e.g. AAPL or BTC.")
    asset_type: AssetType = Field(default=AssetType.STOCK)
    strategy: StrategyName
    params: BacktestParams | None = Field(default=None)
    range: BacktestRange = Field(default="1y", description="Daily history window to backtest over.")


class EquityPoint(BaseModel):
    date: datetime
    strategy: float
    buy_hold: float


class BacktestResult(BaseModel):
    symbol: str
    asset_type: AssetType
    strategy: StrategyName
    range: str
    bars_used: int
    total_return_pct: float
    buy_hold_return_pct: float
    cagr_pct: float
    sharpe: float
    max_drawdown_pct: float
    win_rate_pct: float | None
    num_trades: int
    equity_curve: list[EquityPoint]
