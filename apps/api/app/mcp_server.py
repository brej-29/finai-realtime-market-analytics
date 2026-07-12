"""FinAI MCP server — exposes the platform's market analytics as MCP tools.

Any MCP client (Claude Desktop, Claude Code, ...) can connect over stdio and
query live quotes, indicators, news sentiment, forecasts, anomalies, and the
demo portfolio. Reuses the same service layer as the REST API and the research
agents, so behavior (caching, rate limiting, fallbacks) is identical.

Run:
    python -m app.mcp_server

Claude Desktop config (claude_desktop_config.json):
    {
      "mcpServers": {
        "finai": {
          "command": "/path/to/apps/api/.venv/bin/python",
          "args": ["-m", "app.mcp_server"],
          "cwd": "/path/to/apps/api"
        }
      }
    }
"""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from app.core.config import get_settings
from app.core.deps import build_market_data_service, build_news_client
from app.db.models import AssetType, Holding
from app.services.research.tools import ResearchToolbox

mcp = FastMCP(
    "finai-market-analytics",
    instructions=(
        "Live stock & crypto analytics from the FinAI platform: quotes, price "
        "history, technical indicators, news sentiment, baseline forecasts, "
        "anomaly detection, and the demo portfolio. Data is educational and "
        "must not be presented as investment advice."
    ),
)

_settings = get_settings()
_market_data = build_market_data_service(_settings)
_news_client = build_news_client(_settings)


def _toolbox(asset_type: str) -> ResearchToolbox:
    normalized = AssetType(asset_type.lower())
    return ResearchToolbox(
        market_data=_market_data,
        news_client=_news_client,
        asset_type=normalized,
    )


async def _run(tool: str, symbol: str, asset_type: str) -> str:
    payload, _is_error = await _toolbox(asset_type).execute(tool, {"symbol": symbol})
    return payload


@mcp.tool()
async def get_quote(symbol: str, asset_type: str = "stock") -> str:
    """Latest price and 24h change for a stock or crypto symbol.

    Args:
        symbol: Ticker, e.g. AAPL or BTC.
        asset_type: "stock" or "crypto".
    """
    return await _run("get_quote", symbol, asset_type)


@mcp.tool()
async def get_price_history(symbol: str, asset_type: str = "stock") -> str:
    """~1 month of daily closes with period return, high/low, and volatility."""
    return await _run("get_price_history", symbol, asset_type)


@mcp.tool()
async def get_technical_indicators(symbol: str, asset_type: str = "stock") -> str:
    """RSI(14), MACD vs signal, and 10/30-day moving averages vs price."""
    return await _run("get_technical_indicators", symbol, asset_type)


@mcp.tool()
async def get_news_sentiment(symbol: str, asset_type: str = "stock") -> str:
    """Recent headlines with per-headline VADER sentiment scores (-1 to 1)."""
    return await _run("get_news_sentiment", symbol, asset_type)


@mcp.tool()
async def get_forecast(symbol: str, asset_type: str = "stock") -> str:
    """Baseline 7-day linear-regression forecast. Educational, not a signal."""
    return await _run("get_forecast", symbol, asset_type)


@mcp.tool()
async def get_anomalies(symbol: str, asset_type: str = "stock") -> str:
    """Anomalous daily moves over the last month (IsolationForest on returns)."""
    return await _run("get_anomalies", symbol, asset_type)


@mcp.tool()
async def get_portfolio_summary() -> str:
    """Cost basis, live market value, and unrealized P&L of the demo portfolio."""
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        holdings = db.query(Holding).all()
    finally:
        db.close()

    if not holdings:
        return json.dumps({"holdings": 0, "message": "No holdings in the portfolio."})

    positions = []
    total_cost = 0.0
    total_value = 0.0
    by_type: dict[AssetType, list[Holding]] = {}
    for h in holdings:
        by_type.setdefault(h.asset_type, []).append(h)

    prices: dict[tuple[AssetType, str], float] = {}
    for asset_type, type_holdings in by_type.items():
        symbols = sorted({h.symbol for h in type_holdings})
        try:
            quotes = await _market_data.get_quotes(asset_type=asset_type, symbols=symbols)
            for q in quotes:
                prices[(q.asset_type, q.symbol)] = q.price
        except Exception:  # noqa: BLE001 - fall back to cost basis below
            pass

    for h in holdings:
        price = prices.get((h.asset_type, h.symbol), h.average_price)
        cost = h.quantity * h.average_price
        value = h.quantity * price
        total_cost += cost
        total_value += value
        positions.append(
            {
                "symbol": h.symbol,
                "asset_type": h.asset_type.value,
                "quantity": h.quantity,
                "average_price": h.average_price,
                "last_price": price,
                "unrealized_pnl": round(value - cost, 2),
            }
        )

    return json.dumps(
        {
            "holdings": len(positions),
            "total_cost_basis": round(total_cost, 2),
            "total_market_value": round(total_value, 2),
            "total_unrealized_pnl": round(total_value - total_cost, 2),
            "positions": positions,
        }
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
