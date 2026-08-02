"""Idempotent demo data seeding.

Populates a default watchlist, a sample portfolio, and a couple of alerts so a
fresh deployment shows a meaningful dashboard instead of empty tables.

Usage:
    python -m app.db.seed          # seed directly against DATABASE_URL
    SEED_DEMO_DATA=true            # or seed automatically on API startup

Seeding is skipped whenever any watchlist, holding, or alert already exists,
so it is safe to leave enabled on a long-lived deployment.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models import (
    Alert,
    AlertDirection,
    AssetType,
    Holding,
    Watchlist,
    WatchlistItem,
)

logger = get_logger("app.db.seed")

DEMO_WATCHLIST_ITEMS: list[tuple[str, AssetType]] = [
    ("AAPL", AssetType.STOCK),
    ("MSFT", AssetType.STOCK),
    ("NVDA", AssetType.STOCK),
    ("BTC", AssetType.CRYPTO),
    ("ETH", AssetType.CRYPTO),
]

DEMO_HOLDINGS: list[tuple[str, AssetType, float, float]] = [
    # (symbol, asset_type, quantity, average_price)
    ("AAPL", AssetType.STOCK, 10.0, 185.50),
    ("MSFT", AssetType.STOCK, 5.0, 402.00),
    ("NVDA", AssetType.STOCK, 8.0, 118.25),
    ("BTC", AssetType.CRYPTO, 0.05, 62000.00),
    ("ETH", AssetType.CRYPTO, 0.75, 3100.00),
]

DEMO_ALERTS: list[tuple[str, AssetType, AlertDirection, float]] = [
    ("AAPL", AssetType.STOCK, AlertDirection.PRICE_ABOVE, 260.0),
    ("BTC", AssetType.CRYPTO, AlertDirection.PRICE_BELOW, 50000.0),
    ("NVDA", AssetType.STOCK, AlertDirection.RSI_ABOVE, 70.0),
]


def seed_demo_data(db: Session, workspace_id: str = "demo") -> bool:
    """Seed demo data for a workspace if it has none. Returns True if data was created."""
    has_data = (
        db.query(Watchlist.id).filter(Watchlist.workspace_id == workspace_id).first() is not None
        or db.query(Holding.id).filter(Holding.workspace_id == workspace_id).first() is not None
        or db.query(Alert.id).filter(Alert.workspace_id == workspace_id).first() is not None
    )
    if has_data:
        logger.info("Demo seed skipped: workspace %s already contains data.", workspace_id)
        return False

    watchlist = Watchlist(name="Default", workspace_id=workspace_id)
    db.add(watchlist)
    db.flush()

    for symbol, asset_type in DEMO_WATCHLIST_ITEMS:
        db.add(
            WatchlistItem(
                watchlist_id=watchlist.id,
                symbol=symbol,
                asset_type=asset_type,
            )
        )

    for symbol, asset_type, quantity, average_price in DEMO_HOLDINGS:
        db.add(
            Holding(
                symbol=symbol,
                asset_type=asset_type,
                quantity=quantity,
                average_price=average_price,
                workspace_id=workspace_id,
            )
        )

    for symbol, asset_type, direction, threshold in DEMO_ALERTS:
        db.add(
            Alert(
                symbol=symbol,
                asset_type=asset_type,
                direction=direction,
                threshold=threshold,
                is_active=True,
                workspace_id=workspace_id,
            )
        )

    db.commit()
    logger.info(
        "Demo seed complete for workspace %s: 1 watchlist, %d items, %d holdings, %d alerts.",
        workspace_id,
        len(DEMO_WATCHLIST_ITEMS),
        len(DEMO_HOLDINGS),
        len(DEMO_ALERTS),
    )
    return True


def main() -> None:
    from app.db import models  # noqa: F401  # ensure models are registered
    from app.db.base import Base
    from app.db.session import SessionLocal, engine

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        created = seed_demo_data(db)
        print("Seeded demo data." if created else "Database not empty; nothing seeded.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
