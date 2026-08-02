from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Tuple

from sqlalchemy.orm import Session

from app.core.config import AppSettings
from app.core.logging import get_logger
from app.db.models import (
    Alert,
    AlertDirection,
    AlertEvent,
    AlertEventStatus,
    AssetType,
)
from app.db.session import SessionLocal
from app.schemas.common import HistoricalBar
from app.services.analytics.indicators import compute_simple_rsi, moving_average
from app.services.market_data.service import MarketDataService
from app.services.realtime.manager import RealtimeManager

logger = get_logger("app.services.alerts.scheduler")


class AlertScheduler:
    """Evaluate active alerts periodically and push in-app notifications."""

    def __init__(
        self,
        market_data_service: MarketDataService,
        realtime_manager: RealtimeManager,
        settings: AppSettings,
    ) -> None:
        self.market_data_service = market_data_service
        self.realtime_manager = realtime_manager
        self.settings = settings

    async def evaluate_alerts(self) -> None:
        """Evaluate all active alerts and create events when triggered."""
        db: Session = SessionLocal()
        try:
            alerts: List[Alert] = (
                db.query(Alert)
                .filter(Alert.is_active.is_(True))
                .order_by(Alert.created_at.asc())
                .all()
            )
            if not alerts:
                return

            quotes_by_key = await self._fetch_quotes(alerts)
            history_by_key = await self._fetch_history(alerts)

            now = datetime.now(timezone.utc)
            new_events: List[AlertEvent] = []

            for alert in alerts:
                key = (alert.asset_type, alert.symbol.upper())
                current_price = quotes_by_key.get(key)

                bars = history_by_key.get(key, [])
                closes = [b.close for b in bars]

                triggered, message, payload = self._evaluate_single_alert(
                    alert=alert,
                    current_price=current_price,
                    closes=closes,
                    bars=bars,
                )
                if not triggered:
                    continue

                if not self._should_create_event(db, alert, now):
                    continue

                event_payload = {
                    "symbol": alert.symbol,
                    "asset_type": alert.asset_type.value,
                    "direction": alert.direction.value,
                    "threshold": alert.threshold,
                    "current_price": current_price,
                    **payload,
                }

                event = AlertEvent(
                    alert_id=alert.id,
                    fired_at=now,
                    message=message,
                    payload=event_payload,
                    status=AlertEventStatus.NEW,
                )
                db.add(event)
                new_events.append(event)

            if not new_events:
                return

            db.commit()

            # Broadcast over WebSocket and mark as delivered.
            for event in new_events:
                payload = {
                    "type": "alert",
                    "alertId": event.alert_id,
                    "symbol": event.payload.get("symbol"),
                    "assetType": event.payload.get("asset_type"),
                    "message": event.message,
                    "ts": event.fired_at.isoformat(),
                }
                try:
                    # ponytail: fans out to every connected client regardless
                    # of workspace - fine while alert data is not sensitive,
                    # upgrade path is per-workspace broadcast channels if it
                    # ever holds private data.
                    await self.realtime_manager.broadcast_alert(payload)
                    event.status = AlertEventStatus.DELIVERED
                except Exception as exc:  # pragma: no cover - best-effort logging
                    logger.warning(
                        "Failed to broadcast alert event",
                        extra={
                            "alert_id": event.alert_id,
                            "event_id": event.id,
                            "error": str(exc),
                        },
                    )
                    event.status = AlertEventStatus.ERROR

            db.commit()
        finally:
            db.close()

    async def _fetch_quotes(self, alerts: Iterable[Alert]) -> Dict[Tuple[AssetType, str], float]:
        """Fetch latest prices needed for alert evaluation."""
        symbols_by_type: Dict[AssetType, List[str]] = {}
        for alert in alerts:
            symbols_by_type.setdefault(alert.asset_type, []).append(alert.symbol.upper())

        quotes_by_key: Dict[Tuple[AssetType, str], float] = {}
        for asset_type, symbols in symbols_by_type.items():
            unique_symbols = sorted(set(symbols))
            try:
                quotes = await self.market_data_service.get_quotes(
                    asset_type=asset_type,
                    symbols=unique_symbols,
                )
            except Exception as exc:  # pragma: no cover - logged and skipped
                logger.warning(
                    "Error fetching quotes for alert evaluation",
                    extra={"asset_type": asset_type.value, "error": str(exc)},
                )
                continue

            for q in quotes:
                quotes_by_key[(q.asset_type, q.symbol.upper())] = q.price

        return quotes_by_key

    async def _fetch_history(
        self,
        alerts: Iterable[Alert],
    ) -> Dict[Tuple[AssetType, str], List[HistoricalBar]]:
        """Fetch recent history for RSI / MA-based alerts."""
        keys: set[Tuple[AssetType, str]] = set()
        for alert in alerts:
            if alert.direction in (
                AlertDirection.RSI_ABOVE,
                AlertDirection.RSI_BELOW,
                AlertDirection.MA_CROSS,
            ):
                keys.add((alert.asset_type, alert.symbol.upper()))

        history_by_key: Dict[Tuple[AssetType, str], List[HistoricalBar]] = {}
        if not keys:
            return history_by_key

        for asset_type, symbol in keys:
            try:
                bars = await self.market_data_service.get_history(
                    asset_type=asset_type,
                    symbol=symbol,
                    interval="1h",
                    range_="1d",
                )
                history_by_key[(asset_type, symbol)] = bars
            except Exception as exc:  # pragma: no cover - logged and skipped
                logger.warning(
                    "Error fetching history for alert evaluation",
                    extra={"asset_type": asset_type.value, "symbol": symbol, "error": str(exc)},
                )
                continue

        return history_by_key

    def _evaluate_single_alert(
        self,
        alert: Alert,
        current_price: float | None,
        closes: List[float],
        bars: List[HistoricalBar],
    ) -> Tuple[bool, str, Dict[str, object]]:
        """Return (triggered, message, extra_payload)."""
        payload: Dict[str, object] = {}

        if alert.direction is AlertDirection.PRICE_ABOVE:
            if current_price is None:
                return False, "", payload
            triggered = current_price >= alert.threshold
            if not triggered:
                return False, "", payload
            message = (
                f"{alert.symbol} price {current_price:.2f} is above "
                f"threshold {alert.threshold:.2f}."
            )
            return True, message, payload

        if alert.direction is AlertDirection.PRICE_BELOW:
            if current_price is None:
                return False, "", payload
            triggered = current_price <= alert.threshold
            if not triggered:
                return False, "", payload
            message = (
                f"{alert.symbol} price {current_price:.2f} is below "
                f"threshold {alert.threshold:.2f}."
            )
            return True, message, payload

        if alert.direction in (AlertDirection.RSI_ABOVE, AlertDirection.RSI_BELOW):
            rsi = compute_simple_rsi(closes, period=self.settings.alerts_rsi_period)
            if rsi is None:
                return False, "", payload
            payload["rsi"] = rsi
            if alert.direction is AlertDirection.RSI_ABOVE:
                triggered = rsi >= alert.threshold
                if not triggered:
                    return False, "", payload
                message = (
                    f"{alert.symbol} RSI {rsi:.1f} is above threshold {alert.threshold:.1f}."
                )
            else:
                triggered = rsi <= alert.threshold
                if not triggered:
                    return False, "", payload
                message = (
                    f"{alert.symbol} RSI {rsi:.1f} is below threshold {alert.threshold:.1f}."
                )
            return True, message, payload

        if alert.direction is AlertDirection.MA_CROSS:
            short_window = self.settings.alerts_ma_short_window
            long_window = self.settings.alerts_ma_long_window
            if len(closes) < long_window + 2:
                return False, "", payload

            short_ma_prev = moving_average(closes[:-1], short_window)
            long_ma_prev = moving_average(closes[:-1], long_window)
            short_ma_curr = moving_average(closes, short_window)
            long_ma_curr = moving_average(closes, long_window)
            if (
                short_ma_prev is None
                or long_ma_prev is None
                or short_ma_curr is None
                or long_ma_curr is None
            ):
                return False, "", payload

            prev_diff = short_ma_prev - long_ma_prev
            curr_diff = short_ma_curr - long_ma_curr
            crossed_up = prev_diff <= 0 < curr_diff
            crossed_down = prev_diff >= 0 > curr_diff
            if not (crossed_up or crossed_down):
                return False, "", payload

            payload.update(
                {
                    "short_ma": short_ma_curr,
                    "long_ma": long_ma_curr,
                    "direction": "up" if crossed_up else "down",
                }
            )
            direction_text = "above" if crossed_up else "below"
            message = (
                f"{alert.symbol} short moving average crossed {direction_text} "
                f"the long moving average."
            )
            return True, message, payload

        # Unknown direction type
        return False, "", payload

    def _should_create_event(self, db: Session, alert: Alert, now: datetime) -> bool:
        """Throttle events so the same alert does not fire too frequently."""
        min_interval = timedelta(seconds=self.settings.alerts_min_event_interval_seconds)
        last_event: AlertEvent | None = (
            db.query(AlertEvent)
            .filter(AlertEvent.alert_id == alert.id)
            .order_by(AlertEvent.fired_at.desc())
            .first()
        )
        if last_event is None:
            return True
        return now - last_event.fired_at >= min_interval