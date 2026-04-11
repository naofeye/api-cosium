"""Tests for Cosium integration — security + mock sync."""

import inspect
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.integrations.cosium.client import CosiumClient

# ===== SECURITY TESTS =====

def test_cosium_client_has_no_put_method() -> None:
    """The CosiumClient must NOT have a put() method."""
    assert not hasattr(CosiumClient, "put"), "CosiumClient must NOT have a put() method"


def test_cosium_client_has_no_delete_method() -> None:
    """The CosiumClient must NOT have a delete() method."""
    assert not hasattr(CosiumClient, "delete"), "CosiumClient must NOT have a delete() method"


def test_cosium_client_has_no_patch_method() -> None:
    """The CosiumClient must NOT have a patch() method."""
    assert not hasattr(CosiumClient, "patch"), "CosiumClient must NOT have a patch() method"


def test_cosium_client_has_no_generic_post() -> None:
    """The CosiumClient must NOT have a generic post() method (only authenticate)."""
    assert not hasattr(CosiumClient, "post"), "CosiumClient must NOT have a generic post() method"


def test_cosium_client_has_no_request_method() -> None:
    """The CosiumClient must NOT have a generic request() method."""
    assert not hasattr(CosiumClient, "request"), "CosiumClient must NOT have a generic request() method"


def test_cosium_client_has_no_send_method() -> None:
    """The CosiumClient must NOT have a send() method."""
    assert not hasattr(CosiumClient, "send"), "CosiumClient must NOT have a generic send() method"


def test_cosium_client_only_allowed_methods() -> None:
    """The CosiumClient must only have authenticate(), get(), get_paginated(), and get_raw() as public methods."""
    allowed = {"authenticate", "get", "get_paginated", "get_raw"}
    public_methods = {
        name for name, method in inspect.getmembers(CosiumClient, predicate=inspect.isfunction)
        if not name.startswith("_")
    }
    forbidden = public_methods - allowed
    assert not forbidden, f"CosiumClient has forbidden public methods: {forbidden}"


def test_cosium_client_authenticate_uses_only_post() -> None:
    """Verify that authenticate sub-methods use httpx.post (the only allowed POST)."""
    basic_source = inspect.getsource(CosiumClient._authenticate_basic)
    oidc_source = inspect.getsource(CosiumClient._authenticate_oidc)
    for label, source in [("basic", basic_source), ("oidc", oidc_source)]:
        assert "self._client.post" in source, f"{label} auth must use self._client.post"
        assert "self._client.put" not in source, f"{label} auth must not use put"
        assert "self._client.delete" not in source, f"{label} auth must not use delete"
        assert "self._client.patch" not in source, f"{label} auth must not use patch"


def test_cosium_client_get_uses_only_get() -> None:
    """Verify that get uses httpx.get (only allowed read method)."""
    source = inspect.getsource(CosiumClient.get)
    assert "self._client.get" in source, "get must use self._client.get"
    assert "self._client.post" not in source
    assert "self._client.put" not in source
    assert "self._client.delete" not in source
    assert "self._client.patch" not in source


# ===== FUNCTIONAL TESTS (with mocks) =====

def test_sync_status(client: TestClient, auth_headers: dict) -> None:
    resp = client.get("/api/v1/sync/status", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "configured" in data
    assert "authenticated" in data


@patch("app.services.erp_auth_service.get_connector")
def test_sync_customers_mock(mock_get_connector: MagicMock, client: TestClient, auth_headers: dict) -> None:
    mock_connector = MagicMock()
    mock_connector.erp_type = "cosium"
    mock_get_connector.return_value = mock_connector

    from app.integrations.erp_models import ERPCustomer
    mock_connector.get_customers.return_value = [
        ERPCustomer(erp_id="1", first_name="Jean", last_name="Cosium",
                    email="jean@cosium.test", phone="0600000001",
                    address="1 rue Test", city="Paris", postal_code="75001"),
        ERPCustomer(erp_id="2", first_name="Marie", last_name="Cosium",
                    email="marie@cosium.test"),
    ]

    resp = client.post("/api/v1/sync/customers", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["created"] >= 1
    assert data["total"] == 2


@patch("app.services.erp_auth_service.get_connector")
def test_sync_invoices_mock(mock_get_connector: MagicMock, client: TestClient, auth_headers: dict) -> None:
    mock_connector = MagicMock()
    mock_connector.erp_type = "cosium"
    mock_get_connector.return_value = mock_connector

    from app.integrations.erp_models import ERPInvoice
    mock_connector.get_invoices.return_value = [
        ERPInvoice(erp_id="1", type="INVOICE", number="INV-001", total_ttc=500),
    ]
    mock_connector.get_invoices_by_date_range = MagicMock(return_value=[
        ERPInvoice(erp_id="1", type="INVOICE", number="INV-001", total_ttc=500),
    ])
    resp = client.post("/api/v1/sync/invoices", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 0


@patch("app.services.erp_auth_service.get_connector")
def test_sync_products_mock(mock_get_connector: MagicMock, client: TestClient, auth_headers: dict) -> None:
    mock_connector = MagicMock()
    mock_connector.erp_type = "cosium"
    mock_get_connector.return_value = mock_connector

    from app.integrations.erp_models import ERPProduct
    mock_connector.get_products.return_value = [
        ERPProduct(erp_id="1", code="PROD-001", label="Monture Ray-Ban"),
    ]
    resp = client.post("/api/v1/sync/products", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 0
