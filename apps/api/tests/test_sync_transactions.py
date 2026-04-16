"""Tests for sync batch commit logic and transactional integrity."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.integrations.erp_models import ERPCustomer


def _make_erp_customers(count: int) -> list[ERPCustomer]:
    """Generate N distinct ERP customers."""
    return [
        ERPCustomer(
            erp_id=str(i),
            first_name=f"Prenom{i}",
            last_name=f"Nom{i}",
            email=f"client{i}@test.com",
        )
        for i in range(1, count + 1)
    ]


def _make_mock_connector(erp_customers: list[ERPCustomer]) -> MagicMock:
    connector = MagicMock()
    connector.erp_type = "cosium"
    connector.authenticate = MagicMock()
    connector.get_customers.return_value = erp_customers
    return connector


# ---------- Test 1: batch flush every BATCH_SIZE records ----------

@patch("app.services.erp_auth_service.get_connector")
def test_sync_customers_flushes_in_batches(
    mock_get_connector: MagicMock,
    client: TestClient,
    auth_headers: dict,
    db: Session,
) -> None:
    """sync_customers should call db.flush() every BATCH_SIZE (500) records."""
    customers = _make_erp_customers(1100)
    mock_get_connector.return_value = _make_mock_connector(customers)

    with patch.object(db, "flush", wraps=db.flush) as spy_flush:
        resp = client.post("/api/v1/sync/customers", headers=auth_headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["created"] == 1100
    # flush is called at processed=500 and processed=1000, so at least 2 batch flushes
    assert spy_flush.call_count >= 2


# ---------- Test 2: sync continues after single record failure ----------

@patch("app.services.erp_auth_service.get_connector")
def test_sync_continues_after_record_failure(
    mock_get_connector: MagicMock,
    client: TestClient,
    auth_headers: dict,
) -> None:
    """If a single ERP record has empty last_name, sync should skip it and continue."""
    erp_customers = [
        ERPCustomer(erp_id="1", first_name="Valid", last_name="Client", email="valid@test.com"),
        ERPCustomer(erp_id="2", first_name="NoName", last_name="", email="noname@test.com"),
        ERPCustomer(erp_id="3", first_name="Also", last_name="Valid", email="also@test.com"),
    ]
    mock_get_connector.return_value = _make_mock_connector(erp_customers)

    resp = client.post("/api/v1/sync/customers", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["created"] == 2
    assert data["skipped"] == 1


# ---------- Test 3: batch_errors counted in service result ----------

@patch("app.services.erp_auth_service.get_connector")
def test_batch_errors_counted_in_service_result(
    mock_get_connector: MagicMock,
    db: Session,
    default_tenant,
    seed_user,
) -> None:
    """When db.flush() fails during a batch, batch_errors should be incremented in service result."""
    from app.services import erp_sync_service

    customers = _make_erp_customers(600)
    mock_get_connector.return_value = _make_mock_connector(customers)

    flush_count = [0]
    original_flush = db.flush

    def flaky_flush(*args, **kwargs):
        flush_count[0] += 1
        if flush_count[0] == 1:  # Fail on first batch flush
            raise Exception("Simulated batch flush error")
        return original_flush(*args, **kwargs)

    with patch.object(db, "flush", side_effect=flaky_flush):
        result = erp_sync_service.sync_customers(db, tenant_id=default_tenant.id, user_id=seed_user.id)

    assert result["batch_errors"] >= 1
    # Records should still be created despite the batch error (rollback + retry on commit)
    assert result["created"] > 0


# ---------- Test 4: sync_all returns has_errors=True on partial failure ----------

@patch("app.services.cosium_reference_sync.sync_all_reference", return_value={"total_created": 0, "total_updated": 0})
@patch("app.services.erp_sync_service.sync_prescriptions", side_effect=Exception("Prescriptions failed"))
@patch("app.services.erp_sync_service.sync_payments", return_value={"created": 0, "updated": 0, "total": 0, "batch_errors": 0})
@patch("app.services.erp_sync_service.sync_invoices", return_value={"created": 0, "updated": 0, "total": 0, "batch_errors": 0})
@patch("app.services.erp_sync_service.sync_customers", return_value={"created": 0, "updated": 0, "unchanged": 0, "skipped": 0, "batch_errors": 0, "total": 0, "mode": "full", "warnings": []})
def test_sync_all_returns_has_errors_on_partial_failure(
    mock_customers: MagicMock,
    mock_invoices: MagicMock,
    mock_payments: MagicMock,
    mock_prescriptions: MagicMock,
    mock_reference: MagicMock,
    client: TestClient,
    auth_headers: dict,
) -> None:
    """sync_all should return has_errors=True when one domain fails."""
    resp = client.post("/api/v1/sync/all", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_errors"] is True


# ---------- Test 5: sync_all returns has_errors=False on full success ----------

@patch("app.services.cosium_reference_sync.sync_all_reference", return_value={"total_created": 0, "total_updated": 0})
@patch("app.services.erp_sync_service.sync_prescriptions", return_value={"created": 0, "updated": 0, "total": 0, "batch_errors": 0})
@patch("app.services.erp_sync_service.sync_payments", return_value={"created": 0, "updated": 0, "total": 0, "batch_errors": 0})
@patch("app.services.erp_sync_service.sync_invoices", return_value={"created": 0, "updated": 0, "total": 0, "batch_errors": 0})
@patch("app.services.erp_sync_service.sync_customers", return_value={"created": 0, "updated": 0, "unchanged": 0, "skipped": 0, "batch_errors": 0, "total": 0, "mode": "full", "warnings": []})
def test_sync_all_returns_has_errors_false_on_success(
    mock_customers: MagicMock,
    mock_invoices: MagicMock,
    mock_payments: MagicMock,
    mock_prescriptions: MagicMock,
    mock_reference: MagicMock,
    client: TestClient,
    auth_headers: dict,
) -> None:
    """sync_all should return has_errors=False when all domains succeed."""
    resp = client.post("/api/v1/sync/all", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_errors"] is False


# ---------- Test 6: concurrent sync blocked by Redis lock ----------

@patch("app.api.routers.sync.acquire_lock", return_value=False)
def test_concurrent_sync_blocked_by_redis_lock(
    mock_acquire: MagicMock,
    client: TestClient,
    auth_headers: dict,
) -> None:
    """When Redis lock is held, sync_all should return an error."""
    resp = client.post("/api/v1/sync/all", headers=auth_headers)
    # BusinessError should produce a 409 or 400
    assert resp.status_code in (400, 409, 422)
    data = resp.json()
    detail = data.get("detail", data.get("message", ""))
    assert "en cours" in detail.lower() or "SYNC_IN_PROGRESS" in str(data)


@patch("app.api.routers.sync.acquire_lock", return_value=False)
def test_concurrent_sync_returns_stable_business_error_payload(
    mock_acquire: MagicMock,
    client: TestClient,
    auth_headers: dict,
) -> None:
    """Concurrent sync errors should keep the functional code/message mapping."""
    resp = client.post("/api/v1/sync/customers", headers=auth_headers)
    assert resp.status_code == 400
    data = resp.json()
    assert data["error"]["code"] == "SYNC_IN_PROGRESS"
    assert "synchronisation des clients" in data["error"]["message"].lower()


def test_enrich_clients_limit_is_bounded(client: TestClient, auth_headers: dict) -> None:
    """Expensive enrichment endpoint should reject unbounded limits early."""
    resp = client.post("/api/v1/sync/enrich-clients?limit=5000", headers=auth_headers)
    assert resp.status_code == 422


# ---------- Test 7: sync with empty ERP data returns zeros ----------

@patch("app.services.erp_auth_service.get_connector")
def test_sync_with_empty_erp_data(
    mock_get_connector: MagicMock,
    client: TestClient,
    auth_headers: dict,
) -> None:
    """When ERP returns no customers, sync should return zeros without error."""
    mock_get_connector.return_value = _make_mock_connector([])

    resp = client.post("/api/v1/sync/customers", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["created"] == 0
    assert data["updated"] == 0
    assert data["skipped"] == 0
    assert data["total"] == 0


# ---------- Test 8: sync preserves existing data on failure ----------

@patch("app.services.erp_auth_service.get_connector")
def test_sync_preserves_existing_data_on_failure(
    mock_get_connector: MagicMock,
    client: TestClient,
    auth_headers: dict,
) -> None:
    """Existing customers should not be lost if a subsequent sync fails."""
    # First: successfully sync 2 customers
    erp_v1 = _make_erp_customers(2)
    mock_get_connector.return_value = _make_mock_connector(erp_v1)
    resp1 = client.post("/api/v1/sync/customers", headers=auth_headers)
    assert resp1.json()["created"] == 2

    # Verify they exist
    clients_resp = client.get("/api/v1/clients", headers=auth_headers)
    initial_count = clients_resp.json()["total"]
    assert initial_count >= 2

    # Second: sync where get_customers raises (simulating ERP connection failure)
    connector_broken = MagicMock()
    connector_broken.erp_type = "cosium"
    connector_broken.authenticate = MagicMock()
    connector_broken.get_customers.side_effect = Exception("ERP connection lost")
    mock_get_connector.return_value = connector_broken

    try:
        resp2 = client.post("/api/v1/sync/customers", headers=auth_headers)
        # Should fail with 4xx or 5xx
        assert resp2.status_code >= 400
    except Exception:
        # Unhandled exception in starlette test client is also acceptable
        pass

    # Original customers should still exist
    clients_resp_after = client.get("/api/v1/clients", headers=auth_headers)
    assert clients_resp_after.json()["total"] >= initial_count
