"""Tests pour la task d'expiration automatique des devis."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.models import Case, Customer, Devis
from app.tasks.devis_tasks import expire_devis


class _NoCloseSession:
    """Wrapper qui ignore close() pour permettre au test de relire la session
    apres l'execution de la task (qui ferme habituellement sa propre session)."""

    def __init__(self, real: Session) -> None:
        self._real = real

    def __getattr__(self, name: str):  # type: ignore[no-untyped-def]
        return getattr(self._real, name)

    def close(self) -> None:
        pass


def _patch_session_local(monkeypatch, db: Session) -> None:
    from app.tasks import devis_tasks as dt
    monkeypatch.setattr(dt, "SessionLocal", lambda: _NoCloseSession(db))


def _seed_devis(db: Session, tenant_id: int, status: str, valid_until: datetime | None) -> int:
    """Cree un devis et retourne son id (l'instance peut etre detachee apres commit)."""
    customer = Customer(tenant_id=tenant_id, first_name="A", last_name=f"Client-{status}")
    db.add(customer)
    db.flush()
    case = Case(tenant_id=tenant_id, customer_id=customer.id, status="en_cours", source="manual")
    db.add(case)
    db.flush()
    devis = Devis(
        tenant_id=tenant_id,
        case_id=case.id,
        numero=f"DEV-{customer.id:05d}",
        status=status,
        valid_until=valid_until,
    )
    db.add(devis)
    db.flush()
    return devis.id


@pytest.mark.parametrize("status", ["brouillon", "envoye"])
def test_expire_devis_marks_overdue_devis_as_expire(db, default_tenant, monkeypatch, status):
    """Devis avec valid_until < now ET status in (brouillon, envoye) -> expire."""
    past = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=1)
    devis_id = _seed_devis(db, default_tenant.id, status, past)
    db.commit()

    _patch_session_local(monkeypatch, db)
    result = expire_devis()

    assert result["expired"] >= 1
    assert db.query(Devis).filter(Devis.id == devis_id).one().status == "expire"


def test_expire_devis_ignores_signed_and_facture_status(db, default_tenant, monkeypatch):
    past = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=1)
    signe_id = _seed_devis(db, default_tenant.id, "signe", past)
    facture_id = _seed_devis(db, default_tenant.id, "facture", past)
    db.commit()

    _patch_session_local(monkeypatch, db)
    expire_devis()

    assert db.query(Devis).filter(Devis.id == signe_id).one().status == "signe"
    assert db.query(Devis).filter(Devis.id == facture_id).one().status == "facture"


def test_expire_devis_ignores_future_devis(db, default_tenant, monkeypatch):
    future = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=30)
    devis_id = _seed_devis(db, default_tenant.id, "envoye", future)
    db.commit()

    _patch_session_local(monkeypatch, db)
    result = expire_devis()

    assert result["expired"] == 0
    assert db.query(Devis).filter(Devis.id == devis_id).one().status == "envoye"


def test_expire_devis_ignores_null_valid_until(db, default_tenant, monkeypatch):
    """Anciens devis sans valid_until (NULL) ne doivent jamais expirer."""
    devis_id = _seed_devis(db, default_tenant.id, "envoye", None)
    db.commit()

    _patch_session_local(monkeypatch, db)
    result = expire_devis()

    assert result["expired"] == 0
    assert db.query(Devis).filter(Devis.id == devis_id).one().status == "envoye"


def test_create_devis_sets_valid_until_default_90_days(db, default_tenant):
    """Un nouveau devis cree via le repo doit avoir valid_until ~= now+90j."""
    from app.repositories import devis_repo
    customer = Customer(tenant_id=default_tenant.id, first_name="Test", last_name="ValidUntil")
    db.add(customer)
    db.flush()
    case = Case(tenant_id=default_tenant.id, customer_id=customer.id, status="en_cours", source="manual")
    db.add(case)
    db.flush()

    devis = devis_repo.create(db, default_tenant.id, case.id, "DEV-VU-001")
    db.commit()

    assert devis.valid_until is not None
    delta = devis.valid_until - datetime.now(UTC).replace(tzinfo=None)
    assert timedelta(days=89, hours=23) < delta < timedelta(days=90, hours=1)
