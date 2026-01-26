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