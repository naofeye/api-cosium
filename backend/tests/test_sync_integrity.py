"""Tests d'intégrité de synchronisation ERP → OptiFlow."""

from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.integrations.erp_models import ERPCustomer


def _make_mock_connector(erp_customers: list[ERPCustomer]) -> MagicMock:
    """Crée un mock du connecteur ERP avec les clients fournis."""
    connector = MagicMock()
    connector.erp_type = "cosium"
    connector.authenticate = MagicMock()
    connector.get_customers.return_value = erp_customers
    return connector


@patch("app.services.erp_sync_service.get_connector")
def test_sync_creates_correct_customers(mock_get_connector: MagicMock, client: TestClient, auth_headers: dict) -> None:
    """After sync, customers should exist in OptiFlow with correct data."""
    erp_customers = [
        ERPCustomer(erp_id="1", first_name="Alice", last_name="Martin",
                    email="alice@test.com", phone="0600000001", city="Lyon", postal_code="69001"),
        ERPCustomer(erp_id="2", first_name="Bob", last_name="Durand",
                    email="bob@test.com"),
        ERPCustomer(erp_id="3", first_name="", last_name=""),
    ]
    mock_get_connector.return_value = _make_mock_connector(erp_customers)

    resp = client.post("/api/v1/sync/customers", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["created"] == 2  # 3rd skipped (empty name)
    assert data["skipped"] == 1
    assert data["total"] == 3


@patch("app.services.erp_sync_service.get_connector")
def test_sync_no_duplicates(mock_get_connector: MagicMock, client: TestClient, auth_headers: dict) -> None:
    """Running sync twice should not create duplicates."""
    erp_customers = [
        ERPCustomer(erp_id="1", first_name="Unique", last_name="Client",
                    email="unique@test.com"),
    ]
    mock_get_connector.return_value = _make_mock_connector(erp_customers)

    resp1 = client.post("/api/v1/sync/customers", headers=auth_headers)
    created1 = resp1.json()["created"]

    resp2 = client.post("/api/v1/sync/customers", headers=auth_headers)
    created2 = resp2.json()["created"]

    assert created1 == 1
    assert created2 == 0  # No duplicates


@patch("app.services.erp_sync_service.get_connector")
def test_sync_updates_missing_fields(mock_get_connector: MagicMock, client: TestClient, auth_headers: dict) -> None:
    """Sync should update empty fields on existing customers."""
    # First sync: create with email only
    erp_customers_v1 = [
        ERPCustomer(erp_id="1", first_name="Update", last_name="Test",
                    email="update@test.com"),
    ]
    mock_get_connector.return_value = _make_mock_connector(erp_customers_v1)
    client.post("/api/v1/sync/customers", headers=auth_headers)

    # Second sync: same person with phone now
    erp_customers_v2 = [
        ERPCustomer(erp_id="1", first_name="Update", last_name="Test",
                    email="update@test.com", phone="0699999999", city="Marseille"),
    ]
    mock_get_connector.return_value = _make_mock_connector(erp_customers_v2)
    resp = client.post("/api/v1/sync/customers", headers=auth_headers)
    assert resp.json()["updated"] >= 1
