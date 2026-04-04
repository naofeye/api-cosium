from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError, NotFoundError
from app.core.logging import get_logger
from app.domain.schemas.pec import (
    PayerOrgCreate,
    PayerOrgResponse,
    PecCreate,
    PecDetail,
    PecResponse,
    PecStatusHistoryResponse,
    PecStatusUpdate,
    RelanceCreate,
    RelanceResponse,
)
from app.repositories import pec_repo
from app.services import audit_service, event_service

logger = get_logger("pec_service")

VALID_TRANSITIONS: dict[str, list[str]] = {
    "soumise": ["en_attente", "acceptee", "refusee", "partielle"],
    "en_attente": ["acceptee", "refusee", "partielle"],
    "acceptee": ["cloturee"],
    "refusee": ["cloturee"],
    "partielle": ["cloturee"],
    "cloturee": [],
}

EVENT_MAP: dict[str, str] = {
    "soumise": "PECSoumise",
    "acceptee": "PECAcceptee",
    "refusee": "PECRefusee",
}


# --- Organizations ---


def list_organizations(db: Session, tenant_id: int) -> list[PayerOrgResponse]:
    orgs = pec_repo.list_organizations(db, tenant_id)
    return [PayerOrgResponse.model_validate(o) for o in orgs]


def create_organization(db: Session, tenant_id: int, payload: PayerOrgCreate, user_id: int) -> PayerOrgResponse:
    org = pec_repo.create_organization(db, tenant_id, payload.name, payload.type, payload.code, payload.contact_email)
    if user_id:
        audit_service.log_action(db, tenant_id, user_id, "create", "payer_organization", org.id)
    logger.info("organization_created", tenant_id=tenant_id, org_id=org.id, name=payload.name)
    return PayerOrgResponse.model_validate(org)


# --- PEC Requests ---


def create_pec(db: Session, tenant_id: int, payload: PecCreate, user_id: int) -> PecResponse:
    org = pec_repo.get_organization(db, org_id=payload.organization_id, tenant_id=tenant_id)
    if not org:
        raise NotFoundError("organization", payload.organization_id)

    pec = pec_repo.create_pec(
        db,
        tenant_id=tenant_id,
        case_id=payload.case_id,
        organization_id=payload.organization_id,
        facture_id=payload.facture_id,
        montant_demande=payload.montant_demande,
    )
    pec_repo.add_history(db, tenant_id, pec.id, "", "soumise", "Demande de PEC soumise")

    if user_id:
        audit_service.log_action(
            db,
            tenant_id,
            user_id,
            "create",
            "pec_request",
            pec.id,
            new_value={"montant": payload.montant_demande, "org": org.name},
        )
        event_service.emit_event(db, tenant_id, "PECSoumise", "pec_request", pec.id, user_id)

    logger.info("pec_created", tenant_id=tenant_id, pec_id=pec.id, org=org.name)
    return PecResponse(
        **{
            "id": pec.id,
            "case_id": pec.case_id,
            "organization_id": pec.organization_id,
            "facture_id": pec.facture_id,
            "montant_demande": float(pec.montant_demande),
            "montant_accorde": None,
            "status": pec.status,
            "created_at": pec.created_at,
            "organization_name": org.name,
        }
    )


def list_pec(
    db: Session,
    tenant_id: int,
    status: str | None = None,
    organization_id: int | None = None,
    limit: int = 25,
    offset: int = 0,
) -> list[PecResponse]:
    rows = pec_repo.list_pec(db, tenant_id, status, organization_id, limit=limit, offset=offset)
    return [PecResponse(**r) for r in rows]


def get_pec_detail(db: Session, tenant_id: int, pec_id: int) -> PecDetail:
    pec = pec_repo.get_pec(db, pec_id=pec_id, tenant_id=tenant_id)
    if not pec:
        raise NotFoundError("pec_request", pec_id)

    org = pec_repo.get_organization(db, org_id=pec.organization_id, tenant_id=tenant_id)
    history = pec_repo.get_history(db, pec_id=pec_id, tenant_id=tenant_id)

    return PecDetail(
        id=pec.id,
        case_id=pec.case_id,
        organization_id=pec.organization_id,
        facture_id=pec.facture_id,
        montant_demande=float(pec.montant_demande),
        montant_accorde=float(pec.montant_accorde) if pec.montant_accorde is not None else None,
        status=pec.status,
        created_at=pec.created_at,
        organization_name=org.name if org else None,
        history=[PecStatusHistoryResponse.model_validate(h) for h in history],
    )


def change_status(db: Session, tenant_id: int, pec_id: int, payload: PecStatusUpdate, user_id: int) -> PecResponse:
    pec = pec_repo.get_pec(db, pec_id=pec_id, tenant_id=tenant_id)
    if not pec:
        raise NotFoundError("pec_request", pec_id)

    allowed = VALID_TRANSITIONS.get(pec.status, [])
    if payload.status not in allowed:
        raise BusinessError(
            "INVALID_PEC_TRANSITION",
            f"Transition '{pec.status}' -> '{payload.status}' non autorisee. "
            f"Transitions possibles : {', '.join(allowed) or 'aucune'}",
        )

    old_status = pec.status
    pec_repo.update_status(db, pec, payload.status, payload.montant_accorde)
    pec_repo.add_history(
        db,
        tenant_id=tenant_id,
        pec_id=pec_id,
        old_status=old_status,
        new_status=payload.status,
        comment=payload.comment,
    )

    if user_id:
        audit_service.log_action(
            db,
            tenant_id,
            user_id,
            "update",
            "pec_request",
            pec_id,
            old_value={"status": old_status},
            new_value={"status": payload.status},
        )
        event_name = EVENT_MAP.get(payload.status)
        if event_name:
            event_service.emit_event(db, tenant_id, event_name, "pec_request", pec_id, user_id)

    logger.info("pec_status_changed", tenant_id=tenant_id, pec_id=pec_id, old=old_status, new=payload.status)
    org = pec_repo.get_organization(db, org_id=pec.organization_id, tenant_id=tenant_id)
    return PecResponse(
        id=pec.id,
        case_id=pec.case_id,
        organization_id=pec.organization_id,
        facture_id=pec.facture_id,
        montant_demande=float(pec.montant_demande),
        montant_accorde=float(pec.montant_accorde) if pec.montant_accorde is not None else None,
        status=pec.status,
        created_at=pec.created_at,
        organization_name=org.name if org else None,
    )


def get_history(db: Session, tenant_id: int, pec_id: int) -> list[PecStatusHistoryResponse]:
    pec = pec_repo.get_pec(db, pec_id=pec_id, tenant_id=tenant_id)
    if not pec:
        raise NotFoundError("pec_request", pec_id)
    history = pec_repo.get_history(db, pec_id=pec_id, tenant_id=tenant_id)
    return [PecStatusHistoryResponse.model_validate(h) for h in history]


# --- Relances ---


def create_relance(db: Session, tenant_id: int, pec_id: int, payload: RelanceCreate, user_id: int) -> RelanceResponse:
    pec = pec_repo.get_pec(db, pec_id=pec_id, tenant_id=tenant_id)
    if not pec:
        raise NotFoundError("pec_request", pec_id)

    relance = pec_repo.create_relance(
        db, tenant_id=tenant_id, pec_id=pec_id, type=payload.type, contenu=payload.contenu, user_id=user_id
    )
    audit_service.log_action(
        db,
        tenant_id,
        user_id,
        "create",
        "relance",
        relance.id,
        new_value={"pec_id": pec_id, "type": payload.type},
    )
    logger.info("relance_created", tenant_id=tenant_id, pec_id=pec_id, relance_id=relance.id, type=payload.type)
    return RelanceResponse.model_validate(relance)


def get_relances(db: Session, tenant_id: int, pec_id: int) -> list[RelanceResponse]:
    pec = pec_repo.get_pec(db, pec_id=pec_id, tenant_id=tenant_id)
    if not pec:
        raise NotFoundError("pec_request", pec_id)
    relances = pec_repo.get_relances(db, pec_id=pec_id, tenant_id=tenant_id)
    return [RelanceResponse.model_validate(r) for r in relances]
