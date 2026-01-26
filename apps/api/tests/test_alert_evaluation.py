from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.db.models import AlertDirection, AssetType
from app.schemas.alerts import AlertEvaluationResult
from app.schemas.common import Quote


def evaluate_alert(
    direction: AlertDirection,
    threshold: float,
    quote: Quote | None,
) -> AlertEvaluationResult:
    if quote is None:
        return AlertEvaluationResult(alert_id=1, triggered=False, current_price=None)

    if direction is AlertDirection.PRICE_ABOVE:
        triggered = quote.price >= threshold
    else:
        triggered = quote.price <= threshold

    return AlertEvaluationResult(alert_id=1, triggered=triggered, current_price=quote.price)


@pytest.mark.parametrize(
    "direction,price,threshold,expected",
    [
        (AlertDirection.PRICE_ABOVE, 110.0, 100.0, True),
        (AlertDirection.PRICE_ABOVE, 90.0, 100.0, False),
        (AlertDirection.PRICE_BELOW, 90.0, 100.0, True),
        (AlertDirection.PRICE_BELOW, 110.0, 100.0, False),
    ],
)
def test_alert_evaluation_logic(
    direction: AlertDirection,
    price: float,
    threshold: float,
    expected: bool,
) -> None:
    quote = Quote(
        symbol="TEST",
        asset_type=AssetType.STOCK,
        price=price,
        change_24h=None,
        ts=datetime.now(timezone.utc),
        is_stale=False,
    )
    result = evaluate_alert(direction, threshold, quote)
    assert result.triggered is expected