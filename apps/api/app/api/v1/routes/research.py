from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Path, Request

from sqlalchemy.orm import Session

from app.core.config import AppSettings
from app.core.deps import get_app_settings, get_db_session, get_market_data_service, get_news_client
from app.core.errors import NotFoundError, ResearchDisabledError, ResearchLimitError
from app.core.logging import get_logger
from app.db.models import ResearchReport, ResearchStatus
from app.db.session import SessionLocal
from app.schemas.research import ResearchReportRead, ResearchReportSummary, ResearchRequest
from app.services.market_data.service import MarketDataService
from app.services.news.gdelt_client import GDELTClient
from app.services.research.agents import run_research
from app.services.research.tools import ResearchToolbox

router = APIRouter()

logger = get_logger("app.api.research")


def _runs_today(db: Session) -> int:
    start_of_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return (
        db.query(ResearchReport)
        .filter(ResearchReport.created_at >= start_of_day.replace(tzinfo=None))
        .count()
    )


def _get_research_client(request: Request, settings: AppSettings) -> Any:
    """Return the Anthropic client, honoring a test override on app.state."""
    override = getattr(request.app.state, "research_client", None)
    if override is not None:
        return override
    from anthropic import AsyncAnthropic  # lazy: keeps import cost off the hot path

    return AsyncAnthropic(api_key=settings.anthropic_api_key)


async def _execute_research(
    report_id: int,
    client: Any,
    settings: AppSettings,
    market_data: MarketDataService,
    news_client: GDELTClient,
    request_payload: ResearchRequest,
) -> None:
    """Background task: run the agents and persist the outcome."""
    db = SessionLocal()
    try:
        report = db.get(ResearchReport, report_id)
        if report is None:  # pragma: no cover - row deleted mid-run
            return
        try:
            toolbox = ResearchToolbox(
                market_data=market_data,
                news_client=news_client,
                asset_type=request_payload.asset_type,
            )
            outcome = await run_research(
                client=client,
                model=settings.research_model,
                symbol=request_payload.symbol.upper(),
                toolbox=toolbox,
                max_iterations=settings.research_max_agent_iterations,
            )
            report.status = ResearchStatus.COMPLETED
            report.report_markdown = outcome.synthesis
            report.sections = [
                {
                    "name": s.name,
                    "title": s.title,
                    "text": s.text,
                    "tool_calls": s.tool_calls,
                    "error": s.error,
                }
                for s in outcome.sections
            ]
            report.input_tokens = outcome.usage.input_tokens
            report.output_tokens = outcome.usage.output_tokens
        except Exception as exc:  # noqa: BLE001 - persist failures for the UI
            logger.warning(
                "Research run failed",
                extra={"report_id": report_id, "error": str(exc)},
            )
            report.status = ResearchStatus.FAILED
            report.error = str(exc)[:500]
        report.completed_at = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()


@router.post("", response_model=ResearchReportRead, status_code=202)
async def start_research(
    payload: ResearchRequest,
    request: Request,
    settings: AppSettings = Depends(get_app_settings),
    db: Session = Depends(get_db_session),
    market_data: MarketDataService = Depends(get_market_data_service),
    news_client: GDELTClient = Depends(get_news_client),
) -> ResearchReportRead:
    """Kick off a multi-agent research run; poll the returned id for the result."""
    client = None
    if getattr(request.app.state, "research_client", None) is None and not settings.anthropic_api_key:
        raise ResearchDisabledError(
            "AI research is not configured on this deployment (ANTHROPIC_API_KEY is unset)."
        )
    if _runs_today(db) >= settings.research_daily_limit:
        raise ResearchLimitError(
            "The daily research budget for this demo has been used up. Try again tomorrow."
        )

    client = _get_research_client(request, settings)

    report = ResearchReport(
        symbol=payload.symbol.upper(),
        asset_type=payload.asset_type,
        status=ResearchStatus.RUNNING,
        model=settings.research_model,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    task = asyncio.create_task(
        _execute_research(report.id, client, settings, market_data, news_client, payload),
        name=f"research-{report.id}",
    )
    # Keep a reference so the task isn't garbage collected mid-run.
    tasks: set[asyncio.Task[None]] = getattr(request.app.state, "research_tasks", set())
    tasks.add(task)
    task.add_done_callback(tasks.discard)
    request.app.state.research_tasks = tasks

    return ResearchReportRead.model_validate(report)


@router.get("", response_model=list[ResearchReportSummary])
def list_research(
    db: Session = Depends(get_db_session),
) -> list[ResearchReportSummary]:
    reports = (
        db.query(ResearchReport).order_by(ResearchReport.created_at.desc()).limit(20).all()
    )
    return [ResearchReportSummary.model_validate(r) for r in reports]


@router.get("/{report_id}", response_model=ResearchReportRead)
def get_research(
    report_id: int = Path(..., ge=1),
    db: Session = Depends(get_db_session),
) -> ResearchReportRead:
    report = db.get(ResearchReport, report_id)
    if report is None:
        raise NotFoundError("Research report not found.", details={"report_id": report_id})
    return ResearchReportRead.model_validate(report)
