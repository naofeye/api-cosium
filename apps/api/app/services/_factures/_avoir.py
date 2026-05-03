"""Logique avoir (note de credit) extraite de facture_service.

Norme comptable : on ne modifie/supprime pas une facture emise. L'avoir
est une nouvelle facture aux montants negatifs liee a l'originale.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError, NotFoundError
from app.core.logging import get_logger
from app.domain.schemas.factures import FactureResponse
from app.repositories import facture_repo
from app.services import audit_service, event_service, webhook_emit_helpers

logger = get_logger("facture_service.avoir")

# Quantum 2 decimales pour les montants en euros (BDD = Numeric(10,2)).
_EURO_QUANT = Decimal("0.01")


def _q2(value: Decimal) -> Decimal:
    return value.quantize(_EURO_QUANT, rounding=ROUND_HALF_UP)


def create_avoir(
    db: Session,
    tenant_id: int,
    facture_id: int,
    motif: str,
    montant_ttc_partiel: float | None,
    user_id: int,
) -> FactureResponse:
    """Cree un avoir (note de credit) sur une facture existante.

    - `montant_ttc_partiel=None` -> avoir total (annule toute la facture).
    - `montant_ttc_partiel=X` (positif, X <= facture.montant_ttc) -> avoir partiel.

    Lignes de l'avoir : copie inversee des lignes originales (avoir total) ou
    ligne unique forfaitaire (avoir partiel).
    """
    original = facture_repo.get_by_id(db, facture_id=facture_id, tenant_id=tenant_id)
    if not original:
        raise NotFoundError("facture", facture_id)

    if original.original_facture_id is not None:
        raise BusinessError(
            "AVOIR_ON_AVOIR_FORBIDDEN",
            "Impossible d'emettre un avoir sur un avoir. Avoir cible la facture originale.",
        )

    original_ttc_d = Decimal(str(original.montant_ttc))
    original_ht_d = Decimal(str(original.montant_ht))
    original_tva_d = Decimal(str(original.tva))

    if original_ttc_d <= 0:
        raise BusinessError(
            "FACTURE_NEGATIVE",
            "La facture originale a un montant negatif ou nul ; impossible d'emettre un avoir.",
        )

    if montant_ttc_partiel is not None:
        partiel_d = Decimal(str(montant_ttc_partiel))
        if partiel_d <= 0:
            raise BusinessError(
                "AVOIR_AMOUNT_INVALID",
                "Le montant de l'avoir partiel doit etre strictement positif.",
            )
        if partiel_d > original_ttc_d:
            raise BusinessError(
                "AVOIR_AMOUNT_EXCEEDS_FACTURE",
                f"Le montant de l'avoir ({partiel_d}EUR) ne peut pas exceder "
                f"la facture originale ({original_ttc_d}EUR).",
            )

        ratio = partiel_d / original_ttc_d
        ht = -_q2(original_ht_d * ratio)
        tva = -_q2(original_tva_d * ratio)
        ttc = -_q2(partiel_d)
        partial = True
    else:
        ht = -_q2(original_ht_d)
        tva = -_q2(original_tva_d)
        ttc = -_q2(original_ttc_d)
        partial = False

    numero = facture_repo.generate_avoir_numero(db, tenant_id)
    avoir = facture_repo.create_avoir(
        db,
        tenant_id=tenant_id,
        original=original,
        numero=numero,
        montant_ht=ht,
        tva=tva,
        montant_ttc=ttc,
        motif=motif,
    )

    if partial:
        if original_ht_d > 0:
            taux_tva_avoir = float(_q2(original_tva_d / original_ht_d * Decimal("100")))
        else:
            taux_tva_avoir = 20.0
        facture_repo.add_ligne(
            db,
            tenant_id,
            avoir.id,
            designation=f"Avoir partiel sur facture {original.numero} : {motif[:200]}",
            quantite=1,
            prix_unitaire_ht=ht,
            taux_tva=taux_tva_avoir,
            montant_ht=ht,
            montant_ttc=ttc,
        )
    else:
        original_lignes = facture_repo.get_lignes(db, facture_id=original.id, tenant_id=tenant_id)
        for line in original_lignes:
            facture_repo.add_ligne(
                db,
                tenant_id,
                avoir.id,
                designation=f"AVOIR : {line.designation}",
                quantite=line.quantite,
                prix_unitaire_ht=-float(line.prix_unitaire_ht),
                taux_tva=float(line.taux_tva),
                montant_ht=-float(line.montant_ht),
                montant_ttc=-float(line.montant_ttc),
            )

    db.commit()
    db.refresh(avoir)

    if user_id:
        audit_service.log_action(
            db,
            tenant_id,
            user_id,
            "create",
            "avoir",
            avoir.id,
            new_value={
                "numero": numero,
                "original_facture_id": original.id,
                "original_numero": original.numero,
                "montant_ttc": float(ttc),
                "motif": motif,
                "partial": partial,
            },
        )
        event_service.emit_event(db, tenant_id, "AvoirEmis", "facture", avoir.id, user_id)
        avoir_response = FactureResponse.model_validate(avoir)
        webhook_emit_helpers.emit_facture_avoir_created(db, tenant_id, avoir_response, facture_id)
        db.commit()

    logger.info(
        "avoir_created",
        tenant_id=tenant_id,
        avoir_id=avoir.id,
        numero=numero,
        original_facture_id=original.id,
        montant_ttc=ttc,
        partial=partial,
    )
    return FactureResponse.model_validate(avoir)
