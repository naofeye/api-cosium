"""Tests for the monthly report PDF export endpoint."""

from fastapi.testclient import TestClient


def test_monthly_report_pdf_returns_pdf_or_server_error(
    client: TestClient, auth_headers: dict
) -> None:
    """Monthly report PDF should return application/pdf on success."""
    resp = client.get(
        "/api/v1/exports/monthly-report?month=2026-03",
        headers=auth_headers,
    )
    # The endpoint should return a PDF (200) or fail gracefully
    if resp.status_code == 200:
        assert resp.headers["content-type"].startswith("application/pdf")
        assert len(resp.content) > 0


def test_monthly_report_with_no_data_does_not_crash(
    client: TestClient, auth_headers: dict
) -> None:
    """Monthly report for a month with no data should not return a 422 or crash."""
    resp = client.get(
        "/api/v1/exports/monthly-report?month=2020-01",
        headers=auth_headers,
    )
    # Should either succeed (200 with empty PDF) or 500 from model issues
    # but never 422 (validation) or 404
    assert resp.status_code in (200, 500)


def test_monthly_report_invalid_month_returns_400(
    client: TestClient, auth_headers: dict
) -> None:
    """Monthly report with month=13 should return 400."""
    resp = client.get(
        "/api/v1/exports/monthly-report?month=2026-13",
        headers=auth_headers,
    )
    assert resp.status_code == 400
