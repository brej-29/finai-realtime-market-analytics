from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Path, Request, Response

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.core.config import AppSettings
from app.core.deps import get_app_settings, get_db_session, get_market_data_service, get_news_client
from app.core.errors import NotFoundError, ResearchDisabledError, ResearchLimitError
from app.core.logging import get_logger
from app.db.models import AssetType, ResearchReport, ResearchStatus
from app.db.session import SessionLocal
from app.schemas.research import (
    ResearchBudget,
    ResearchReportRead,
    ResearchReportSummary,
    ResearchRequest,
)
from app.services.market_data.service import MarketDataService
from app.services.news.gdelt_client import GDELTClient
from app.services.research.agents import run_research
from app.services.research.pricing import estimate_cost_usd
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


def _find_reusable_report(
    db: Session, symbol: str, asset_type: AssetType, settings: AppSettings
) -> ResearchReport | None:
    """Most recent report for (symbol, asset_type) that can be handed back
    instead of starting a new run: a COMPLETED report inside the shared
    reuse window, or a RUNNING report started in the last 10 minutes (so
    concurrent requests attach to the in-flight run rather than duplicating
    it). FAILED reports are never reused.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    completed_cutoff = now - timedelta(days=settings.research_cache_days)
    running_cutoff = now - timedelta(minutes=10)
    return (
        db.query(ResearchReport)
        .filter(ResearchReport.symbol == symbol)
        .filter(ResearchReport.asset_type == asset_type)
        .filter(
            or_(
                and_(
                    ResearchReport.status == ResearchStatus.COMPLETED,
                    ResearchReport.created_at >= completed_cutoff,
                ),
                and_(
                    ResearchReport.status == ResearchStatus.RUNNING,
                    ResearchReport.created_at >= running_cutoff,
                ),
            )
        )
        .order_by(ResearchReport.created_at.desc())
        .first()
    )


def _today_anthropic_cost(db: Session) -> float:
    start_of_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    total = (
        db.query(func.coalesce(func.sum(ResearchReport.estimated_cost_usd), 0.0))
        .filter(ResearchReport.provider == "anthropic")
        .filter(ResearchReport.created_at >= start_of_day.replace(tzinfo=None))
        .scalar()
    )
    return float(total or 0.0)


def _build_anthropic_client(settings: AppSettings) -> Any:
    from anthropic import AsyncAnthropic  # lazy: keeps import cost off the hot path

    return AsyncAnthropic(api_key=settings.anthropic_api_key)


def _build_groq_client(settings: AppSettings) -> Any:
    from app.services.research.llm import GroqResearchClient  # lazy: same reason

    if not settings.groq_api_key:  # pragma: no cover - callers only reach here when set
        raise ResearchDisabledError("GROQ_API_KEY is not configured.")
    return GroqResearchClient(api_key=settings.groq_api_key)


def _availability(request: Request, settings: AppSettings) -> tuple[bool, bool]:
    """Whether Anthropic/Groq are usable, honoring test overrides on app.state."""
    anthropic_override = getattr(request.app.state, "research_client", None)
    groq_override = getattr(request.app.state, "research_groq_client", None)
    anthropic_available = anthropic_override is not None or bool(settings.anthropic_api_key)
    groq_available = groq_override is not None or bool(settings.groq_api_key)
    return anthropic_available, groq_available


def _select_provider(request: Request, settings: AppSettings, db: Session) -> tuple[str, str, Any]:
    """Pick (provider, model, client) for a new run, preferring Anthropic while
    today's estimated spend is under budget, and falling back to Groq once
    it's exhausted (or if Anthropic isn't configured at all).
    """
    anthropic_available, groq_available = _availability(request, settings)

    if not anthropic_available and not groq_available:
        raise ResearchDisabledError(
            "AI research is not configured on this deployment "
            "(neither ANTHROPIC_API_KEY nor GROQ_API_KEY is set)."
        )

    if anthropic_available and _today_anthropic_cost(db) < settings.research_daily_budget_usd:
        override = getattr(request.app.state, "research_client", None)
        client = override or _build_anthropic_client(settings)
        return "anthropic", settings.research_model, client

    if groq_available:
        override = getattr(request.app.state, "research_groq_client", None)
        client = override or _build_groq_client(settings)
        return "groq", settings.groq_research_model, client

    raise ResearchLimitError(
        f"Today's Anthropic research budget (${settings.research_daily_budget_usd:.2f}) has "
        "been used. Add a GROQ_API_KEY for a free fallback, or try again tomorrow."
    )


async def _execute_research(
    report_id: int,
    provider: str,
    client: Any,
    model: str,
    settings: AppSettings,
    market_data: MarketDataService,
    news_client: GDELTClient,
    request_payload: ResearchRequest,
    fallback_client: Any | None,
    fallback_model: str | None,
) -> None:
    """Background task: run the agents and persist the outcome.

    If every agent fails on the primary provider (e.g. an Anthropic outage),
    and a Groq fallback is configured, the whole run is retried on Groq before
    giving up — so a demo doesn't just go dark when one provider hiccups.
    """
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
            symbol = request_payload.symbol.upper()

            primary_error: Exception | None = None
            outcome = None
            try:
                outcome = await run_research(
                    client=client,
                    model=model,
                    symbol=symbol,
                    toolbox=toolbox,
                    max_iterations=settings.research_max_agent_iterations,
                )
                total_failure = all(s.error for s in outcome.sections)
            except Exception as exc:  # noqa: BLE001 - a fully down provider raises here
                # synthesize() has no per-agent error isolation, so a totally
                # unreachable provider (not just a broken tool) surfaces as an
                # exception here rather than an outcome with all sections errored.
                primary_error = exc
                total_failure = True

            if total_failure and fallback_client is not None and fallback_model:
                logger.warning(
                    "Primary research provider failed; retrying entire run via Groq fallback",
                    extra={"report_id": report_id, "provider": provider, "error": str(primary_error)},
                )
                outcome = await run_research(
                    client=fallback_client,
                    model=fallback_model,
                    symbol=symbol,
                    toolbox=toolbox,
                    max_iterations=settings.research_max_agent_iterations,
                )
                provider = "groq"
                model = fallback_model
            elif outcome is None:
                # No fallback available — surface the original failure. (outcome
                # is only ever None when the except block above ran, which
                # always sets primary_error, but mypy can't see that invariant.)
                assert primary_error is not None
                raise primary_error

            report.status = ResearchStatus.COMPLETED
            report.provider = provider
            report.model = model
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
            report.estimated_cost_usd = estimate_cost_usd(
                model, outcome.usage.input_tokens, outcome.usage.output_tokens
            )
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
    response: Response,
    settings: AppSettings = Depends(get_app_settings),
    db: Session = Depends(get_db_session),
    market_data: MarketDataService = Depends(get_market_data_service),
    news_client: GDELTClient = Depends(get_news_client),
) -> ResearchReportRead:
    """Kick off a multi-agent research run; poll the returned id for the result.

    Research is shared: a COMPLETED report for the same symbol within the
    last `research_cache_days` days (or a RUNNING report started in the
    last 10 minutes) is returned as-is with a 200 status instead of paying
    for a new LLM run.
    """
    symbol = payload.symbol.upper()
    existing = _find_reusable_report(db, symbol, payload.asset_type, settings)
    if existing is not None:
        response.status_code = 200
        return ResearchReportRead.model_validate(existing)

    if _runs_today(db) >= settings.research_daily_limit:
        raise ResearchLimitError(
            "The daily research run limit for this demo has been reached. Try again tomorrow."
        )

    provider, model, client = _select_provider(request, settings, db)

    fallback_client: Any | None = None
    fallback_model: str | None = None
    if provider == "anthropic":
        _, groq_available = _availability(request, settings)
        if groq_available:
            override = getattr(request.app.state, "research_groq_client", None)
            fallback_client = override or _build_groq_client(settings)
            fallback_model = settings.groq_research_model

    report = ResearchReport(
        symbol=symbol,
        asset_type=payload.asset_type,
        status=ResearchStatus.RUNNING,
        model=model,
        provider=provider,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    task = asyncio.create_task(
        _execute_research(
            report.id,
            provider,
            client,
            model,
            settings,
            market_data,
            news_client,
            payload,
            fallback_client,
            fallback_model,
        ),
        name=f"research-{report.id}",
    )
    # Keep a reference so the task isn't garbage collected mid-run.
    tasks: set[asyncio.Task[None]] = getattr(request.app.state, "research_tasks", set())
    tasks.add(task)
    task.add_done_callback(tasks.discard)
    request.app.state.research_tasks = tasks

    return ResearchReportRead.model_validate(report)


@router.get("/budget", response_model=ResearchBudget)
def get_budget(
    request: Request,
    settings: AppSettings = Depends(get_app_settings),
    db: Session = Depends(get_db_session),
) -> ResearchBudget:
    """Today's estimated Anthropic spend vs. the configured daily cap."""
    spent = _today_anthropic_cost(db)
    anthropic_available, groq_available = _availability(request, settings)

    if anthropic_available and spent < settings.research_daily_budget_usd:
        next_provider = "anthropic"
    elif groq_available:
        next_provider = "groq"
    else:
        next_provider = "disabled"

    return ResearchBudget(
        spent_usd=round(spent, 4),
        budget_usd=settings.research_daily_budget_usd,
        remaining_usd=round(max(0.0, settings.research_daily_budget_usd - spent), 4),
        next_run_provider=next_provider,
    )


@router.get("", response_model=list[ResearchReportSummary])
def list_research(
    settings: AppSettings = Depends(get_app_settings),
    db: Session = Depends(get_db_session),
) -> list[ResearchReportSummary]:
    """Recent reports only — anything older than `research_cache_days` has
    aged out of the shared-reuse window and drops off this list, but the
    row itself is retained; fetch it directly via GET /research/{id}.
    """
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
        days=settings.research_cache_days
    )
    reports = (
        db.query(ResearchReport)
        .filter(ResearchReport.created_at >= cutoff)
        .order_by(ResearchReport.created_at.desc())
        .limit(20)
        .all()
    )
    return [ResearchReportSummary.model_validate(r) for r in reports]


@router.get("/{report_id}", response_model=ResearchReportRead)
def get_research(
    report_id: int = Path(..., ge=1),
    db: Session = Depends(get_db_session),
) -> ResearchReportRead:
    # Rows are never deleted, only aged out of reuse/listing — so a report of
    # any age remains individually retrievable by id.
    report = db.get(ResearchReport, report_id)
    if report is None:
        raise NotFoundError("Research report not found.", details={"report_id": report_id})
    return ResearchReportRead.model_validate(report)
