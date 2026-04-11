"""Tests for consolidation_service (multi-source PEC consolidation)."""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Tenant
from app.models.case import Case
from app.models.client import Customer
from app.models.client_mutuelle import ClientMutuelle
from app.models.cosium_data import CosiumPrescription
from app.models.devis import Devis, DevisLigne
from app.services.consolidation_service import (
    PEC_REQUIRED_FIELDS,
    consolidate_client_for_pec,
)


def _make_customer(db: Session, tenant_id: int, **kwargs) -> Customer:
    defaults = dict(
        tenant_id=tenant_id, cosium_id="1001",
        first_name="Jean", last_name="Dupont",
    )
    defaults.update(kwargs)
    c = Customer(**defaults)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


# ---------- 1. Cosium client data populates identity fields ----------

def test_consolidation_with_cosium_client_data(db: Session, default_tenant: Tenant) -> None:
    tid = default_tenant.id
    cust = _make_customer(db, tid, social_security_number="1850175012345")

    profile = consolidate_client_for_pec(db, tid, cust.id)

    assert profile.nom is not None
    assert profile.nom.value == "Dupont"
    assert profile.nom.source == "cosium_client"
    assert profile.prenom is not None
    assert profile.prenom.value == "Jean"
    assert profile.numero_secu is not None
    assert profile.numero_secu.value == "1850175012345"
    assert "cosium_client" in profile.sources_utilisees


# ---------- 2. Prescription populates optical fields ----------

def test_consolidation_with_prescription(db: Session, default_tenant: Tenant) -> None:
    tid = default_tenant.id
    cust = _make_customer(db, tid)

    rx = CosiumPrescription(
        tenant_id=tid, cosium_id=500, customer_id=cust.id,
        prescription_date="2026-03-15",
        sphere_right=-2.50, cylinder_right=-0.75, axis_right=90,
        addition_right=1.50,
        sphere_left=-3.00, cylinder_left=-1.00, axis_left=85,
        addition_left=1.50,
        prescriber_name="Dr Martin",
    )
    db.add(rx)
    db.commit()

    profile = consolidate_client_for_pec(db, tid, cust.id)

    assert profile.sphere_od is not None
    assert profile.sphere_od.value == -2.50
    assert profile.sphere_og is not None
    assert profile.sphere_og.value == -3.00
    assert profile.prescripteur is not None
    assert profile.prescripteur.value == "Dr Martin"
    assert profile.date_ordonnance is not None
    assert profile.date_ordonnance.value == "2026-03-15"
    # Source should contain cosium_prescription
    assert any("cosium_prescription" in s for s in profile.sources_utilisees)


# ---------- 3. Devis populates financial fields ----------

def test_consolidation_with_devis(db: Session, default_tenant: Tenant) -> None:
    tid = default_tenant.id
    cust = _make_customer(db, tid)

    case = Case(tenant_id=tid, customer_id=cust.id, status="en_cours")
    db.add(case)
    db.flush()

    devis = Devis(
        tenant_id=tid, case_id=case.id, numero="DEV-2026-001",
        montant_ht=Decimal("400.00"), tva=Decimal("0.00"),
        montant_ttc=Decimal("480.00"),
        part_secu=Decimal("60.00"), part_mutuelle=Decimal("300.00"),
        reste_a_charge=Decimal("120.00"),
    )
    db.add(devis)
    db.flush()

    ligne_monture = DevisLigne(
        tenant_id=tid, devis_id=devis.id,
        designation="Monture Ray-Ban", quantite=1,
        prix_unitaire_ht=Decimal("150.00"), montant_ht=Decimal("150.00"),
        montant_ttc=Decimal("180.00"),
    )
    ligne_verre = DevisLigne(
        tenant_id=tid, devis_id=devis.id,
        designation="Verre progressif OD", quantite=1,
        prix_unitaire_ht=Decimal("125.00"), montant_ht=Decimal("125.00"),
        montant_ttc=Decimal("150.00"),
    )
    db.add_all([ligne_monture, ligne_verre])
    db.commit()

    profile = consolidate_client_for_pec(db, tid, cust.id)

    assert profile.montant_ttc is not None
    assert profile.montant_ttc.value == 480.0
    assert profile.part_secu is not None
    assert profile.part_secu.value == 60.0
    assert profile.part_mutuelle is not None
    assert profile.part_mutuelle.value == 300.0
    assert profile.reste_a_charge is not None
    assert profile.reste_a_charge.value == 120.0
    # Equipment
    assert profile.monture is not None
    assert "Monture" in profile.monture.value
    assert len(profile.verres) >= 1
    assert any("devis" in s for s in profile.sources_utilisees)


# ---------- 4. Empty consolidation has 0% score ----------

def test_empty_consolidation_low_score(db: Session, default_tenant: Tenant) -> None:
    """A customer with no real data should have a very low completude score."""
    tid = default_tenant.id
    # Create customer with minimal empty data
    cust = Customer(
        tenant_id=tid, first_name="", last_name="", cosium_id=None,
    )
    db.add(cust)
    db.commit()
    db.refresh(cust)

    profile = consolidate_client_for_pec(db, tid, cust.id)

    # Customer not found by id lookup (cosium_id=None), so no Cosium fields populated
    # Score should be 0 if customer not found, or very low if empty strings count
    assert profile.score_completude <= 20.0
    assert len(profile.champs_manquants) >= 10


# ---------- 5. Sources correctly tracked ----------

def test_sources_are_correctly_tracked(db: Session, default_tenant: Tenant) -> None:
    tid = default_tenant.id
    cust = _make_customer(db, tid, social_security_number="2900175012345")

    # Add prescription
    db.add(CosiumPrescription(
        tenant_id=tid, cosium_id=600, customer_id=cust.id,
        sphere_right=-1.00, prescriber_name="Dr Leroy",
    ))
    # Add mutuelle
    db.add(ClientMutuelle(
        tenant_id=tid, customer_id=cust.id,
        mutuelle_name="Harmonie Mutuelle",
        numero_adherent="HM-12345",
        source="cosium_tpp", confidence=0.9, active=True,
    ))
    db.commit()

    profile = consolidate_client_for_pec(db, tid, cust.id)

    assert "cosium_client" in profile.sources_utilisees
    assert any("cosium_prescription" in s for s in profile.sources_utilisees)
    assert any("mutuelle" in s for s in profile.sources_utilisees)
    # At least 3 distinct source groups
    assert len(profile.sources_utilisees) >= 3
    # Score should be > 0 since we have some fields filled
    assert profile.score_completude > 0
