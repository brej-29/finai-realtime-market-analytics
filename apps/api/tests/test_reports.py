from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_portfolio_pdf_report_generation() -> None:
    response = client.post("/api/v1/reports/portfolio.pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    # Basic sanity check on content length
    assert len(response.content) > 100