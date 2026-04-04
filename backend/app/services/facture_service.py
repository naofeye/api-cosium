from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError, NotFoundError
from app.core.logging import get_logger
from app.domain.schemas.factures import (
    FactureDetail,
    FactureLigneResponse,
    FactureResponse,
)
from app.repositories import devis_repo, facture_repo
from app.services import audit_service, event_service

logger = get_logger("facture_service")


def create_from_devis(db: Session, tenant_id: int, devis_id: int, user_id: int) -> FactureResponse:
    devis = devis_repo.get_by_id(db, devis_id=devis_id, tenant_id=tenant_id)
    if not devis:
        raise NotFoundError("devis", devis_id)

    if devis.status not in ("signe", "facture"):
        raise BusinessError(
            "DEVIS_NOT_SIGNED",
            "Le devis doit etre signe avant de pouvoir generer une facture",
        )

    existing = facture_repo.get_by_devis_id(db, devis_id=devis_id, tenant_id=tenant_id)
    if existing:
        raise BusinessError(
            "FACTURE_ALREADY_EXISTS",
            f"Une facture existe deja pour ce devis ({existing.numero})",
        )

    numero = facture_repo.generate_numero(db, tenant_id)
    facture = facture_repo.create(
        db,
        tenant_id=tenant_id,
        case_id=devis.case_id,
        devis_id=devis.id,
        numero=numero,
        montant_ht=float(devis.montant_ht),
        tva=float(devis.tva),
        montant_ttc=float(devis.montant_ttc),
    )

    lignes = devis_repo.get_lignes(db, devis_id=devis_id, tenant_id=tenant_id)
    for l in lignes:
        facture_repo.add_ligne(
            db,
            tenant_id,
            facture.id,
            designation=l.designation,
            quantite=l.quantite,
            prix_unitaire_ht=float(l.prix_unitaire_ht),
            taux_tva=float(l.taux_tva),
            montant_ht=float(l.montant_ht),
            montant_ttc=float(l.montant_ttc),
        )

    if devis.status == "signe":
        devis_repo.update_status(db, devis, "facture")

    db.commit()
    db.refresh(facture)

    if user_id:
        audit_service.log_action(
            db,
            user_id,
            "create",
            "facture",
            facture.id,
            new_value={"numero": numero, "devis_id": devis_id},
            tenant_id=tenant_id,
        )
        event_service.emit_event(db, tenant_id, "FactureEmise", "facture", facture.id, user_id)

    logger.info("facture_created", tenant_id=tenant_id, facture_id=facture.id, numero=numero, devis_id=devis_id)
    return FactureResponse.model_validate(facture)


def list_factures(db: Session, tenant_id: int, limit: int = 25, offset: int = 0) -> list[FactureResponse]:
    rows = facture_repo.list_all(db, tenant_id, limit=limit, offset=offset)
    return [FactureResponse(**r) for r in rows]


def get_facture_detail(db: Session, tenant_id: int, facture_id: int) -> FactureDetail:
    data = facture_repo.get_detail(db, facture_id=facture_id, tenant_id=tenant_id)
    if not data:
        raise NotFoundError("facture", facture_id)
    lignes = facture_repo.get_lignes(db, facture_id=facture_id, tenant_id=tenant_id)
    return FactureDetail(
        **data,
        lignes=[FactureLigneResponse.model_validate(l) for l in lignes],
    )
