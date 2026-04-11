"""Tests for cosium_document_sync service."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from sqlalchemy.orm import Session

from app.integrations.cosium.cosium_connector import CosiumConnector
from app.models.client import Customer
from app.models.cosium_data import CosiumDocument
from app.models import Tenant
from app.services.cosium_document_sync import (
    get_sync_status,
    sync_customer_documents,
)

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _make_storage() -> MagicMock:
    s = MagicMock()
    s.ensure_bucket = MagicMock()
    s.upload_file = MagicMock()
    return s


# ---------- 1. skip already-downloaded docs ----------

def test_sync_customer_documents_skips_already_downloaded(db: Session, default_tenant: Tenant) -> None:
    """Documents already in DB should be counted as skipped, not re-downloaded."""
    tid = default_tenant.id
    connector = MagicMock()
    connector.get_customer_documents.return_value = [
        {"document_id": 100, "label": "ordonnance.pdf"},
        {"document_id": 200, "label": "attestation.pdf"},
    ]

    # Pre-insert doc 100 so it should be skipped
    db.add(CosiumDocument(
        tenant_id=tid, customer_cosium_id=42, cosium_document_id=100,
        name="ordonnance.pdf", content_type="application/pdf", size_bytes=10,
        minio_key="k", synced_at=_NOW,
    ))
    db.commit()

    connector.get_document_content.return_value = b"%PDF-fake"

    result = sync_customer_documents(
        db, tid, customer_cosium_id=42, connector=connector,
        storage=_make_storage(), delay_between_docs=0,
    )

    assert result["skipped"] == 1
    assert result["downloaded"] == 1
    assert result["errors"] == 0
    # Only doc 200 should have been fetched
    connector.get_document_content.assert_called_once_with(42, 200)


# ---------- 2. empty document list ----------

def test_sync_customer_documents_handles_empty_list(db: Session, default_tenant: Tenant) -> None:
    """An empty document list from Cosium should return zeros."""
    connector = MagicMock()
    connector.get_customer_documents.return_value = []

    result = sync_customer_documents(
        db, default_tenant.id, customer_cosium_id=99, connector=connector,
        storage=_make_storage(), delay_between_docs=0,
    )

    assert result == {"downloaded": 0, "skipped": 0, "errors": 0}
    connector.get_document_content.assert_not_called()


# ---------- 3. download error handled gracefully ----------

def test_sync_customer_documents_handles_download_error(db: Session, default_tenant: Tenant) -> None:
    """A download error for one doc should not abort the whole sync."""
    tid = default_tenant.id
    connector = MagicMock()
    connector.get_customer_documents.return_value = [
        {"document_id": 300, "label": "crash.pdf"},
        {"document_id": 301, "label": "ok.pdf"},
    ]
    # First call raises, second succeeds
    connector.get_document_content.side_effect = [
        Exception("Network timeout"),
        b"%PDF-ok",
    ]

    result = sync_customer_documents(
        db, tid, customer_cosium_id=50, connector=connector,
        storage=_make_storage(), delay_between_docs=0,
    )

    assert result["errors"] == 1
    assert result["downloaded"] == 1


# ---------- 4. sync_all_documents skips already-processed customers ----------

def test_sync_all_documents_skips_already_processed(db: Session, default_tenant: Tenant) -> None:
    """Customers that already have docs in DB should be skipped entirely."""
    tid = default_tenant.id

    # Create a customer with cosium_id
    cust = Customer(tenant_id=tid, cosium_id="77", first_name="Jean", last_name="Dupont")
    db.add(cust)
    db.flush()

    # Pre-insert a doc for this customer → should be skipped
    db.add(CosiumDocument(
        tenant_id=tid, customer_cosium_id=77, customer_id=cust.id,
        cosium_document_id=1, name="old.pdf", content_type="application/pdf",
        size_bytes=5, minio_key="k", synced_at=_NOW,
    ))
    db.commit()

    mock_connector = MagicMock(spec=CosiumConnector)
    mock_tenant_obj = MagicMock()

    with (
        patch("app.services.erp_sync_service._get_connector_for_tenant", return_value=(mock_connector, mock_tenant_obj)),
        patch("app.services.erp_sync_service._authenticate_connector"),
        patch("app.integrations.storage.storage"),
        patch("app.services.cosium_document_sync.sync_customer_documents") as mock_sync_cust,
    ):
        from app.services.cosium_document_sync import sync_all_documents

        result = sync_all_documents(
            db, tid, user_id=1, delay_between_customers=0, delay_between_docs=0,
        )

    # sync_customer_documents should NOT have been called because customer was already processed
    mock_sync_cust.assert_not_called()
    assert result["customers_processed"] == 1


# ---------- 5. get_sync_status returns correct counts ----------

def test_get_sync_status_returns_correct_counts(db: Session, default_tenant: Tenant) -> None:
    tid = default_tenant.id

    # Add 2 customers with cosium_id
    db.add(Customer(tenant_id=tid, cosium_id="10", first_name="A", last_name="B"))
    db.add(Customer(tenant_id=tid, cosium_id="20", first_name="C", last_name="D"))
    db.flush()

    # Add 3 docs for customer 10
    for i in range(3):
        db.add(CosiumDocument(
            tenant_id=tid, customer_cosium_id=10, cosium_document_id=i + 1,
            name=f"doc{i}.pdf", content_type="application/pdf",
            size_bytes=1000, minio_key=f"k{i}", synced_at=_NOW,
        ))
    db.commit()

    status = get_sync_status(db, tid)

    assert status["total_documents"] == 3
    assert status["customers_with_docs"] == 1
    assert status["total_customers"] == 2
    assert status["total_size_bytes"] == 3000
    assert status["total_size_mb"] == 0.0  # 3000 bytes ~ 0.0 MB
    assert status["last_sync_at"] is not None
