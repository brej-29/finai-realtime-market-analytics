from __future__ import annotations

import time
from collections.abc import Generator, Iterable
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.deps import get_market_data_service, get_news_client
from app.db.base import Base
from app.db.models import AssetType
from app.db.session import engine
from app.main import app
from app.schemas.common import HistoricalBar, Quote
from app.schemas.news import NewsArticle, SentimentScore
from app.services.news.gdelt_client import NewsResult
from app.services.research.agents import AGENT_SPECS, run_research
from app.services.research.tools import ResearchToolbox


class DummyMarketDataService:
    async def get_quotes(self, asset_type: AssetType, symbols: Iterable[str]) -> list[Quote]:
        now = datetime.now(timezone.utc)
        return [
            Quote(
                symbol=s.upper(),
                asset_type=asset_type,
                price=100.0,
                change_24h=1.5,
                ts=now,
                is_stale=False,
            )
            for s in symbols
        ]

    async def get_history(
        self, asset_type: AssetType, symbol: str, interval: str, range_: str
    ) -> list[HistoricalBar]:
        now = datetime.now(timezone.utc)
        return [
            HistoricalBar(
                ts=now,
                open=100 + i,
                high=110 + i,
                low=90 + i,
                close=100 + i,
                volume=1000.0,
            )
            for i in range(30)
        ]


class DummyNewsClient:
    async def get_news(self, symbol: str, asset_type: AssetType) -> NewsResult:
        return NewsResult(
            items=[
                NewsArticle(
                    title=f"{symbol} rallies on strong earnings",
                    url=f"https://example.com/{symbol.lower()}",
                    published_at=datetime.now(timezone.utc),
                    source="Example News",
                    sentiment=SentimentScore(
                        score=0.6, label="positive", explanation="Positive: strong"
                    ),
                )
            ],
            fetched_at=datetime.now(timezone.utc),
        )


def _text_block(text: str) -> SimpleNamespace:
    return SimpleNamespace(type="text", text=text)


def _tool_block(name: str) -> SimpleNamespace:
    return SimpleNamespace(type="tool_use", name=name, input={"symbol": "AAPL"}, id="toolu_1")


class StubAnthropicMessages:
    """Scripted Claude stub: one tool call per agent, then a final answer."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        usage = SimpleNamespace(input_tokens=100, output_tokens=50)
        tools = kwargs.get("tools")
        messages = kwargs["messages"]
        if tools and len(messages) == 1:
            # First agent turn: ask for the first available tool.
            return SimpleNamespace(
                content=[_tool_block(tools[0]["name"])],
                stop_reason="tool_use",
                usage=usage,
            )
        return SimpleNamespace(
            content=[_text_block("Scripted analysis: metrics look neutral overall.")],
            stop_reason="end_turn",
            usage=usage,
        )


class StubAnthropicClient:
    def __init__(self) -> None:
        self.messages = StubAnthropicMessages()


async def test_run_research_orchestrates_agents_and_synthesis() -> None:
    client = StubAnthropicClient()
    toolbox = ResearchToolbox(
        market_data=DummyMarketDataService(),  # type: ignore[arg-type]
        news_client=DummyNewsClient(),  # type: ignore[arg-type]
        asset_type=AssetType.STOCK,
    )
    outcome = await run_research(client, "stub-model", "AAPL", toolbox)

    assert len(outcome.sections) == len(AGENT_SPECS)
    for section in outcome.sections:
        assert section.error is None
        assert "Scripted analysis" in section.text
        assert len(section.tool_calls) == 1  # each agent made one tool call
    assert "Scripted analysis" in outcome.synthesis
    assert "NOT investment advice" in outcome.synthesis
    # 3 agents x 2 calls + 1 synthesis call
    assert len(client.messages.calls) == 7
    assert outcome.usage.input_tokens == 700
    assert outcome.usage.output_tokens == 350


async def test_agent_failure_does_not_sink_the_run() -> None:
    class ExplodingMessages:
        async def create(self, **kwargs: Any) -> SimpleNamespace:
            raise RuntimeError("api down")

    client = SimpleNamespace(messages=ExplodingMessages())
    toolbox = ResearchToolbox(
        market_data=DummyMarketDataService(),  # type: ignore[arg-type]
        news_client=DummyNewsClient(),  # type: ignore[arg-type]
        asset_type=AssetType.STOCK,
    )
    from app.services.research.agents import Usage, run_agent

    result = await run_agent(client, "stub-model", AGENT_SPECS[0], "AAPL", toolbox, Usage())
    assert result.error == "api down"
    assert "unavailable" in result.text


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    app.dependency_overrides[get_market_data_service] = lambda: DummyMarketDataService()
    app.dependency_overrides[get_news_client] = lambda: DummyNewsClient()
    app.state.research_client = StubAnthropicClient()

    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        app.dependency_overrides.clear()
        app.state.research_client = None
        Base.metadata.drop_all(bind=engine)


def test_research_endpoint_full_flow(client: TestClient) -> None:
    resp = client.post("/api/v1/research", json={"symbol": "aapl", "asset_type": "stock"})
    assert resp.status_code == 202
    report = resp.json()
    assert report["symbol"] == "AAPL"
    assert report["status"] == "running"

    # The background task runs on the app's event loop; poll for completion.
    for _ in range(50):
        resp = client.get(f"/api/v1/research/{report['id']}")
        assert resp.status_code == 200
        report = resp.json()
        if report["status"] != "running":
            break
        time.sleep(0.1)

    assert report["status"] == "completed"
    assert "NOT investment advice" in report["report_markdown"]
    assert len(report["sections"]) == 3
    assert report["input_tokens"] > 0

    # List endpoint includes the run.
    resp = client.get("/api/v1/research")
    assert resp.status_code == 200
    assert any(item["id"] == report["id"] for item in resp.json())


def test_research_endpoint_disabled_without_key(client: TestClient) -> None:
    app.state.research_client = None
    settings = get_settings()
    original = settings.anthropic_api_key
    settings.anthropic_api_key = None
    try:
        resp = client.post("/api/v1/research", json={"symbol": "AAPL", "asset_type": "stock"})
        assert resp.status_code == 503
        assert resp.json()["code"] == "research_disabled"
    finally:
        settings.anthropic_api_key = original
        app.state.research_client = StubAnthropicClient()


def test_research_daily_limit(client: TestClient) -> None:
    settings = get_settings()
    original = settings.research_daily_limit
    settings.research_daily_limit = 1
    try:
        resp = client.post("/api/v1/research", json={"symbol": "AAPL", "asset_type": "stock"})
        assert resp.status_code == 202
        resp = client.post("/api/v1/research", json={"symbol": "MSFT", "asset_type": "stock"})
        assert resp.status_code == 429
        assert resp.json()["code"] == "research_daily_limit"
    finally:
        settings.research_daily_limit = original


def test_research_report_not_found(client: TestClient) -> None:
    resp = client.get("/api/v1/research/99999")
    assert resp.status_code == 404


def test_mcp_server_registers_tools() -> None:
    import asyncio

    from app.mcp_server import mcp

    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert {
        "get_quote",
        "get_price_history",
        "get_technical_indicators",
        "get_news_sentiment",
        "get_forecast",
        "get_anomalies",
        "get_portfolio_summary",
    } <= names
