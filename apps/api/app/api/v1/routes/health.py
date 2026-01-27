from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from app.schemas.common import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Simple healthcheck endpoint."""
    return HealthResponse(status="ok", timestamp=datetime.now(timezone.utc))