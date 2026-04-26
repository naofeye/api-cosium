"""Tests for cosium_invoice_repo.get_totals — aggregate query with order_by."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.cosium_data import CosiumInvoice
from app.repositories import cosium_invoice_repo


def _make_invoice(
    tenant_id: int,
    cosium_id: int,
    total_ti: float = 100.0,
    outstanding: float = 0.0,
    type_: str = "INVOICE",
    settled: bool = True,
) -> CosiumInvoice:
    return CosiumInvoice(
        tenant_id=tenant_id,
        cosium_id=cosium_id,
        invoice_number=f"F{cosium_id}",
        invoice_date=datetime.now(UTC),
        customer_name="Dupont Jean",
        type=type_,
        total_ti=total_ti,
        outstanding_balance=outstanding,
        settled=settled,
    )


def test_get_totals_empty_returns_zero(db: Session, default_tenant) -> None:
    """No invoices for tenant — totals should be zero."""
    result = cosium_invoice_repo.get_totals(db, tenant_id=default_tenant.id)
    assert result == {"total_ttc": 0.0, "total_impaye": 0.0, "count": 0}


def test_get_totals_aggregates_across_rows(db: Session, default_tenant) -> None:
    """Sums total_ti and outstanding_balance, counts rows."""
    db.add(_make_invoice(default_tenant.id, 1, total_ti=100.0, outstanding=20.0))
    db.add(_make_invoice(default_tenant.id, 2, total_ti=250.0, outstanding=0.0))
    db.add(_make_invoice(default_tenant.id, 3, total_ti=50.5, outstanding=50.5))
    db.commit()

    result = cosium_invoice_repo.get_totals(db, tenant_id=default_tenant.id)
    assert result["count"] == 3
    assert result["total_ttc"] == 400.5
    assert result["total_impaye"] == 70.5


def test_get_totals_filters_by_tenant(db: Session, default_tenant) -> None:
    """Only rows for the requested tenant are aggregated."""
    db.add(_make_invoice(default_tenant.id, 1, total_ti=100.0))
    db.add(_make_invoice(tenant_id=999, cosium_id=2, total_ti=999.0))
    db.commit()

    result = cosium_invoice_repo.get_totals(db, tenant_id=default_tenant.id)
    assert result["count"] == 1
    assert result["total_ttc"] == 100.0


def test_get_totals_applies_settled_filter(db: Session, default_tenant) -> None:
    """settled=False excludes settled invoices."""
    db.add(_make_invoice(default_tenant.id, 1, total_ti=100.0, settled=True))
    db.add(_make_invoice(default_tenant.id, 2, total_ti=200.0, settled=False))
    db.commit()

    result = cosium_invoice_repo.get_totals(db, tenant_id=default_tenant.id, settled=False)
    assert result["count"] == 1
    assert result["total_ttc"] == 200.0
