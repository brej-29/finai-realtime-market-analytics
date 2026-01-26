from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Any

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.deps import build_market_data_service
from app.core.errors import register_exception_handlers
from app.core.logging import setup_app_logging
from app.db import models  # noqa: F401  # ensure models are imported for metadata
from app.db.base import Base
from app.db.session import engine
from app.services.realtime.manager import realtime_manager
from app.services.realtime.streamer import RealtimeStreamer


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.project_name,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    setup_app_logging(app)
    register_exception_handlers(app)

    # Routers
    app.include_router(api_router)

    @app.on_event("startup")
    async def on_startup() -> None:  # pragma: no cover - covered indirectly via tests
        # Create tables automatically in local/test environments to simplify setup.
        if settings.env in ("local", "test"):
            Base.metadata.create_all(bind=engine)

        # Shared market data service instance
        market_data_service = build_market_data_service(settings)
        app.state.market_data_service = market_data_service  # type: ignore[assignment]

        # Realtime manager is a singleton; attach for convenience
        app.state.realtime_manager = realtime_manager  # type: ignore[assignment]

        # Start realtime streamer
        streamer = RealtimeStreamer(
            manager=realtime_manager,
            market_data_service=market_data_service,
        )
        app.state.realtime_streamer = streamer  # type: ignore[assignment]
        await streamer.start()

        # Heartbeat loop
        async def heartbeat_loop() -> None:
            while True:
                await asyncio.sleep(settings.websocket_heartbeat_interval_seconds)
                await realtime_manager.broadcast_heartbeat()

        app.state.heartbeat_task = asyncio.create_task(
            heartbeat_loop(), name="realtime-heartbeat"
        )  # type: ignore[assignment]

    @app.on_event("shutdown")
    async def on_shutdown() -> None:  # pragma: no cover - covered indirectly via tests
        streamer: RealtimeStreamer | None = getattr(
            app.state, "realtime_streamer", None
        )  # type: ignore[assignment]
        heartbeat_task: asyncio.Task[Any] | None = getattr(
            app.state, "heartbeat_task", None
        )  # type: ignore[assignment]

        if streamer is not None:
            await streamer.stop()

        if heartbeat_task is not None:
            heartbeat_task.cancel()
            with suppress(asyncio.CancelledError):
                await heartbeat_task

    return app


app = create_app()