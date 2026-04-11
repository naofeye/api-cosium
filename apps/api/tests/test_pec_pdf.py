"""Tests for PEC preparation PDF export endpoint."""

from fastapi.testclient import TestClient


def _create_client(client: TestClient, auth_headers: dict) -> int:
    resp = client.post(
        "/api/v1/clients",
        json={"first_name": "PecPdf", "last_name": "Test"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _create_preparation(client: TestClient, auth_headers: dict, customer_id: int) -> int:
    resp = client.post(
        f"/api/v1/clients/{customer_id}/pec-preparation",
        json={},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


class TestPecPdfEndpoint:
    def test_pec_pdf_returns_pdf_content_type(self, client: TestClient, auth_headers: dict) -> None:
        """PEC PDF export should return application/pdf content type."""
        cid = _create_client(client, auth_headers)
        pid = _create_preparation(client, auth_headers, cid)

        resp = client.get(
            f"/api/v1/pec-preparations/{pid}/export-pdf",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        # PDF magic bytes: %PDF
        assert resp.content[:5] == b"%PDF-"

    def test_pec_pdf_with_minimal_data_does_not_crash(self, client: TestClient, auth_headers: dict) -> None:
        """PEC PDF should generate successfully even with minimal client data (no phone, email, etc.)."""
        cid = _create_client(client, auth_headers)
        pid = _create_preparation(client, auth_headers, cid)

        resp = client.get(
            f"/api/v1/pec-preparations/{pid}/export-pdf",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert len(resp.content) > 100  # Non-trivial PDF content

    def test_pec_pdf_for_nonexistent_preparation_returns_404(self, client: TestClient, auth_headers: dict) -> None:
        """Requesting PDF for a non-existent preparation ID should return 404."""
        resp = client.get(
            "/api/v1/pec-preparations/999999/export-pdf",
            headers=auth_headers,
        )
        assert resp.status_code == 404
