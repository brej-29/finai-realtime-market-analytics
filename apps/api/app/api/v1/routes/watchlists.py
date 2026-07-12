from __future__ import annotations

from fastapi import APIRouter, Depends, Path

from sqlalchemy.orm import Session

from app.core.deps import get_db_session
from app.core.errors import BadRequestError, NotFoundError
from app.db.models import AssetType, Watchlist, WatchlistItem
from app.schemas.watchlists import (
    WatchlistCreate,
    WatchlistItemCreate,
    WatchlistItemDeleteResult,
    WatchlistItemRead,
    WatchlistRead,
)

router = APIRouter()


@router.post("", response_model=WatchlistRead, status_code=201)
def create_watchlist(
    payload: WatchlistCreate,
    db: Session = Depends(get_db_session),
) -> WatchlistRead:
    watchlist = Watchlist(name=payload.name)
    db.add(watchlist)
    db.commit()
    db.refresh(watchlist)
    return WatchlistRead.model_validate(watchlist)


@router.get("/default", response_model=WatchlistRead)
def get_or_create_default_watchlist(
    db: Session = Depends(get_db_session),
) -> WatchlistRead:
    """Return the shared default watchlist, creating it if it does not exist yet.

    The MVP is single-user, so the frontend works against one well-known
    watchlist instead of tracking IDs client-side.
    """
    watchlist = db.query(Watchlist).filter(Watchlist.name == "Default").order_by(Watchlist.id).first()
    if not watchlist:
        watchlist = Watchlist(name="Default")
        db.add(watchlist)
        db.commit()
        db.refresh(watchlist)
    items = [
        WatchlistItemRead.model_validate(item)
        for item in watchlist.items  # type: ignore[attr-defined]
    ]
    return WatchlistRead(
        id=watchlist.id,
        name=watchlist.name,
        created_at=watchlist.created_at,
        items=items,
    )


@router.get("/{watchlist_id}", response_model=WatchlistRead)
def get_watchlist(
    watchlist_id: int = Path(..., ge=1),
    db: Session = Depends(get_db_session),
) -> WatchlistRead:
    watchlist = db.get(Watchlist, watchlist_id)
    if not watchlist:
        raise NotFoundError("Watchlist not found.", details={"watchlist_id": watchlist_id})
    # Load items relationship
    items = [
        WatchlistItemRead.model_validate(item)
        for item in watchlist.items  # type: ignore[attr-defined]
    ]
    return WatchlistRead(
        id=watchlist.id,
        name=watchlist.name,
        created_at=watchlist.created_at,
        items=items,
    )


@router.post("/{watchlist_id}/items", response_model=WatchlistItemRead, status_code=201)
def add_watchlist_item(
    payload: WatchlistItemCreate,
    watchlist_id: int = Path(..., ge=1),
    db: Session = Depends(get_db_session),
) -> WatchlistItemRead:
    watchlist = db.get(Watchlist, watchlist_id)
    if not watchlist:
        raise NotFoundError("Watchlist not found.", details={"watchlist_id": watchlist_id})

    item = WatchlistItem(
        watchlist_id=watchlist_id,
        symbol=payload.symbol.upper(),
        asset_type=payload.asset_type or AssetType.STOCK,
    )
    db.add(item)
    try:
        db.commit()
    except Exception as exc:  # pragma: no cover - integrity-specific
        db.rollback()
        raise BadRequestError(
            "Failed to add watchlist item. It may already exist.",
            details={"symbol": payload.symbol, "asset_type": payload.asset_type.value},
        ) from exc

    db.refresh(item)
    return WatchlistItemRead.model_validate(item)


@router.delete("/{watchlist_id}/items/{item_id}", response_model=WatchlistItemDeleteResult)
def delete_watchlist_item(
    watchlist_id: int = Path(..., ge=1),
    item_id: int = Path(..., ge=1),
    db: Session = Depends(get_db_session),
) -> WatchlistItemDeleteResult:
    item = db.get(WatchlistItem, item_id)
    if not item or item.watchlist_id != watchlist_id:
        raise NotFoundError(
            "Watchlist item not found.",
            details={"watchlist_id": watchlist_id, "item_id": item_id},
        )
    db.delete(item)
    db.commit()
    return WatchlistItemDeleteResult(success=True, deleted_item_id=item_id)