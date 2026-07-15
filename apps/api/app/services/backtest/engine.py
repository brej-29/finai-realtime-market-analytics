"""Deterministic strategy backtesting engine over daily OHLCV bars.

Modeling assumptions (read before trusting any result):

* Long-only, all-in/all-out sizing. When a strategy is "long" it holds 100%
  of capital in the asset; when "flat" it holds 0%. There is no shorting, no
  leverage, and no partial position sizing.
* No transaction costs, spreads, or slippage are modeled. Every simulated
  trade fills exactly at the bar's close price with zero friction, so real
  returns (especially for higher-turnover strategies) will be lower than what
  this engine reports.
* No lookahead bias: a signal is computed from data available through a
  bar's close, but the resulting position is only applied starting at the
  NEXT bar (`position[i] = signal[i - 1]`). Concretely, the return earned on
  bar `i` is decided using information available no later than bar `i - 1`'s
  close. This is the standard "shift-by-one" backtest convention.

Two strategies are supported:

* ``sma_cross``: long while SMA(fast_window) > SMA(slow_window), flat
  otherwise.
* ``rsi_reversion``: enter long when RSI(period) crosses below `oversold`,
  exit (go flat) when RSI crosses above `overbought`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Sequence

from app.schemas.common import HistoricalBar
from app.services.analytics.indicators import compute_simple_rsi, moving_average

StrategyName = Literal["sma_cross", "rsi_reversion"]

_TRADING_DAYS_PER_YEAR = 252


@dataclass(frozen=True)
class EquityPoint:
    date: datetime
    strategy: float
    buy_hold: float


@dataclass(frozen=True)
class BacktestOutcome:
    total_return_pct: float
    buy_hold_return_pct: float
    cagr_pct: float
    sharpe: float
    max_drawdown_pct: float
    win_rate_pct: float | None
    num_trades: int
    equity_curve: list[EquityPoint]


def _sma_cross_signals(
    closes: Sequence[float],
    fast_window: int,
    slow_window: int,
) -> list[int]:
    """1 = long, 0 = flat, one entry per bar computed using data through that bar."""
    signals: list[int] = []
    for i in range(len(closes)):
        window = closes[: i + 1]
        fast = moving_average(window, fast_window)
        slow = moving_average(window, slow_window)
        signals.append(1 if (fast is not None and slow is not None and fast > slow) else 0)
    return signals


def _rsi_reversion_signals(
    closes: Sequence[float],
    period: int,
    oversold: float,
    overbought: float,
) -> list[int]:
    """1 = long, 0 = flat. Long is entered on a downward cross of `oversold`
    and exited on an upward cross of `overbought`; otherwise the previous
    position is held (RSI reversion is a stateful strategy, unlike SMA cross)."""
    signals: list[int] = []
    position = 0
    prev_rsi: float | None = None
    for i in range(len(closes)):
        window = closes[: i + 1]
        rsi = compute_simple_rsi(window, period=period)
        if rsi is not None and prev_rsi is not None:
            if prev_rsi >= oversold and rsi < oversold:
                position = 1
            elif prev_rsi <= overbought and rsi > overbought:
                position = 0
        signals.append(position)
        if rsi is not None:
            prev_rsi = rsi
    return signals


def _sharpe_annualized(returns: Sequence[float]) -> float:
    n = len(returns)
    if n < 2:
        return 0.0
    mean = sum(returns) / n
    variance = sum((r - mean) ** 2 for r in returns) / (n - 1)
    std = variance**0.5
    if std == 0.0:
        return 0.0
    return (mean / std) * (_TRADING_DAYS_PER_YEAR**0.5)


def _max_drawdown_pct(equity: Sequence[float]) -> float:
    if not equity:
        return 0.0
    peak = equity[0]
    max_dd = 0.0
    for v in equity:
        if v > peak:
            peak = v
        if peak > 0:
            dd = (v - peak) / peak
            if dd < max_dd:
                max_dd = dd
    return abs(max_dd) * 100.0


def run_backtest(
    bars: Sequence[HistoricalBar],
    strategy: StrategyName,
    fast_window: int = 10,
    slow_window: int = 30,
    rsi_period: int = 14,
    oversold: float = 30.0,
    overbought: float = 70.0,
) -> BacktestOutcome:
    """Run a deterministic backtest of `strategy` over `bars`.

    `bars` must be in ascending chronological order (oldest first), matching
    what `MarketDataService.get_history` returns. Raises `ValueError` if
    there are fewer than 2 bars, since at least one return period is needed.
    """
    if len(bars) < 2:
        raise ValueError("At least 2 bars are required to run a backtest.")

    closes = [b.close for b in bars]
    dates = [b.ts for b in bars]
    n = len(closes)

    if strategy == "sma_cross":
        signals = _sma_cross_signals(closes, fast_window, slow_window)
    elif strategy == "rsi_reversion":
        signals = _rsi_reversion_signals(closes, rsi_period, oversold, overbought)
    else:  # pragma: no cover - guarded by Pydantic Literal at the API boundary
        raise ValueError(f"Unknown strategy: {strategy}")

    # No-lookahead: position for bar i is the signal computed through bar i-1.
    positions = [0] * n
    for i in range(1, n):
        positions[i] = signals[i - 1]

    asset_returns = [0.0] * n
    for i in range(1, n):
        prev_close = closes[i - 1]
        asset_returns[i] = (closes[i] / prev_close - 1.0) if prev_close != 0 else 0.0

    strategy_returns = [positions[i] * asset_returns[i] for i in range(n)]

    equity_strategy = [100.0] * n
    equity_buy_hold = [100.0] * n
    for i in range(1, n):
        equity_strategy[i] = equity_strategy[i - 1] * (1.0 + strategy_returns[i])
        equity_buy_hold[i] = equity_buy_hold[i - 1] * (1.0 + asset_returns[i])

    # `num_trades` counts every entry (position flips 0 -> 1), whether or not
    # it has been closed out by the end of the series. `win_rate_pct` is
    # narrower: it is computed only over *closed* trades (entry matched with
    # a later exit, i.e. position flips back 1 -> 0), since a still-open
    # position has no realized outcome to grade as a win or loss.
    closed_trades: list[tuple[float, float]] = []
    entry_price: float | None = None
    num_trades = 0
    for i in range(1, n):
        if positions[i] == 1 and positions[i - 1] == 0:
            entry_price = closes[i - 1]
            num_trades += 1
        elif positions[i] == 0 and positions[i - 1] == 1 and entry_price is not None:
            closed_trades.append((entry_price, closes[i - 1]))
            entry_price = None

    num_closed_trades = len(closed_trades)
    win_rate_pct: float | None
    if num_closed_trades > 0:
        wins = sum(1 for entry, exit_ in closed_trades if exit_ > entry)
        win_rate_pct = (wins / num_closed_trades) * 100.0
    else:
        win_rate_pct = None

    total_return_pct = (equity_strategy[-1] / 100.0 - 1.0) * 100.0
    buy_hold_return_pct = (equity_buy_hold[-1] / 100.0 - 1.0) * 100.0

    trading_days = n - 1
    years = trading_days / float(_TRADING_DAYS_PER_YEAR) if trading_days > 0 else 0.0
    if years > 0 and equity_strategy[-1] > 0:
        cagr_pct = ((equity_strategy[-1] / 100.0) ** (1.0 / years) - 1.0) * 100.0
    else:
        cagr_pct = 0.0

    sharpe = _sharpe_annualized(strategy_returns[1:])
    max_drawdown_pct = _max_drawdown_pct(equity_strategy)

    equity_curve = [
        EquityPoint(date=dates[i], strategy=equity_strategy[i], buy_hold=equity_buy_hold[i])
        for i in range(n)
    ]

    return BacktestOutcome(
        total_return_pct=total_return_pct,
        buy_hold_return_pct=buy_hold_return_pct,
        cagr_pct=cagr_pct,
        sharpe=sharpe,
        max_drawdown_pct=max_drawdown_pct,
        win_rate_pct=win_rate_pct,
        num_trades=num_trades,
        equity_curve=equity_curve,
    )
