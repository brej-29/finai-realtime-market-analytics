from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes import (
    alerts,
    health,
    history,
    news,
    portfolio,
    quotes,
    reports,
    research,
    analytics,
    ai,
    watchlists,
    websocket,
)

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
v1_router.include_router(news.router, prefix="/news", tags=["news"])
v1_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
v1_router.include_router(reports.router, prefix="/reports", tags=["reports"])
v1_router.include_router(ai.router, prefix="/ai", tags=["ai"])
v1_router.include_router(research.router, prefix="/research", tags=["research"])

api_router.include_router(v1_router)

# WebSocket routes (no versioning)
api_router.include_router(websocket.router, tags=["realtime"])