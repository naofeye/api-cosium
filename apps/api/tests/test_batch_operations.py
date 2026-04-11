"""Tests for batch PEC operations (OptiSante)."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.models.batch_operation import BatchOperation, BatchOperationItem
from app.models.client import Customer
from app.models.cosium_reference import CosiumCustomerTag, CosiumTag
from app.models.tenant import Tenant


_tag_counter = 0


def _seed_tags_and_clients(db, tenant_id: int, tag_code: str = "SAFRAN", count: int = 3):
    """Create customers linked to a marketing code via CosiumCustomerTag."""
    global _tag_counter
    _tag_counter += 1

    # Create tag
    tag = CosiumTag(
        tenant_id=tenant_id,
        cosium_id=9000 + _tag_counter,
        code=tag_code,
        description=f"Tag {tag_code}",
    )
    db.add(tag)
    db.flush()

    customers = []
    for i in range(count):
        c = Customer(
            tenant_id=tenant_id,
            first_name=f"Client{i}",
            last_name=f"Batch{i}",
            cosium_id=str(5000 + i),
        )
        db.add(c)
        db.flush()
        customers.append(c)

        ct = CosiumCustomerTag(
            tenant_id=tenant_id,
            customer_id=c.id,
            customer_cosium_id=str(5000 + i),
            tag_code=tag_code,
        )
        db.add(ct)

    db.commit()
    return customers


def test_get_available_marketing_codes(db, client: TestClient, auth_headers: dict, default_tenant: Tenant):
    """Marketing codes endpoint returns tags with counts."""
    _seed_tags_and_clients(db, default_tenant.id, "SAFRAN", 3)
    _seed_tags_and_clients(db, default_tenant.id, "PROMO_HIVER", 2)

    resp = client.get("/api/v1/batch/marketing-codes", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2

    codes = {item["code"]: item["client_count"] for item in data}
    assert codes["SAFRAN"] == 3
    assert codes["PROMO_HIVER"] == 2


def test_create_batch(db, client: TestClient, auth_headers: dict, default_tenant: Tenant):
    """Create batch creates operation + items for each client."""
    _seed_tags_and_clients(db, default_tenant.id, "SAFRAN", 4)

    resp = client.post(
        "/api/v1/batch/create",
        json={"marketing_code": "SAFRAN", "label": "Journee SAFRAN 06/04"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["marketing_code"] == "SAFRAN"
    assert data["total_clients"] == 4
    assert data["status"] == "en_cours"

    # Verify items were created
    items = db.query(BatchOperationItem).filter(
        BatchOperationItem.batch_id == data["id"]
    ).all()
    assert len(items) == 4
    assert all(i.status == "en_attente" for i in items)


@patch("app.services.batch_operation_service.consolidation_service.consolidate_client_for_pec")
def test_process_batch_consolidates_all(mock_consolidate, db, client: TestClient, auth_headers: dict, default_tenant: Tenant):
    """Process batch consolidates all clients."""
    from app.domain.schemas.consolidation import ConsolidatedClientProfile

    _seed_tags_and_clients(db, default_tenant.id, "SAFRAN", 2)

    # Create the batch
    resp = client.post(
        "/api/v1/batch/create",
        json={"marketing_code": "SAFRAN"},
        headers=auth_headers,
    )
    batch_id = resp.json()["id"]

    # Mock consolidation to return a profile with good score
    mock_profile = ConsolidatedClientProfile(score_completude=85.0, alertes=[])
    mock_consolidate.return_value = mock_profile

    resp = client.post(f"/api/v1/batch/{batch_id}/process", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "termine"
    assert data["clients_prets"] == 2
    assert mock_consolidate.call_count == 2


@patch("app.services.batch_operation_service.consolidation_service.consolidate_client_for_pec")
def test_process_batch_handles_errors(mock_consolidate, db, client: TestClient, auth_headers: dict, default_tenant: Tenant):
    """Process batch handles individual client errors gracefully."""
    from app.domain.schemas.consolidation import ConsolidatedClientProfile

    _seed_tags_and_clients(db, default_tenant.id, "ERR", 3)

    resp = client.post(
        "/api/v1/batch/create",
        json={"marketing_code": "ERR"},
        headers=auth_headers,
    )
    batch_id = resp.json()["id"]

    # First call succeeds, second raises, third succeeds
    good_profile = ConsolidatedClientProfile(score_completude=90.0, alertes=[])
    mock_consolidate.side_effect = [
        good_profile,
        ValueError("Consolidation failed"),
        good_profile,
    ]

    resp = client.post(f"/api/v1/batch/{batch_id}/process", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "termine"
    assert data["clients_prets"] == 2
    assert data["clients_erreur"] == 1


@patch("app.services.batch_operation_service.pec_preparation_service.prepare_pec")
@patch("app.services.batch_operation_service.consolidation_service.consolidate_client_for_pec")
def test_prepare_batch_pec(mock_consolidate, mock_prepare, db, client: TestClient, auth_headers: dict, default_tenant: Tenant):
    """Prepare batch PEC creates PEC for pret items."""
    from unittest.mock import MagicMock

    from app.domain.schemas.consolidation import ConsolidatedClientProfile

    _seed_tags_and_clients(db, default_tenant.id, "PEC", 2)

    # Create and process
    resp = client.post(
        "/api/v1/batch/create",
        json={"marketing_code": "PEC"},
        headers=auth_headers,
    )
    batch_id = resp.json()["id"]

    mock_consolidate.return_value = ConsolidatedClientProfile(
        score_completude=90.0, alertes=[]
    )
    client.post(f"/api/v1/batch/{batch_id}/process", headers=auth_headers)

    # Mock prepare_pec
    mock_resp = MagicMock()
    mock_resp.id = 100
    mock_prepare.return_value = mock_resp

    resp = client.post(f"/api/v1/batch/{batch_id}/prepare-pec", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["prepared"] == 2
    assert data["errors"] == 0


def test_get_batch_summary(db, client: TestClient, auth_headers: dict, default_tenant: Tenant):
    """Get batch summary returns correct stats."""
    _seed_tags_and_clients(db, default_tenant.id, "SUM", 2)

    resp = client.post(
        "/api/v1/batch/create",
        json={"marketing_code": "SUM", "label": "Summary test"},
        headers=auth_headers,
    )
    batch_id = resp.json()["id"]

    resp = client.get(f"/api/v1/batch/{batch_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["batch"]["id"] == batch_id
    assert data["batch"]["label"] == "Summary test"
    assert len(data["items"]) == 2
    assert all(item["status"] == "en_attente" for item in data["items"])
    # Verify customer names are populated
    assert all(item["customer_name"] is not None for item in data["items"])


def test_invalid_marketing_code_returns_empty(db, client: TestClient, auth_headers: dict):
    """Invalid marketing code returns an empty batch."""
    resp = client.post(
        "/api/v1/batch/create",
        json={"marketing_code": "NONEXISTENT_CODE"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["total_clients"] == 0


def test_batch_endpoint_requires_auth(client: TestClient):
    """Batch endpoints require authentication."""
    resp = client.get("/api/v1/batch/marketing-codes")
    assert resp.status_code == 401

    resp = client.post("/api/v1/batch/create", json={"marketing_code": "X"})
    assert resp.status_code == 401

    resp = client.get("/api/v1/batch/1")
    assert resp.status_code == 401

    resp = client.post("/api/v1/batch/1/process")
    assert resp.status_code == 401
