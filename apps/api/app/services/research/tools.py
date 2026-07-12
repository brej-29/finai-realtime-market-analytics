"""Tools the research agents can call.

Each tool wraps an existing platform service and returns a compact JSON string
so analyst context windows (and token spend) stay small. The same toolbox
backs both the multi-agent research pipeline and the MCP server.
"""

from __future__ import annotations

import json
from typing import Any

from app.core.logging import get_logger
from app.db.models import AssetType
from app.schemas.common import HistoricalBar
from app.services.analytics.indicators import compute_macd, compute_simple_rsi, moving_average
from app.services.market_data.service import MarketDataService
from app.services.ml.anomaly import detect_return_anomalies
from app.services.ml.forecasting import train_linear_forecast
from app.services.news.gdelt_client import GDELTClient

logger = get_logger("app.services.research.tools")

# Anthropic-format tool definitions, keyed by tool name. Agents receive a
# subset of these depending on their specialty.
TOOL_DEFINITIONS: dict[str, dict[str, Any]] = {
    "get_quote": {
        "name": "get_quote",
        "description": (
            "Get the latest price and 24h change for a symbol. Call this first to "
            "anchor your analysis on the current price."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Ticker, e.g. AAPL or BTC."},
            },
            "required": ["symbol"],
        },
    },
    "get_price_history": {
        "name": "get_price_history",
        "description": (
            "Get recent daily closing prices (about one month) with summary statistics: "
            "period return, high/low, and realized volatility. Use this to understand "
            "the recent trend."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Ticker, e.g. AAPL or BTC."},
            },
            "required": ["symbol"],
        },
    },
    "get_technical_indicators": {
        "name": "get_technical_indicators",
        "description": (
            "Compute technical indicators from ~1 month of daily closes: RSI(14), "
            "MACD vs signal, and price vs 10/30-day moving averages. Call this when "
            "assessing momentum or trend strength."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Ticker, e.g. AAPL or BTC."},
            },
            "required": ["symbol"],
        },
    },
    "get_news_sentiment": {
        "name": "get_news_sentiment",
        "description": (
            "Fetch recent news headlines for a symbol with per-headline sentiment "
            "scores (-1 to 1) from the GDELT feed. Call this when assessing market "
            "mood or looking for catalysts."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Ticker, e.g. AAPL or BTC."},
            },
            "required": ["symbol"],
        },
    },
    "get_forecast": {
        "name": "get_forecast",
        "description": (
            "Get the platform's baseline 7-day linear-regression forecast (direction, "
            "rough confidence, projected end value). This is a naive statistical "
            "baseline, not a trading signal — treat it with skepticism."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Ticker, e.g. AAPL or BTC."},
            },
            "required": ["symbol"],
        },
    },
    "get_anomalies": {
        "name": "get_anomalies",
        "description": (
            "Detect anomalous daily moves (IsolationForest on returns/volume) over the "
            "last month. Call this when assessing risk or unusual activity."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Ticker, e.g. AAPL or BTC."},
            },
            "required": ["symbol"],
        },
    },
}


def _round(value: float | None, digits: int = 4) -> float | None:
    return round(value, digits) if value is not None else None


class ResearchToolbox:
    """Executes research tools against the platform's internal services.

    The asset type is fixed per toolbox instance so agents cannot wander to
    other assets mid-run and every tool call stays on the requested symbol
    universe.
    """

    def __init__(
        self,
        market_data: MarketDataService,
        news_client: GDELTClient,
        asset_type: AssetType,
    ) -> None:
        self.market_data = market_data
        self.news_client = news_client
        self.asset_type = asset_type

    async def execute(self, name: str, args: dict[str, Any]) -> tuple[str, bool]:
        """Run a tool and return (json_result, is_error)."""
        symbol = str(args.get("symbol", "")).upper()
        if not symbol:
            return json.dumps({"error": "symbol is required"}), True
        try:
            handler = {
                "get_quote": self._get_quote,
                "get_price_history": self._get_price_history,
                "get_technical_indicators": self._get_technical_indicators,
                "get_news_sentiment": self._get_news_sentiment,
                "get_forecast": self._get_forecast,
                "get_anomalies": self._get_anomalies,
            }.get(name)
            if handler is None:
                return json.dumps({"error": f"unknown tool: {name}"}), True
            result = await handler(symbol)
            return json.dumps(result, default=str), False
        except Exception as exc:  # noqa: BLE001 - tool errors go back to the model
            logger.warning(
                "Research tool failed",
                extra={"tool": name, "symbol": symbol, "error": str(exc)},
            )
            return (
                json.dumps({"error": f"{name} failed: {exc}. Continue without this data."}),
                True,
            )

    async def _bars(self, symbol: str) -> list[HistoricalBar]:
        return await self.market_data.get_history(
            asset_type=self.asset_type,
            symbol=symbol,
            interval="1d",
            range_="1mo",
        )

    async def _get_quote(self, symbol: str) -> dict[str, Any]:
        quotes = await self.market_data.get_quotes(asset_type=self.asset_type, symbols=[symbol])
        if not quotes:
            return {"error": f"no quote available for {symbol}"}
        q = quotes[0]
        return {
            "symbol": q.symbol,
            "price": q.price,
            "change_24h_pct": _round(q.change_24h, 2),
            "as_of": q.ts,
            "is_stale": q.is_stale,
        }

    async def _get_price_history(self, symbol: str) -> dict[str, Any]:
        bars = await self._bars(symbol)
        if not bars:
            return {"error": f"no history available for {symbol}"}
        closes = [b.close for b in bars]
        returns = [
            closes[i] / closes[i - 1] - 1.0 for i in range(1, len(closes)) if closes[i - 1] > 0
        ]
        mean_ret = sum(returns) / len(returns) if returns else 0.0
        variance = (
            sum((r - mean_ret) ** 2 for r in returns) / len(returns) if returns else 0.0
        )
        return {
            "symbol": symbol,
            "days": len(closes),
            "first_close": closes[0],
            "last_close": closes[-1],
            "period_return_pct": _round((closes[-1] / closes[0] - 1.0) * 100, 2),
            "high": max(closes),
            "low": min(closes),
            "daily_volatility_pct": _round((variance**0.5) * 100, 2),
            # Compact series: (date, close) pairs, at most ~30 points.
            "closes": [
                (b.ts.strftime("%Y-%m-%d"), round(b.close, 4)) for b in bars[-30:]
            ],
        }

    async def _get_technical_indicators(self, symbol: str) -> dict[str, Any]:
        bars = await self._bars(symbol)
        closes = [b.close for b in bars]
        if not closes:
            return {"error": f"no history available for {symbol}"}
        rsi = compute_simple_rsi(closes)
        macd, macd_signal = compute_macd(closes)
        ma_short = moving_average(closes, 10)
        ma_long = moving_average(closes, 30)
        return {
            "symbol": symbol,
            "last_close": closes[-1],
            "rsi_14": _round(rsi, 2),
            "macd": _round(macd),
            "macd_signal": _round(macd_signal),
            "macd_histogram": _round(macd - macd_signal)
            if macd is not None and macd_signal is not None
            else None,
            "ma_10": _round(ma_short),
            "ma_30": _round(ma_long),
        }

    async def _get_news_sentiment(self, symbol: str) -> dict[str, Any]:
        result = await self.news_client.get_news(symbol, self.asset_type)
        items = result.items[:10]
        if not items:
            return {"symbol": symbol, "headline_count": 0, "headlines": []}
        scores = [i.sentiment.score for i in items]
        return {
            "symbol": symbol,
            "headline_count": len(items),
            "avg_sentiment": _round(sum(scores) / len(scores), 3),
            "fetched_at": result.fetched_at,
            "headlines": [
                {
                    "title": i.title,
                    "source": i.source,
                    "published_at": i.published_at,
                    "sentiment": _round(i.sentiment.score, 2),
                    "label": i.sentiment.label,
                }
                for i in items
            ],
        }

    async def _get_forecast(self, symbol: str) -> dict[str, Any]:
        bars = await self._bars(symbol)
        if not bars:
            return {"error": f"no history available for {symbol}"}
        try:
            forecast = train_linear_forecast(bars)
        except ValueError as exc:
            return {"error": str(exc)}
        points = forecast.points
        last_close = bars[-1].close
        end = points[-1].value if points else last_close
        return {
            "symbol": symbol,
            "method": "linear regression on 5 lagged daily closes (naive baseline)",
            "horizon_days": len(points),
            "last_close": last_close,
            "projected_end_value": _round(end),
            "projected_change_pct": _round((end / last_close - 1.0) * 100, 2)
            if last_close > 0
            else None,
            "rmse": _round(forecast.rmse),
            "caveat": "Educational baseline only; not a trading signal.",
        }

    async def _get_anomalies(self, symbol: str) -> dict[str, Any]:
        bars = await self._bars(symbol)
        result = detect_return_anomalies(bars)
        anomalies = [p for p in result.points if p.is_anomaly]
        return {
            "symbol": symbol,
            "days_analyzed": len(result.points),
            "anomaly_count": len(anomalies),
            "recent_anomalies": [
                {"date": p.ts.strftime("%Y-%m-%d"), "close": p.value, "score": _round(p.score)}
                for p in anomalies[-5:]
            ],
        }
