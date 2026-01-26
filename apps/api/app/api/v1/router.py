from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes import alerts, health, history, portfolio, quotes, watchlists, websocket

api_router = APIRouter()

# Public health endpoint (no version prefix)
api_router.include_router(health.router, tags=["health"])

# Versioned API
v1_router = APIRouter(prefix="/api/v1")

v1_router.include_router(quotes.router, prefix="/quotes", tags=["quotes"])
v1_router.include_router(history.router, prefix="/history", tags=["history"])
v1_router.include_router(watchlists.router, prefix="/watchlists", tags=["watchlists"])
v1_router.include_router(portfolio.router, tags=["portfolio"])
v1_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])

api_router.include_router(v1_router)

# WebSocket routes (no versioning)
api_router.include_router(websocket.router, tags=["realtime"])