from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query

from sqlalchemy.orm import Session

from app.core.deps import get_db_session, get_market_data_service
from app.core.errors import NotFoundError
from app.db.models import Alert, AlertDirection, AlertEvent
from app.schemas.alerts import (
    AlertCreate,
    AlertEvaluationResult,
    AlertEventRead,
    AlertRead,
)
from app.services.market_data.service import MarketDataService

router = APIRouter()


@router.post("", response_model=AlertRead, status_code=201)
def create_alert(
    payload: AlertCreate,
    db: Session = Depends(get_db_session),
) -> AlertRead:
    alert = Alert(
        symbol=payload.symbol.upper(),
        asset_type=payload.asset_type,
        direction=payload.direction,
        threshold=payload.threshold,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return AlertRead.model_validate(alert)


@router.get("", response_model=list[AlertRead])
def list_alerts(
    db: Session = Depends(get_db_session),
) -> list[AlertRead]:
    alerts = db.query(Alert).order_by(Alert.created_at.desc()).all()
    return [AlertRead.model_validate(a) for a in alerts]


@router.get("/events", response_model=list[AlertEventRead])
def list_alert_events(
    db: Session = Depends(get_db_session),
    limit: int = Query(
        50,
        ge=1,
        le=200,
        description="Maximum number of recent events to return.",
    ),
) -> list[AlertEventRead]:
    """Return recent alert events, newest first."""
    query = (
        db.query(AlertEvent, Alert)
        .join(Alert, AlertEvent.alert_id == Alert.id)
        .order_by(AlertEvent.fired_at.desc())
        .limit(limit)
    )
    rows = query.all()

    results: list[AlertEventRead] = []
    for event, alert in rows:
        results.append(
            AlertEventRead(
                id=event.id,
                alert_id=event.alert_id,
                symbol=alert.symbol,
                asset_type=alert.asset_type,
                direction=alert.direction,
                message=event.message,
                fired_at=event.fired_at,
                status=event.status,
                payload=event.payload,
            )
        )
    return results


@router.post("/{alert_id}/test-evaluate", response_model=AlertEvaluationResult)
async def test_evaluate_alert(
    alert_id: int = Path(..., ge=1),
    db: Session = Depends(get_db_session),
    market_data: MarketDataService = Depends(get_market_data_service),
) -> AlertEvaluationResult:
    alert = db.get(Alert, alert_id)
    if not alert:
        raise NotFoundError("Alert not found.", details={"alert_id": alert_id})

    quotes = await market_data.get_quotes(asset_type=alert.asset_type, symbols=[alert.symbol])
    current_price = quotes[0].price if quotes else None

    if current_price is None:
        return AlertEvaluationResult(alert_id=alert.id, triggered=False, current_price=None)

    if alert.direction is AlertDirection.PRICE_ABOVE:
        triggered = current_price >= alert.threshold
    elif alert.direction is AlertDirection.PRICE_BELOW:
        triggered = current_price <= alert.threshold
    elif alert.direction is AlertDirection.RSI_ABOVE:
        # For test-evaluate, only price-based evaluation is performed.
        triggered = False
    elif alert.direction is AlertDirection.RSI_BELOW:
        triggered = False
    else:
        # MA_CROSS and other technical alerts are evaluated by the scheduler.
        triggered = False

    return AlertEvaluationResult(alert_id=alert.id, triggered=triggered, current_price=current_price)