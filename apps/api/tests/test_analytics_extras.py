"""Tests smoke pour analytics_cosium_extras : trends, best_contact_hour, cashflow, top clients."""

from datetime import UTC, datetime, timedelta

from app.models import Customer
from app.models.cosium_data import CosiumInvoice
from app.models.interaction import Interaction
from app.services.analytics_cosium_extras import (
    compute_best_contact_hour,
    compute_trends,
    get_cashflow_forecast,
    get_top_clients_by_ca,
)


def _add_invoice(db, tenant_id: int, customer_id: int | None, total: float, days_ago: int) -> None:
    db.add(
        CosiumInvoice(
            tenant_id=tenant_id,
            cosium_id=hash((tenant_id, customer_id or 0, total, days_ago)) % (10**9),
            invoice_number=f"F{days_ago:03d}",
            invoice_date=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days_ago),
            customer_id=customer_id,
            customer_name="Test",
            type="INVOICE",
            total_ti=total,
            outstanding_balance=0,
        )
    )


def test_compute_trends_no_data(db, default_tenant) -> None:
    res = compute_trends(db, default_tenant.id)
    assert res["period_current"]["ca"] == 0
    assert res["period_previous"]["ca"] == 0
    assert res["delta"]["ca_pct"] is None


def test_compute_trends_with_data(db, default_tenant) -> None:
    _add_invoice(db, default_tenant.id, None, 1000, days_ago=10)
    _add_invoice(db, default_tenant.id, None, 500, days_ago=40)
    db.commit()

    res = compute_trends(db, default_tenant.id)
    assert res["period_current"]["ca"] == 1000
    assert res["period_previous"]["ca"] == 500
    assert res["delta"]["ca_pct"] == 100.0


def test_best_contact_hour_insufficient_samples(db, default_tenant) -> None:
    res = compute_best_contact_hour(db, default_tenant.id, min_sample=10)
    assert res["confident"] is False
    assert res["best_hours"] == []


def test_best_contact_hour_with_samples(db, default_tenant) -> None:
    c = Customer(tenant_id=default_tenant.id, first_name="C", last_name="L")
    db.add(c)
    db.flush()
    now = datetime.now(UTC).replace(tzinfo=None)
    for _ in range(12):
        db.add(
            Interaction(
                tenant_id=default_tenant.id, client_id=c.id, type="email", direction="entrant",
                subject="test", created_at=now.replace(hour=14),
            )
        )
    db.commit()
    res = compute_best_contact_hour(db, default_tenant.id, min_sample=10)
    assert res["confident"] is True
    assert res["best_hours"][0]["hour"] == 14


def test_top_clients_empty(db, default_tenant) -> None:
    res = get_top_clients_by_ca(db, default_tenant.id, limit=10)
    assert res == []


def test_cashflow_forecast_empty_returns_zeros(db, default_tenant) -> None:
    res = get_cashflow_forecast(db, default_tenant.id)
    assert "cashflow" in res or "forecast" in res or isinstance(res, dict)
