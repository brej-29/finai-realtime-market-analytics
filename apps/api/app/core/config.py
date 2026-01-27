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
        default=60,
        description="Token bucket capacity for provider calls (roughly max calls per minute).",
    )
    provider_rate_limit_refill_per_second: float = Field(
        default=1.0,
        description="Token bucket refill rate (tokens per second).",
    )

    # Realtime / WebSockets
    websocket_heartbeat_interval_seconds: int = Field(
        default=25,
        description="Interval between heartbeat pings to WebSocket clients.",
    )
    websocket_stream_interval_seconds: int = Field(
        default=5,
        description="Interval for background streamer to poll providers.",
    )

    # Alerts / scheduler
    alerts_scheduler_interval_seconds: int = Field(
        default=60,
        description="Interval for evaluating active alerts (seconds).",
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