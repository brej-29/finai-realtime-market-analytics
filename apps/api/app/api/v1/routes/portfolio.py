from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends

from sqlalchemy.orm import Session

from app.core.deps import get_db_session, get_market_data_service
from app.core.errors import ProviderError
from app.db.models import AssetType, Holding
from app.schemas.portfolio import HoldingCreate, HoldingRead, PortfolioSummary, PortfolioSummaryByType
from app.services.market_data.service import MarketDataService

router = APIRouter()


@router.post("/holdings", response_model=HoldingRead, status_code=201)
def create_holding(
    payload: HoldingCreate,
    db: Session = Depends(get_db_session),
) -> HoldingRead:
    holding = Holding(
        symbol=payload.symbol.upper(),
        asset_type=payload.asset_type,
        quantity=payload.quantity,
        average_price=payload.average_price,
    )
    db.add(holding)
    db.commit()
    db.refresh(holding)
    return HoldingRead.model_validate(holding)


@router.get("/holdings", response_model=list[HoldingRead])
def list_holdings(
    db: Session = Depends(get_db_session),
) -> list[HoldingRead]:
    holdings = db.query(Holding).all()
    return [HoldingRead.model_validate(h) for h in holdings]


@router.get("/portfolio/summary", response_model=PortfolioSummary)
async def get_portfolio_summary(
    db: Session = Depends(get_db_session),
    market_data: MarketDataService = Depends(get_market_data_service),
) -> PortfolioSummary:
    holdings: list[Holding] = db.query(Holding).all()

    if not holdings:
        return PortfolioSummary(
            total_cost_basis=0.0,
            total_market_value=0.0,
            total_unrealized_pnl=0.0,
            by_asset_type={},
        )

    # Group holdings by asset type and collect symbols
    by_type: dict[AssetType, list[Holding]] = defaultdict(list)
    for h in holdings:
        by_type[h.asset_type].append(h)

    quotes_by_key: dict[tuple[AssetType, str], float] = {}
    for asset_type, type_holdings in by_type.items():
        symbols = {h.symbol for h in type_holdings}
        try:
            quotes = await market_data.get_quotes(asset_type=asset_type, symbols=list(symbols))
        except ProviderError:
            # Degrade gracefully: positions without a live quote fall back to
            # their average price below, so the summary still renders.
            continue
        for quote in quotes:
            quotes_by_key[(quote.asset_type, quote.symbol)] = quote.price

    total_cost_basis = 0.0
    total_market_value = 0.0
    summary_by_type: dict[AssetType, PortfolioSummaryByType] = {}

    # First pass: compute cost basis and market value by type
    for asset_type, type_holdings in by_type.items():
        cost_basis = 0.0
        market_value = 0.0
        for h in type_holdings:
            position_cost = h.quantity * h.average_price
            cost_basis += position_cost
            price = quotes_by_key.get((h.asset_type, h.symbol), h.average_price)
            market_value += h.quantity * price

        total_cost_basis += cost_basis
        total_market_value += market_value
        summary_by_type[asset_type] = PortfolioSummaryByType(
            asset_type=asset_type,
            cost_basis=cost_basis,
            market_value=market_value,
            unrealized_pnl=market_value - cost_basis,
            weight=None,  # filled in below
        )

    # Second pass: compute weights
    for asset_type, summary in summary_by_type.items():
        if total_market_value > 0:
            summary.weight = summary.market_value / total_market_value
        else:
            summary.weight = 0.0

    total_unrealized_pnl = total_market_value - total_cost_basis

    return PortfolioSummary(
        total_cost_basis=total_cost_basis,
        total_market_value=total_market_value,
        total_unrealized_pnl=total_unrealized_pnl,
        by_asset_type=summary_by_type,
    )