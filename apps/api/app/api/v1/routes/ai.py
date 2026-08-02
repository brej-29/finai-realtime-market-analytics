from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.deps import get_market_data_service
from app.core.errors import BadRequestError
from app.db.models import AssetType
from app.schemas.ai import (
    AIInsightsResponse,
    ForecastAccuracyPoint,
    ForecastAccuracyResponse,
    ForecastSummary,
    TechnicalState,
)
from app.services.analytics.indicators import compute_macd, compute_simple_rsi
from app.services.market_data.service import MarketDataService
from app.services.ml.anomaly import detect_return_anomalies
from app.services.ml.forecast_eval import evaluate_forecast
from app.services.ml.forecasting import train_linear_forecast

router = APIRouter()


@router.get("/insights", response_model=AIInsightsResponse)
async def get_ai_insights(
    symbol: str = Query(..., description="Symbol, e.g. AAPL or BTC."),
    asset_type: AssetType = Query(..., description="Asset type: stock or crypto."),
    market_data: MarketDataService = Depends(get_market_data_service),
) -> AIInsightsResponse:
    """Return lightweight AI/ML insights for a given symbol.

    This endpoint is explicitly educational and must not be treated as investment advice.
    """
    bars = await market_data.get_history(
        asset_type=asset_type,
        symbol=symbol,
        interval="1d",
        range_="1mo",
    )

    closes = [b.close for b in bars]
    rsi = compute_simple_rsi(closes)
    macd, macd_signal = compute_macd(closes)
    macd_hist = macd - macd_signal if macd is not None and macd_signal is not None else None

    rsi_label: str | None = None
    if rsi is not None:
        if rsi >= 70:
            rsi_label = "RSI is in an overbought zone (price has risen quickly)."
        elif rsi <= 30:
            rsi_label = "RSI is in an oversold zone (price has fallen quickly)."
        else:
            rsi_label = "RSI is in a neutral zone."

    macd_label: str | None = None
    if macd is not None and macd_signal is not None:
        if macd > macd_signal:
            macd_label = "MACD is above its signal line (short-term momentum is stronger)."
        elif macd < macd_signal:
            macd_label = "MACD is below its signal line (short-term momentum is weaker)."
        else:
            macd_label = "MACD is roughly equal to its signal line."

    technical = TechnicalState(
        rsi=rsi,
        rsi_label=rsi_label,
        macd=macd,
        macd_signal=macd_signal,
        macd_histogram=macd_hist,
        macd_label=macd_label,
    )

    forecast_summary: ForecastSummary | None = None
    try:
        forecast_result = train_linear_forecast(bars)
        points = forecast_result.points
        if points and closes:
            last_price = closes[-1]
            last_forecast = points[-1].value
            delta = last_forecast - last_price
            if abs(delta) < 1e-8:
                direction = "flat"
            elif delta > 0:
                direction = "up"
            else:
                direction = "down"

            confidence = None
            if forecast_result.rmse > 0:
                confidence = min(1.0, abs(delta) / (forecast_result.rmse + 1e-8))

            forecast_summary = ForecastSummary(
                direction=direction,  # type: ignore[arg-type]
                confidence=confidence,
                horizon_days=len(points),
                points=points,
            )
    except ValueError:
        # Not enough data to train a model; leave forecast_summary as None.
        forecast_summary = None

    anomaly_result = detect_return_anomalies(bars)
    anomalies = anomaly_result.points

    disclaimer = (
        "These AI insights are purely educational analytics based on historical data. "
        "They are NOT investment advice and must not be used as a recommendation to "
        "buy or sell any asset."
    )

    return AIInsightsResponse(
        symbol=symbol.upper(),
        asset_type=asset_type,
        technical_summary=technical,
        forecast_summary=forecast_summary,
        anomalies=anomalies[-10:],
        disclaimer=disclaimer,
    )


@router.get("/forecast-accuracy", response_model=ForecastAccuracyResponse)
async def get_forecast_accuracy(
    symbol: str = Query(..., description="Symbol, e.g. AAPL or BTC."),
    asset_type: AssetType = Query(AssetType.STOCK, description="Asset type: stock or crypto."),
    horizon: int = Query(7, ge=1, le=30, description="Forecast horizon in bars."),
    market_data: MarketDataService = Depends(get_market_data_service),
) -> ForecastAccuracyResponse:
    """Walk-forward backtest of the linear forecast model against realized prices.

    This endpoint is explicitly educational model evaluation and must not be
    treated as investment advice.
    """
    bars = await market_data.get_history(
        asset_type=asset_type,
        symbol=symbol,
        interval="1d",
        range_="1y",
    )

    try:
        evaluation = evaluate_forecast(bars, horizon=horizon)
    except ValueError as exc:
        raise BadRequestError(
            f"Not enough history to evaluate the forecast model for {symbol.upper()}: {exc}"
        ) from exc

    return ForecastAccuracyResponse(
        symbol=symbol.upper(),
        asset_type=asset_type,
        horizon_days=horizon,
        evaluations=evaluation.evaluations,
        mae=evaluation.mae,
        rmse=evaluation.rmse,
        mape_pct=evaluation.mape_pct,
        directional_accuracy_pct=evaluation.directional_accuracy_pct,
        band_coverage_pct=evaluation.band_coverage_pct,
        baseline_mae=evaluation.baseline_mae,
        skill_vs_baseline_pct=evaluation.skill_vs_baseline_pct,
        points=[
            ForecastAccuracyPoint(
                date=p.date,
                predicted=p.predicted,
                actual=p.actual,
                lower=p.lower,
                upper=p.upper,
            )
            for p in evaluation.points
        ],
    )