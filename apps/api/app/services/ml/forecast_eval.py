from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

import numpy as np

from app.schemas.common import HistoricalBar
from app.services.ml.forecasting import train_linear_forecast


@dataclass
class ForecastEvalPoint:
    date: str
    predicted: float
    actual: float
    lower: float
    upper: float


@dataclass
class ForecastEvaluation:
    evaluations: int
    mae: float
    rmse: float
    mape_pct: float
    directional_accuracy_pct: float
    band_coverage_pct: float
    baseline_mae: float
    skill_vs_baseline_pct: float
    points: List[ForecastEvalPoint]


def evaluate_forecast(
    bars: Sequence[HistoricalBar],
    horizon: int = 7,
    n_lags: int = 5,
    max_evaluations: int = 60,
) -> ForecastEvaluation:
    """Walk-forward backtest of ``train_linear_forecast`` against realized closes.

    For each evaluation point ``t`` we fit ``train_linear_forecast(bars[:t], ...)``
    using ONLY data up to (but not including) index ``t``, then compare its
    horizon-step-ahead prediction against the actual close at index
    ``t + horizon - 1``. The fit only ever sees ``bars[:t]`` (indices
    ``0..t-1``); the bar it is scored against lives at index ``t + horizon - 1
    >= t``, so it is never part of the training slice - no lookahead.
    """
    warmup = n_lags + 20
    t_start = warmup
    t_end = len(bars) - horizon  # last valid t: t + horizon - 1 <= len(bars) - 1

    if t_start > t_end:
        raise ValueError(
            "Not enough history for a walk-forward evaluation: need at least "
            f"{warmup + horizon} bars, got {len(bars)}."
        )

    candidate_count = t_end - t_start + 1
    stride = max(1, -(-candidate_count // max_evaluations))  # ceil division

    preds: list[float] = []
    actuals: list[float] = []
    lowers: list[float] = []
    uppers: list[float] = []
    baselines: list[float] = []
    points: list[ForecastEvalPoint] = []

    for t in range(t_start, t_end + 1, stride):
        actual_idx = t + horizon - 1
        # no lookahead: the training slice bars[:t] covers indices 0..t-1 only,
        # and the target bar always lives at t + horizon - 1 >= t.
        assert actual_idx >= t
        train_bars = bars[:t]
        result = train_linear_forecast(train_bars, horizon=horizon, n_lags=n_lags)
        forecast_point = result.points[-1]

        actual_close = bars[actual_idx].close
        last_known_close = bars[t - 1].close

        preds.append(forecast_point.value)
        actuals.append(actual_close)
        lowers.append(forecast_point.lower)
        uppers.append(forecast_point.upper)
        baselines.append(last_known_close)

        points.append(
            ForecastEvalPoint(
                date=bars[actual_idx].ts.isoformat(),
                predicted=forecast_point.value,
                actual=actual_close,
                lower=forecast_point.lower,
                upper=forecast_point.upper,
            )
        )

    preds_arr = np.asarray(preds)
    actuals_arr = np.asarray(actuals)
    lowers_arr = np.asarray(lowers)
    uppers_arr = np.asarray(uppers)
    baselines_arr = np.asarray(baselines)

    errors = preds_arr - actuals_arr
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors**2)))

    nonzero_actual = actuals_arr != 0
    if np.any(nonzero_actual):
        mape_pct = float(
            np.mean(np.abs(errors[nonzero_actual] / actuals_arr[nonzero_actual])) * 100
        )
    else:
        mape_pct = 0.0

    pred_direction = np.sign(preds_arr - baselines_arr)
    actual_direction = np.sign(actuals_arr - baselines_arr)
    directional_accuracy_pct = float(np.mean(pred_direction == actual_direction) * 100)

    in_band = (actuals_arr >= lowers_arr) & (actuals_arr <= uppers_arr)
    band_coverage_pct = float(np.mean(in_band) * 100)

    baseline_mae = float(np.mean(np.abs(baselines_arr - actuals_arr)))

    if baseline_mae > 0:
        skill_vs_baseline_pct = (baseline_mae - mae) / baseline_mae * 100
    else:
        skill_vs_baseline_pct = 0.0

    return ForecastEvaluation(
        evaluations=len(points),
        mae=mae,
        rmse=rmse,
        mape_pct=mape_pct,
        directional_accuracy_pct=directional_accuracy_pct,
        band_coverage_pct=band_coverage_pct,
        baseline_mae=baseline_mae,
        skill_vs_baseline_pct=skill_vs_baseline_pct,
        points=points,
    )
