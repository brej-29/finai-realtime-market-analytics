from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Sequence

import numpy as np
from sklearn.linear_model import LinearRegression

from app.schemas.common import HistoricalBar
from app.schemas.ai import ForecastPoint


@dataclass
class ForecastResult:
    points: List[ForecastPoint]
    rmse: float


def _extract_closes(bars: Sequence[HistoricalBar]) -> List[float]:
    return [b.close for b in bars]


def train_linear_forecast(
    bars: Sequence[HistoricalBar],
    horizon: int = 7,
    n_lags: int = 5,
) -> ForecastResult:
    """Train a simple linear model on lagged prices and forecast forward.

    This is intentionally lightweight and CPU-friendly (no deep learning),
    suitable for free-tier demo environments.
    """
    closes = _extract_closes(bars)
    if len(closes) <= n_lags + 1:
        raise ValueError("Not enough history to train forecast model.")

    X: list[list[float]] = []
    y: list[float] = []
    for i in range(n_lags, len(closes)):
        X.append(closes[i - n_lags : i])
        y.append(closes[i])

    X_arr = np.asarray(X)
    y_arr = np.asarray(y)

    model = LinearRegression()
    model.fit(X_arr, y_arr)

    preds_in_sample = model.predict(X_arr)
    residuals = y_arr - preds_in_sample
    rmse = float(np.sqrt(np.mean(residuals**2))) if len(residuals) > 0 else 0.0

    # Use last known lags as seed for iterative forecasting.
    current_input = list(closes[-n_lags:])
    if len(bars) >= 2:
        freq = bars[-1].ts - bars[-2].ts
    else:
        freq = timedelta(days=1)

    last_ts: datetime = bars[-1].ts
    points: list[ForecastPoint] = []
    for _ in range(horizon):
        x_next = np.asarray(current_input, dtype=float).reshape(1, -1)
        y_pred = float(model.predict(x_next)[0])
        last_ts = last_ts + freq
        lower = y_pred - rmse
        upper = y_pred + rmse
        points.append(ForecastPoint(ts=last_ts, value=y_pred, lower=lower, upper=upper))
        current_input.pop(0)
        current_input.append(y_pred)

    return ForecastResult(points=points, rmse=rmse)