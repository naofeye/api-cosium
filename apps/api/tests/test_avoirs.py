"""Tests pour les avoirs (notes de credit) sur factures."""

import pytest

from app.core.exceptions import BusinessError, NotFoundError
from app.models import Case, Customer, Devis, Facture, FactureLigne
from app.services import facture_service


def _seed_facture(db, tenant_id: int, montant_ttc: float = 100.0) -> Facture:
    customer = Customer(tenant_id=tenant_id, first_name="A", last_name="Test")
    db.add(customer)
    db.flush()
    case = Case(tenant_id=tenant_id, customer_id=customer.id, status="en_cours", source="manual")
    db.add(case)
    db.flush()
    devis = Devis(
        tenant_id=tenant_id, case_id=case.id, numero="DEV-AV-001",
        status="signe", montant_ht=montant_ttc * 0.8, tva=montant_ttc * 0.2,
        montant_ttc=montant_ttc,
    )
    db.add(devis)
    db.flush()
    facture = Facture(
        tenant_id=tenant_id, case_id=case.id, devis_id=devis.id,
        numero="F-2026-0001",
        montant_ht=montant_ttc * 0.8, tva=montant_ttc * 0.2, montant_ttc=montant_ttc,
        status="emise",
    )
    db.add(facture)
    db.flush()
    db.add(FactureLigne(
        tenant_id=tenant_id, facture_id=facture.id,
        designation="Lunettes optiques", quantite=1,
        prix_unitaire_ht=montant_ttc * 0.8, taux_tva=20.0,
        montant_ht=montant_ttc * 0.8, montant_ttc=montant_ttc,
    ))
    db.commit()
    return facture


def test_create_avoir_total_inverts_amounts(db, default_tenant, seed_user):
    facture = _seed_facture(db, default_tenant.id, 250.0)
    avoir = facture_service.create_avoir(
        db, default_tenant.id, facture.id, "Retour produit", None, seed_user.id,
    )

    assert avoir.numero.startswith("AV-")
    assert avoir.montant_ttc == -250.0
    assert avoir.montant_ht == -200.0
    assert avoir.tva == -50.0
    assert avoir.original_facture_id == facture.id
    assert avoir.motif_avoir == "Retour produit"


def test_create_avoir_partiel_proportional(db, default_tenant, seed_user):
    facture = _seed_facture(db, default_tenant.id, 250.0)
    avoir = facture_service.create_avoir(
        db, default_tenant.id, facture.id, "Geste commercial 50EUR", 50.0, seed_user.id,
    )

    assert avoir.montant_ttc == -50.0
    # Partiel : proportionnel sur HT/TVA
    assert avoir.montant_ht == pytest.approx(-40.0, abs=0.01)
    assert avoir.tva == pytest.approx(-10.0, abs=0.01)


def test_create_avoir_facture_not_found_raises(db, default_tenant, seed_user):
    with pytest.raises(NotFoundError):
        facture_service.create_avoir(db, default_tenant.id, 99999, "x", None, seed_user.id)


def test_create_avoir_on_avoir_forbidden(db, default_tenant, seed_user):
    facture = _seed_facture(db, default_tenant.id, 100.0)
    avoir = facture_service.create_avoir(
        db, default_tenant.id, facture.id, "Premier avoir", None, seed_user.id,
    )
    with pytest.raises(BusinessError) as exc_info:
        facture_service.create_avoir(
            db, default_tenant.id, avoir.id, "Avoir sur avoir", None, seed_user.id,
        )
    assert "AVOIR_ON_AVOIR_FORBIDDEN" in str(exc_info.value)


def test_create_avoir_partiel_exceeds_facture_raises(db, default_tenant, seed_user):
    facture = _seed_facture(db, default_tenant.id, 100.0)
    with pytest.raises(BusinessError) as exc_info:
        facture_service.create_avoir(
            db, default_tenant.id, facture.id, "Trop", 200.0, seed_user.id,
        )
    assert "AVOIR_AMOUNT_EXCEEDS_FACTURE" in str(exc_info.value)


def test_create_avoir_zero_amount_rejected(db, default_tenant, seed_user):
    facture = _seed_facture(db, default_tenant.id, 100.0)
    with pytest.raises(BusinessError) as exc_info:
        facture_service.create_avoir(
            db, default_tenant.id, facture.id, "Zero", 0.0, seed_user.id,
        )
    # 0 est invalide (Pydantic ne l'aurait pas accepte de toute facon avec ge=0,
    # mais le service garde un guard pour les appels directs hors API)
    assert "AVOIR_AMOUNT_INVALID" in str(exc_info.value)


def test_avoir_lignes_are_inverted(db, default_tenant, seed_user):
    """L'avoir total doit recopier les lignes originales avec montants negatifs."""
    facture = _seed_facture(db, default_tenant.id, 200.0)
    avoir = facture_service.create_avoir(
        db, default_tenant.id, facture.id, "Annulation totale", None, seed_user.id,
    )

    lignes = db.query(FactureLigne).filter(FactureLigne.facture_id == avoir.id).all()
    assert len(lignes) == 1
    assert lignes[0].montant_ttc == -200.0
    assert lignes[0].designation.startswith("AVOIR :")


def test_facture_numero_excludes_avoirs(db, default_tenant, seed_user):
    """generate_numero ne doit pas compter les avoirs comme des factures."""
    from app.repositories import facture_repo

    facture1 = _seed_facture(db, default_tenant.id, 100.0)
    avoir = facture_service.create_avoir(
        db, default_tenant.id, facture1.id, "Avoir", None, seed_user.id,
    )
    # Le prochain numero de facture doit etre F-yyyy-0002 (pas 0003 a cause de l'avoir)
    next_facture_numero = facture_repo.generate_numero(db, default_tenant.id)
    assert next_facture_numero.endswith("0002")
    next_avoir_numero = facture_repo.generate_avoir_numero(db, default_tenant.id)
    assert next_avoir_numero.endswith("0002")
    # Numero avoir distinct
    assert avoir.numero.startswith("AV-")
