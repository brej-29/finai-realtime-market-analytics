from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    """Application configuration loaded from environment variables."""

    env: Literal["local", "test", "staging", "production"] = Field(
        default="local", description="Runtime environment name."
    )
    debug: bool = Field(default=False, description="Enable debug logging and features.")
    project_name: str = Field(default="finai-realtime-market-analytics-api")

    api_v1_prefix: str = "/api/v1"

    # CORS / frontend integration
    backend_cors_origins: str = Field(
        default="http://localhost:3000",
        alias="BACKEND_CORS_ORIGINS",
        description=(
            "Comma-separated list of allowed CORS origins for browser clients. "
            "Use '*' to allow all origins."
        ),
    )

    # Database
    database_url: str = Field(
        default="sqlite:///./dev.db",
        alias="DATABASE_URL",
        description="Database connection URL. Production should use Postgres.",
    )

    # Market data providers
    twelve_data_api_key: str | None = Field(
        default=None,
        alias="TWELVE_DATA_API_KEY",
        description="API key for Twelve Data (stocks).",
    )
    twelve_data_base_url: str = Field(
        default="https://api.twelvedata.com",
        description="Base URL for Twelve Data API.",
    )

    coingecko_base_url: str = Field(
        default="https://api.coingecko.com/api/v3",
        description="Base URL for CoinGecko API.",
    )

    # News / GDELT
    gdelt_base_url: str = Field(
        default="https://api.gdeltproject.org/api/v2/doc/doc",
        description="Base URL for the GDELT Doc 2.0 API.",
    )
    news_ttl_seconds: int = Field(
        default=1800,
        description="TTL for cached news responses per symbol (seconds).",
    )

    # Market data caching and rate limiting
    quotes_ttl_seconds: int = Field(
        default=10, description="TTL for latest quote cache entries (seconds)."
    )
    history_ttl_seconds: int = Field(
        default=600, description="TTL for historical OHLC cache entries (seconds)."
    )
    provider_rate_limit_capacity: int = Field(
        default=8,
        description=(
            "Token bucket capacity for provider calls (roughly max calls per minute). "
            "Matches Twelve Data's free-tier cap of 8 requests/min by default."
        ),
    )
    provider_rate_limit_refill_per_second: float = Field(
        default=0.1333,
        description="Token bucket refill rate (tokens per second); 8/60 to match the free tier.",
    )

    # Realtime / WebSockets
    websocket_heartbeat_interval_seconds: int = Field(
        default=25,
        description="Interval between heartbeat pings to WebSocket clients.",
    )
    websocket_stream_interval_seconds: int = Field(
        default=10,
        description=(
            "Interval for background streamer to poll providers (seconds). "
            "10s keeps combined polling comfortably under Twelve Data's 8/min free-tier cap."
        ),
    )

    # Alerts / scheduler
    alerts_scheduler_interval_seconds: int = Field(
        default=120,
        description=(
            "Interval for evaluating active alerts (seconds). 120s so the scheduler's own "
            "quote/history calls don't compound with the realtime streamer's polling."
        ),
    )
    alerts_min_event_interval_seconds: int = Field(
        default=300,
        description=(
            "Minimum time between events for the same alert (seconds). "
            "Prevents spamming repeated notifications when conditions remain true."
        ),
    )
    alerts_rsi_period: int = Field(
        default=14,
        description="Lookback period for RSI-based alerts.",
    )
    alerts_ma_short_window: int = Field(
        default=10,
        description="Window length for short moving average in MA cross alerts.",
    )
    alerts_ma_long_window: int = Field(
        default=30,
        description="Window length for long moving average in MA cross alerts.",
    )

    # AI research agents (Phase 2)
    anthropic_api_key: str | None = Field(
        default=None,
        alias="ANTHROPIC_API_KEY",
        description="API key for the Claude API. Falls back to Groq (if configured) when unset.",
    )
    research_model: str = Field(
        default="claude-haiku-4-5",
        alias="RESEARCH_MODEL",
        description=(
            "Claude model used by the research agents. Haiku keeps a full run "
            "around a cent; set claude-sonnet-5 for higher-quality synthesis."
        ),
    )
    groq_api_key: str | None = Field(
        default=None,
        alias="GROQ_API_KEY",
        description=(
            "API key for Groq. Used automatically once today's Anthropic spend "
            "hits RESEARCH_DAILY_BUDGET_USD, or as the sole provider if "
            "ANTHROPIC_API_KEY is unset. Research endpoints are disabled if "
            "neither key is configured."
        ),
    )
    groq_research_model: str = Field(
        default="llama-3.3-70b-versatile",
        alias="GROQ_RESEARCH_MODEL",
        description="Groq model used for fallback research runs.",
    )
    research_daily_budget_usd: float = Field(
        default=0.20,
        alias="RESEARCH_DAILY_BUDGET_USD",
        description=(
            "Max Anthropic spend per UTC day (estimated from actual token usage). "
            "Once hit, new runs use the Groq fallback instead of Anthropic; if Groq "
            "isn't configured either, the endpoint returns 429 for the rest of the day."
        ),
    )
    research_max_agent_iterations: int = Field(
        default=3,
        description=(
            "Max tool-use round trips per analyst agent — a backstop, not the "
            "primary limiter (each agent's system prompt asks for at most 2 tool "
            "calls). Kept low because cost scales with the whole growing "
            "conversation being resent on every turn, not just the new call."
        ),
    )
    research_daily_limit: int = Field(
        default=50,
        alias="RESEARCH_DAILY_LIMIT",
        description=(
            "Max research runs per UTC day across all providers — a coarse "
            "anti-abuse ceiling independent of cost. RESEARCH_DAILY_BUDGET_USD is "
            "the real cost control; this just bounds run count in case cost "
            "estimation is ever wrong."
        ),
    )

    # Demo data
    seed_demo_data: bool = Field(
        default=False,
        alias="SEED_DEMO_DATA",
        description=(
            "Seed a demo watchlist, portfolio, and alerts on startup when the "
            "database is empty. Useful for free-tier deployments where running "
            "one-off commands is not possible."
        ),
    )

    # Logging
    log_level: str = Field(default="INFO", description="Root log level.")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Return application settings (cached)."""
    return AppSettings()  # type: ignore[call-arg]