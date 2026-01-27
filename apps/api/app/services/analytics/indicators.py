from __future__ import annotations

from collections.abc import Sequence
from typing import Tuple


def moving_average(values: Sequence[float], window: int) -> float | None:
    if window <= 0 or len(values) < window:
        return None
    window_values = values[-window:]
    return sum(window_values) / float(window)


def compute_simple_rsi(values: Sequence[float], period: int = 14) -> float | None:
    """Compute a simple RSI over the given closing prices.

    This is a lightweight approximation using the last `period` differences,
    suitable for educational analytics without heavy dependencies.
    """
    if period <= 0 or len(values) < period + 1:
        return None

    changes = [values[i] - values[i - 1] for i in range(1, len(values))]
    window = changes[-period:]
    gains = [c for c in window if c > 0]
    losses = [-c for c in window if c < 0]

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period if losses else 0.0

    if avg_loss == 0:
        # No losses in the window -> RSI at upper bound.
        return 100.0

    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def _ema(values: Sequence[float], period: int) -> float | None:
    if period <= 0 or len(values) < period:
        return None
    k = 2.0 / (period + 1.0)
    ema_value = values[0]
    for v in values[1:]:
        ema_value = (v - ema_value) * k + ema_value
    return ema_value


def compute_macd(
    values: Sequence[float],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> Tuple[float | None, float | None]:
    """Compute a lightweight MACD (fast EMA - slow EMA, and signal EMA).

    Returns (macd, signal). Histogram can be derived as macd - signal.
    """
    if len(values) < slow_period + signal_period:
        return None, None

    fast_ema = _ema(values, fast_period)
    slow_ema = _ema(values, slow_period)
    if fast_ema is None or slow_ema is None:
        return None, None

    macd = fast_ema - slow_ema

    # For a lightweight approximation we re-use the last (slow_period + signal_period)
    # values to build a short MACD history and compute its EMA.
    macd_history = []
    for i in range(slow_period, len(values)):
        window = values[: i + 1]
        fast = _ema(window, fast_period)
        slow = _ema(window, slow_period)
        if fast is not None and slow is not None:
            macd_history.append(fast - slow)

    signal = _ema(macd_history, signal_period) if macd_history else None
    return macd, signal