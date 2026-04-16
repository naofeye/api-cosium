"""Tests d'integration du service de sync factures Cosium → OptiFlow.

Couvre : sync full, sync incremental (avec date_from), absence de doublons, upsert.
Mock le connector ERP pour eviter tout appel reel a Cosium.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.integrations.erp_models import ERPInvoice


def _make_connector(invoices_by_date: list[ERPInvoice] | None = None,
                    invoices_full: list[ERPInvoice] | None = None) -> MagicMock:
    """Mock connector ERP : get_invoices / get_invoices_by_date_range."""
    connector = MagicMock()
    connector.erp_type = "cosium"
    connector.authenticate = MagicMock()
    connector.get_invoices.return_value = invoices_full or []
    connector.get_invoices_by_date_range.return_value = invoices_by_date or []
    return connector


def _invoice(erp_id: str, customer_name: str = "Dupont Jean",
             number: str = "F001", total: float = 100.0) -> ERPInvoice:
    return ERPInvoice(
        erp_id=erp_id,
        type="INVOICE",
        number=number,
        date=datetime.now(UTC),
        total_ttc=total,
        customer_erp_id="",
        customer_name=customer_name,
    )


@patch("app.services.erp_sync_invoices._authenticate_connector", MagicMock())
@patch("app.services.erp_sync_invoices._get_connector_for_tenant")
def test_sync_invoices_full_creates_records(
    mock_get: MagicMock, client: TestClient, auth_headers: dict, default_tenant
) -> None:
    """Sync full doit creer les factures retournees par get_invoices()."""
    invoices = [_invoice("100", number="F100"), _invoice("101", number="F101")]
    mock_get.return_value = (_make_connector(invoices_full=invoices), default_tenant)

    resp = client.post("/api/v1/sync/invoices?full=true", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["created"] == 2
    assert data["updated"] == 0


@patch("app.services.erp_sync_invoices._authenticate_connector", MagicMock())
@patch("app.services.erp_sync_invoices._get_connector_for_tenant")
def test_sync_invoices_no_duplicates(
    mock_get: MagicMock, client: TestClient, auth_headers: dict, default_tenant
) -> None:
    """Re-jouer une sync full avec les memes factures = 0 created, 2 updated."""
    invoices = [_invoice("200", number="F200"), _invoice("201", number="F201")]
    mock_get.return_value = (_make_connector(invoices_full=invoices), default_tenant)

    client.post("/api/v1/sync/invoices?full=true", headers=auth_headers)
    resp2 = client.post("/api/v1/sync/invoices?full=true", headers=auth_headers)
    data = resp2.json()
    assert data["created"] == 0
    assert data["updated"] == 2


@patch("app.services.erp_sync_invoices._authenticate_connector", MagicMock())
@patch("app.services.erp_sync_invoices._get_connector_for_tenant")
def test_sync_invoices_incremental_uses_date_range(
    mock_get: MagicMock, client: TestClient, auth_headers: dict, default_tenant
) -> None:
    """Apres une 1re sync, une 2e sync sans full=true doit appeler get_invoices_by_date_range."""
    initial = [_invoice("300", number="F300")]
    connector = _make_connector(invoices_full=initial, invoices_by_date=[])
    mock_get.return_value = (connector, default_tenant)
    client.post("/api/v1/sync/invoices?full=true", headers=auth_headers)
    connector.get_invoices_by_date_range.assert_not_called()

    new_invoice = _invoice("301", number="F301")
    connector.get_invoices_by_date_range.return_value = [new_invoice]
    resp = client.post("/api/v1/sync/invoices", headers=auth_headers)
    assert resp.status_code == 200
    connector.get_invoices_by_date_range.assert_called()
    args, _kwargs = connector.get_invoices_by_date_range.call_args
    assert "T00:00:00" in args[0]
    assert "T23:59:59" in args[1]


@patch("app.services.erp_sync_invoices._authenticate_connector", MagicMock())
@patch("app.services.erp_sync_invoices._get_connector_for_tenant")
def test_sync_invoices_upserts_updated_fields(
    mock_get: MagicMock, client: TestClient, auth_headers: dict, default_tenant
) -> None:
    """Un second appel avec total_ttc modifie doit mettre a jour la ligne existante."""
    inv_v1 = _invoice("400", number="F400", total=100.0)
    mock_get.return_value = (_make_connector(invoices_full=[inv_v1]), default_tenant)
    client.post("/api/v1/sync/invoices?full=true", headers=auth_headers)

    inv_v2 = _invoice("400", number="F400", total=250.5)
    mock_get.return_value = (_make_connector(invoices_full=[inv_v2]), default_tenant)
    resp = client.post("/api/v1/sync/invoices?full=true", headers=auth_headers)
    data = resp.json()
    assert data["created"] == 0
    assert data["updated"] == 1
