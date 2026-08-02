from __future__ import annotations

import json
import time
from collections.abc import Generator, Iterable
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.deps import get_market_data_service, get_news_client
from app.db.base import Base
from app.db.models import AssetType, ResearchReport, ResearchStatus
from app.db.session import SessionLocal, engine
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


async def test_run_research_emits_lifecycle_events_per_agent() -> None:
    client = StubAnthropicClient()
    toolbox = ResearchToolbox(
        market_data=DummyMarketDataService(),  # type: ignore[arg-type]
        news_client=DummyNewsClient(),  # type: ignore[arg-type]
        asset_type=AssetType.STOCK,
    )
    events: list[dict[str, Any]] = []
    await run_research(client, "stub-model", "AAPL", toolbox, on_event=events.append)

    started = {e["agent"] for e in events if e["type"] == "agent_started"}
    completed = {e["agent"] for e in events if e["type"] == "agent_completed"}
    expected_agents = {spec.name for spec in AGENT_SPECS}
    assert started == expected_agents
    assert completed == expected_agents
    assert all(e["ok"] is True for e in events if e["type"] == "agent_completed")
    assert any(e["type"] == "tool_call" for e in events)
    assert any(e["type"] == "synthesis_started" for e in events)


def test_estimate_cost_usd_uses_model_pricing() -> None:
    from app.services.research.pricing import estimate_cost_usd

    # Haiku: $1.00/$5.00 per 1M tokens.
    cost = estimate_cost_usd("claude-haiku-4-5", input_tokens=10_000, output_tokens=2_000)
    assert cost == pytest.approx(0.01 + 0.01)

    # Unknown model falls back to Haiku-tier pricing rather than $0, so it
    # can't silently defeat the daily budget check.
    unknown_cost = estimate_cost_usd("some-new-model", input_tokens=10_000, output_tokens=2_000)
    assert unknown_cost == pytest.approx(cost)

    groq_cost = estimate_cost_usd("llama-3.3-70b-versatile", input_tokens=10_000, output_tokens=2_000)
    assert groq_cost < cost  # Groq is meaningfully cheaper


async def test_groq_messages_translates_tools_and_round_trips_tool_use() -> None:
    """Exercise the Anthropic<->OpenAI translation in isolation, without
    constructing a real AsyncGroq client."""
    from app.services.research.llm import NormalizedBlock, _GroqMessages

    captured_requests: list[dict[str, Any]] = []

    class FakeCompletions:
        def __init__(self) -> None:
            self._call_count = 0

        async def create(self, **kwargs: Any) -> SimpleNamespace:
            captured_requests.append(kwargs)
            self._call_count += 1
            usage = SimpleNamespace(prompt_tokens=42, completion_tokens=7)
            if self._call_count == 1:
                tool_call = SimpleNamespace(
                    id="call_abc",
                    function=SimpleNamespace(name="get_quote", arguments='{"symbol": "AAPL"}'),
                )
                message = SimpleNamespace(content=None, tool_calls=[tool_call])
            else:
                message = SimpleNamespace(content="Final answer.", tool_calls=None)
            return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=usage)

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=FakeCompletions())
    )
    adapter = _GroqMessages(fake_client)

    tools = [
        {
            "name": "get_quote",
            "description": "Get the latest price.",
            "input_schema": {
                "type": "object",
                "properties": {"symbol": {"type": "string"}},
                "required": ["symbol"],
            },
        }
    ]
    messages: list[dict[str, Any]] = [{"role": "user", "content": "Analyze AAPL."}]

    first = await adapter.create(
        model="llama-3.3-70b-versatile",
        max_tokens=600,
        system="You are a technical analyst.",
        tools=tools,
        messages=messages,
    )

    # Tool schema translated to OpenAI's {"type": "function", "function": {...}} shape.
    sent_tools = captured_requests[0]["tools"]
    assert sent_tools[0]["type"] == "function"
    assert sent_tools[0]["function"]["name"] == "get_quote"
    assert sent_tools[0]["function"]["parameters"] == tools[0]["input_schema"]
    # System prompt becomes a leading {"role": "system", ...} message.
    assert captured_requests[0]["messages"][0] == {
        "role": "system",
        "content": "You are a technical analyst.",
    }

    assert first.stop_reason == "tool_use"
    assert first.content == [
        NormalizedBlock(type="tool_use", id="call_abc", name="get_quote", input={"symbol": "AAPL"})
    ]
    assert first.usage.input_tokens == 42
    assert first.usage.output_tokens == 7

    # Round-trip: append the assistant turn + a tool_result, exactly as run_agent does.
    messages.append({"role": "assistant", "content": first.content})
    messages.append(
        {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "call_abc", "content": '{"price": 150.0}'}
            ],
        }
    )

    second = await adapter.create(
        model="llama-3.3-70b-versatile",
        max_tokens=600,
        system="You are a technical analyst.",
        tools=tools,
        messages=messages,
    )

    sent_messages = captured_requests[1]["messages"]
    # system, original user turn, assistant tool-call turn, tool result.
    assert sent_messages[2]["role"] == "assistant"
    assert sent_messages[2]["tool_calls"][0]["function"]["name"] == "get_quote"
    assert json.loads(sent_messages[2]["tool_calls"][0]["function"]["arguments"]) == {
        "symbol": "AAPL"
    }
    assert sent_messages[3] == {
        "role": "tool",
        "tool_call_id": "call_abc",
        "content": '{"price": 150.0}',
    }

    assert second.stop_reason == "end_turn"
    assert second.content == [NormalizedBlock(type="text", text="Final answer.")]


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    app.dependency_overrides[get_market_data_service] = lambda: DummyMarketDataService()
    app.dependency_overrides[get_news_client] = lambda: DummyNewsClient()
    app.state.research_client = StubAnthropicClient()
    app.state.research_groq_client = None

    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        app.dependency_overrides.clear()
        app.state.research_client = None
        app.state.research_groq_client = None
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


def _insert_backdated_report(symbol: str, days_old: float) -> int:
    """Insert a COMPLETED report directly, bypassing the API, with a
    created_at older than `days_old` days (naive UTC, matching storage)."""
    db = SessionLocal()
    try:
        report = ResearchReport(
            symbol=symbol,
            asset_type=AssetType.STOCK,
            status=ResearchStatus.COMPLETED,
            model="stub-model",
            provider="anthropic",
            report_markdown="Old report",
            input_tokens=1,
            output_tokens=1,
            estimated_cost_usd=0.0,
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        report_id = report.id
        report.created_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
            days=days_old
        )
        db.commit()
        return report_id
    finally:
        db.close()


def test_research_reuses_recent_completed_report(client: TestClient) -> None:
    """A second POST for the same symbol within the cache window returns the
    existing report (200) instead of starting a new LLM run."""
    resp = client.post("/api/v1/research", json={"symbol": "AAPL", "asset_type": "stock"})
    assert resp.status_code == 202
    report = resp.json()

    for _ in range(50):
        resp = client.get(f"/api/v1/research/{report['id']}")
        report = resp.json()
        if report["status"] != "running":
            break
        time.sleep(0.1)
    assert report["status"] == "completed"

    anthropic_stub = app.state.research_client
    calls_before = len(anthropic_stub.messages.calls)

    resp = client.post("/api/v1/research", json={"symbol": "aapl", "asset_type": "stock"})
    assert resp.status_code == 200
    reused = resp.json()
    assert reused["id"] == report["id"]
    assert len(anthropic_stub.messages.calls) == calls_before


def test_research_does_not_reuse_expired_report(client: TestClient) -> None:
    """A report older than the cache window is not reused; a new run starts."""
    settings = get_settings()
    old_id = _insert_backdated_report("AAPL", settings.research_cache_days + 1)

    resp = client.post("/api/v1/research", json={"symbol": "AAPL", "asset_type": "stock"})
    assert resp.status_code == 202
    report = resp.json()
    assert report["id"] != old_id
    assert report["status"] == "running"


def test_list_research_excludes_expired_report_but_get_still_returns_it(
    client: TestClient,
) -> None:
    settings = get_settings()
    old_id = _insert_backdated_report("MSFT", settings.research_cache_days + 1)

    resp = client.get("/api/v1/research")
    assert resp.status_code == 200
    assert all(item["id"] != old_id for item in resp.json())

    resp = client.get(f"/api/v1/research/{old_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == old_id


def test_research_endpoint_disabled_without_key(client: TestClient) -> None:
    app.state.research_client = None
    app.state.research_groq_client = None
    settings = get_settings()
    original_anthropic = settings.anthropic_api_key
    original_groq = settings.groq_api_key
    settings.anthropic_api_key = None
    settings.groq_api_key = None
    try:
        resp = client.post("/api/v1/research", json={"symbol": "AAPL", "asset_type": "stock"})
        assert resp.status_code == 503
        assert resp.json()["code"] == "research_disabled"
    finally:
        settings.anthropic_api_key = original_anthropic
        settings.groq_api_key = original_groq
        app.state.research_client = StubAnthropicClient()
        app.state.research_groq_client = None


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


def test_stream_endpoint_on_completed_report_closes_immediately(client: TestClient) -> None:
    resp = client.post("/api/v1/research", json={"symbol": "AAPL", "asset_type": "stock"})
    assert resp.status_code == 202
    report = resp.json()

    for _ in range(50):
        resp = client.get(f"/api/v1/research/{report['id']}")
        report = resp.json()
        if report["status"] != "running":
            break
        time.sleep(0.1)
    assert report["status"] == "completed"

    with client.stream("GET", f"/api/v1/research/{report['id']}/stream") as stream_resp:
        assert stream_resp.status_code == 200
        assert stream_resp.headers["content-type"].startswith("text/event-stream")
        body = "".join(stream_resp.iter_text())

    lines = [line for line in body.splitlines() if line.startswith("data: ")]
    assert len(lines) == 1
    event = json.loads(lines[0][len("data: ") :])
    assert event == {"type": "done", "status": "completed", "report_id": report["id"]}


def test_research_report_not_found(client: TestClient) -> None:
    resp = client.get("/api/v1/research/99999")
    assert resp.status_code == 404


def test_research_budget_endpoint_reports_anthropic_by_default(client: TestClient) -> None:
    resp = client.get("/api/v1/research/budget")
    assert resp.status_code == 200
    data = resp.json()
    assert data["spent_usd"] == 0.0
    assert data["budget_usd"] > 0
    assert data["next_run_provider"] == "anthropic"


def test_research_falls_back_to_groq_when_budget_exhausted(client: TestClient) -> None:
    """When today's Anthropic budget is already used up, a new run should use
    Groq without ever calling the Anthropic client."""
    settings = get_settings()
    original_budget = settings.research_daily_budget_usd
    groq_stub = StubAnthropicClient()  # interface is provider-agnostic
    app.state.research_groq_client = groq_stub
    settings.research_daily_budget_usd = 0.0  # already "exhausted" before any spend
    try:
        resp = client.post("/api/v1/research", json={"symbol": "AAPL", "asset_type": "stock"})
        assert resp.status_code == 202
        report = resp.json()

        for _ in range(50):
            resp = client.get(f"/api/v1/research/{report['id']}")
            report = resp.json()
            if report["status"] != "running":
                break
            time.sleep(0.1)

        assert report["status"] == "completed"
        assert report["provider"] == "groq"
        assert report["model"] == settings.groq_research_model
        assert len(groq_stub.messages.calls) > 0
        # The Anthropic stub attached by the fixture must never have been used.
        anthropic_stub = app.state.research_client
        assert len(anthropic_stub.messages.calls) == 0
    finally:
        settings.research_daily_budget_usd = original_budget


def test_research_retries_via_groq_on_total_anthropic_failure(client: TestClient) -> None:
    """If every agent errors out on Anthropic (e.g. an outage), the whole run
    should be retried on Groq rather than surfacing a failed report."""

    class ExplodingMessages:
        async def create(self, **kwargs: Any) -> SimpleNamespace:
            raise RuntimeError("Anthropic is down")

    app.state.research_client = SimpleNamespace(messages=ExplodingMessages())
    groq_stub = StubAnthropicClient()
    app.state.research_groq_client = groq_stub
    try:
        resp = client.post("/api/v1/research", json={"symbol": "AAPL", "asset_type": "stock"})
        assert resp.status_code == 202
        report = resp.json()

        for _ in range(50):
            resp = client.get(f"/api/v1/research/{report['id']}")
            report = resp.json()
            if report["status"] != "running":
                break
            time.sleep(0.1)

        assert report["status"] == "completed"
        assert report["provider"] == "groq"
        assert len(groq_stub.messages.calls) > 0
    finally:
        app.state.research_client = StubAnthropicClient()


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
