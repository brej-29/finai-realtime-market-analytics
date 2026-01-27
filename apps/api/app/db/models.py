from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AssetType(str, enum.Enum):
    STOCK = "stock"
    CRYPTO = "crypto"


class AlertDirection(str, enum.Enum):
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    RSI_ABOVE = "rsi_above"
    RSI_BELOW = "rsi_below"
    MA_CROSS = "ma_cross"


class AlertEventStatus(str, enum.Enum):
    NEW = "new"
    DELIVERED = "delivered"
    ERROR = "error"


class Watchlist(Base):
    __tablename__ = "watchlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(length=100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    items: Mapped[list["WatchlistItem"]] = relationship(
        "WatchlistItem",
        back_populates="watchlist",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"
    __table_args__ = (
        UniqueConstraint(
            "watchlist_id",
            "symbol",
            "asset_type",
            name="uq_watchlist_symbol_asset_type",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    watchlist_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("watchlists.id", ondelete="CASCADE"),
        nullable=False,
    )
    symbol: Mapped[str] = mapped_column(String(length=50), nullable=False)
    asset_type: Mapped[AssetType] = mapped_column(
        Enum(AssetType, name="asset_type_enum", native_enum=False),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    watchlist: Mapped[Watchlist] = relationship("Watchlist", back_populates="items")


class Holding(Base):
    __tablename__ = "holdings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(length=50), nullable=False)
    asset_type: Mapped[AssetType] = mapped_column(
        Enum(AssetType, name="holding_asset_type_enum", native_enum=False),
        nullable=False,
    )
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    average_price: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(length=50), nullable=False)
    asset_type: Mapped[AssetType] = mapped_column(
        Enum(AssetType, name="alert_asset_type_enum", native_enum=False),
        nullable=False,
    )
    direction: Mapped[AlertDirection] = mapped_column(
        Enum(AlertDirection, name="alert_direction_enum", native_enum=False),
        nullable=False,
    )
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    events: Mapped[list["AlertEvent"]] = relationship(
        "AlertEvent",
        back_populates="alert",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    alert_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("alerts.id", ondelete="CASCADE"),
        nullable=False,
    )
    fired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    message: Mapped[str] = mapped_column(String(length=255), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[AlertEventStatus] = mapped_column(
        Enum(AlertEventStatus, name="alert_event_status_enum", native_enum=False),
        default=AlertEventStatus.NEW,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    alert: Mapped[Alert] = relationship("Alert", back_populates="events")