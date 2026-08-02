from __future__ import annotations

import uuid
from collections.abc import Generator

from fastapi import Depends, Request, Response
from sqlalchemy.orm import Session

from app.core.config import AppSettings, get_settings
from app.db.session import SessionLocal
from app.services.market_data.service import MarketDataService
from app.services.realtime.manager import RealtimeManager
from app.services.news.gdelt_client import GDELTClient

WORKSPACE_COOKIE_NAME = "finai_ws"
WORKSPACE_COOKIE_MAX_AGE = 31536000  # 1 year, seconds


def get_app_settings() -> AppSettings:
    return get_settings()


def get_db_session() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_workspace_id(
    request: Request,
    response: Response,
    db: Session = Depends(get_db_session),
) -> str:
    """Resolve the visitor's sandboxed workspace from a cookie, minting one if absent.

    # ponytail: this is a data-partitioning token, not an auth credential -
    # it is unsigned and trivially forgeable. Do not use it to gate access to
    # anything sensitive; add real auth if that's ever needed.
    """
    workspace_id = request.cookies.get(WORKSPACE_COOKIE_NAME)
    if workspace_id:
        return workspace_id

    workspace_id = uuid.uuid4().hex
    response.set_cookie(
        WORKSPACE_COOKIE_NAME,
        workspace_id,
        httponly=True,
        samesite="lax",
        secure=True,
        max_age=WORKSPACE_COOKIE_MAX_AGE,
        path="/",
    )

    from app.db.seed import seed_demo_data

    seed_demo_data(db, workspace_id)
    return workspace_id


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


def build_news_client(settings: AppSettings) -> GDELTClient:
    """Create a GDELT client with its own in-memory cache."""
    # Lazy import to avoid circular dependency at import time
    from app.services.market_data.cache import InMemoryCache

    cache = InMemoryCache()
    return GDELTClient(
        base_url=settings.gdelt_base_url,
        cache=cache,
        settings=settings,
    )


def get_market_data_service(
    request: Request,
    settings: AppSettings = Depends(get_app_settings),
) -> MarketDataService:
    """Return the shared MarketDataService attached to the app, or build one."""
    service: MarketDataService | None = getattr(
        request.app.state, "market_data_service", None
    )  # type: ignore[attr-defined]
    if service is not None:
        return service
    service = build_market_data_service(settings)
    request.app.state.market_data_service = service  # type: ignore[assignment]
    return service


def get_news_client(
    request: Request,
    settings: AppSettings = Depends(get_app_settings),
) -> GDELTClient:
    """Return the shared GDELT news client attached to the app, or build one."""
    client: GDELTClient | None = getattr(
        request.app.state, "news_client", None
    )  # type: ignore[attr-defined]
    if client is not None:
        return client
    client = build_news_client(settings)
    request.app.state.news_client = client  # type: ignore[assignment]
    return client


def get_realtime_manager() -> RealtimeManager:
    # Singleton per process; safe to reuse across requests
    from app.services.realtime.manager import realtime_manager

    return realtime_manager