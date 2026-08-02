from __future__ import annotations

import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.core.deps import get_db_session, get_market_data_service, get_workspace_id
from app.db.models import Holding
from app.schemas.portfolio import PortfolioSummary
from app.services.market_data.service import MarketDataService

router = APIRouter()


async def _compute_portfolio_summary(
    db: Session,
    market_data: MarketDataService,
    workspace_id: str,
) -> PortfolioSummary:
    from app.api.v1.routes.portfolio import get_portfolio_summary

    # Reuse existing summary logic for consistency.
    summary = await get_portfolio_summary(db=db, market_data=market_data, workspace_id=workspace_id)
    return summary


@router.post("/portfolio.pdf")
async def generate_portfolio_report(
    db: Session = Depends(get_db_session),
    market_data: MarketDataService = Depends(get_market_data_service),
    workspace_id: str = Depends(get_workspace_id),
) -> Response:
    """Generate a simple PDF portfolio report (holdings + metrics)."""
    holdings: list[Holding] = (
        db.query(Holding)
        .filter(Holding.workspace_id == workspace_id)
        .order_by(Holding.symbol.asc())
        .all()
    )
    summary = await _compute_portfolio_summary(db=db, market_data=market_data, workspace_id=workspace_id)

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    pdf.setTitle("Portfolio Report")
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(72, height - 72, "Portfolio Report")

    pdf.setFont("Helvetica", 10)
    pdf.drawString(72, height - 92, f"Generated at: {ts}")
    pdf.drawString(72, height - 106, "This report is for educational purposes only and is not investment advice.")

    # Summary metrics
    y = height - 140
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(72, y, "Summary")
    y -= 18
    pdf.setFont("Helvetica", 10)
    pdf.drawString(80, y, f"Total cost basis: ${summary.total_cost_basis:,.2f}")
    y -= 14
    pdf.drawString(80, y, f"Total market value: ${summary.total_market_value:,.2f}")
    y -= 14
    pdf.drawString(80, y, f"Unrealized P&L: ${summary.total_unrealized_pnl:,.2f}")

    # Holdings table
    y -= 32
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(72, y, "Holdings")
    y -= 18
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(72, y, "Symbol")
    pdf.drawString(140, y, "Asset")
    pdf.drawString(210, y, "Quantity")
    pdf.drawString(290, y, "Avg Price")
    y -= 14
    pdf.setFont("Helvetica", 10)

    if not holdings:
        pdf.drawString(72, y, "No holdings recorded.")
    else:
        for h in holdings:
            if y < 72:
                pdf.showPage()
                y = height - 72
                pdf.setFont("Helvetica", 10)
            pdf.drawString(72, y, h.symbol)
            pdf.drawString(140, y, h.asset_type.value)
            pdf.drawRightString(260, y, f"{h.quantity:.4f}")
            pdf.drawRightString(360, y, f"${h.average_price:,.2f}")
            y -= 14

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    content = buffer.getvalue()

    headers = {
        "Content-Disposition": 'attachment; filename="portfolio-report.pdf"',
        "Content-Type": "application/pdf",
    }
    return Response(content=content, media_type="application/pdf", headers=headers)