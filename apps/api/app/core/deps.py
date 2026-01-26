from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends, Request

from app.core.config import AppSettings, get_settings
from app.db.session import SessionLocal
from app.services.market_data.service import MarketDataService
from app.services.realtime.manager import RealtimeManager


def get_app_settings() -> AppSettings:
    return get_settings()


def get_db_session() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def build_market_data_service(settings: AppSettings) -> MarketDataService:
    """Create a MarketDataService instance from settings.

    This is used both by FastAPI dependencies and by background tasks.
    """
    # Lazy import to avoid circular dependency at import time
    from app.services.market_data.providers import (
        CoinGeckoProvider,
        TwelveDataProvider,
    )
    from app.services.market_data.cache import InMemoryCache
    from app.services.market_data.rate_limiter import RateLimitGuard

    cache = InMemoryCache()
    twelve_guard = RateLimitGuard(
        capacity=settings.provider_rate_limit_capacity,
        refill_per_second=settings.provider_rate_limit_refill_per_second,
    )
    coingecko_guard = RateLimitGuard(
        capacity=settings.provider_rate_limit_capacity,
        refill_per_second=settings.provider_rate_limit_refill_per_second,
    )

    twelve_provider = TwelveDataProvider(
        api_key=settings.twelve_data_api_key,
        base_url=settings.twelve_data_base_url,
        rate_limit_guard=twelve_guard,
        cache=cache,
    )
    coingecko_provider = CoinGeckoProvider(
        base_url=settings.coingecko_base_url,
        rate_limit_guard=coingecko_guard,
        cache=cache,
    )
    return MarketDataService(
        twelve_data_provider=twelve_provider,
        coingecko_provider=coingecko_provider,
        cache=cache,
        settings=settings,
    )


def get_market_data_service(
    request: Request,
    settings: AppSettings = Depends(get_app_settings),
) -> MarketDataService:
    """Return the shared MarketDataService attached to the app, or build one."""
    service: MarketDataService | None = getattr(request.app.state, "market_data_service", None)  # type: ignore[attr-defined]
    if service is not None:
        return service
    service = build_market_data_service(settings)
    request.app.state.market_data_service = service  # type: ignore[assignment]
    return service


def get_realtime_manager() -> RealtimeManager:
    # Singleton per process; safe to reuse across requests
    from app.services.realtime.manager import realtime_manager

    return realtime_manager