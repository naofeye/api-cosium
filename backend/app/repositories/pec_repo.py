from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Case,
    Customer,
    PayerOrganization,
    PecRequest,
    PecStatusHistory,
    Relance,
)

# --- Payer Organizations ---


def list_organizations(db: Session, tenant_id: int) -> list[PayerOrganization]:
    return list(
        db.scalars(
            select(PayerOrganization).where(PayerOrganization.tenant_id == tenant_id).order_by(PayerOrganization.name)
        ).all()
    )


def get_organization(db: Session, org_id: int, tenant_id: int) -> PayerOrganization | None:
    return db.scalars(
        select(PayerOrganization).where(PayerOrganization.id == org_id, PayerOrganization.tenant_id == tenant_id)
    ).first()


def create_organization(
    db: Session, tenant_id: int, name: str, type: str, code: str, contact_email: str | None
) -> PayerOrganization:
    org = PayerOrganization(tenant_id=tenant_id, name=name, type=type, code=code, contact_email=contact_email)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


# --- PEC Requests ---


def create_pec(
    db: Session, tenant_id: int, case_id: int, organization_id: int, facture_id: int | None, montant_demande: float
) -> PecRequest:
    pec = PecRequest(
        tenant_id=tenant_id,
        case_id=case_id,
        organization_id=organization_id,
        facture_id=facture_id,
        montant_demande=montant_demande,
    )
    db.add(pec)
    db.commit()
    db.refresh(pec)
    return pec


def get_pec(db: Session, pec_id: int, tenant_id: int) -> PecRequest | None:
    return db.scalars(select(PecRequest).where(PecRequest.id == pec_id, PecRequest.tenant_id == tenant_id)).first()


def list_pec(
    db: Session,
    tenant_id: int,
    status: str | None = None,
    organization_id: int | None = None,
    limit: int = 25,
    offset: int = 0,
) -> list[dict]:
    q = (
        select(
            PecRequest.id,
            PecRequest.case_id,
            PecRequest.organization_id,
            PecRequest.facture_id,
            PecRequest.montant_demande,
            PecRequest.montant_accorde,
            PecRequest.status,
            PecRequest.created_at,
            PayerOrganization.name.label("organization_name"),
            Customer.first_name,
            Customer.last_name,
        )
        .join(PayerOrganization, PayerOrganization.id == PecRequest.organization_id)
        .join(Case, Case.id == PecRequest.case_id)
        .join(Customer, Customer.id == Case.customer_id)
        .where(PecRequest.tenant_id == tenant_id)
    )
    if status:
        q = q.where(PecRequest.status == status)
    if organization_id:
        q = q.where(PecRequest.organization_id == organization_id)
    q = q.order_by(PecRequest.id.desc()).limit(limit).offset(offset)
    rows = db.execute(q).all()
    return [
        {
            "id": r.id,
            "case_id": r.case_id,
            "organization_id": r.organization_id,
            "facture_id": r.facture_id,
            "montant_demande": float(r.montant_demande),
            "montant_accorde": float(r.montant_accorde) if r.montant_accorde is not None else None,
            "status": r.status,
            "created_at": r.created_at,
            "organization_name": r.organization_name,
            "customer_name": f"{r.first_name} {r.last_name}",
        }
        for r in rows
    ]


def update_status(db: Session, pec: PecRequest, new_status: str, montant_accorde: float | None = None) -> None:
    pec.status = new_status
    if montant_accorde is not None:
        pec.montant_accorde = montant_accorde
    db.commit()
    db.refresh(pec)


# --- PEC Status History ---


def add_history(
    db: Session, tenant_id: int, pec_id: int, old_status: str, new_status: str, comment: str | None = None
) -> PecStatusHistory:
    h = PecStatusHistory(
        tenant_id=tenant_id,
        pec_request_id=pec_id,
        old_status=old_status,
        new_status=new_status,
        comment=comment,
    )
    db.add(h)
    db.commit()
    db.refresh(h)
    return h


def get_history(db: Session, pec_id: int, tenant_id: int) -> list[PecStatusHistory]:
    return list(
        db.scalars(
            select(PecStatusHistory)
            .where(PecStatusHistory.pec_request_id == pec_id, PecStatusHistory.tenant_id == tenant_id)
            .order_by(PecStatusHistory.created_at)
        ).all()
    )


# --- Relances ---


def create_relance(db: Session, tenant_id: int, pec_id: int, type: str, contenu: str | None, user_id: int) -> Relance:
    r = Relance(
        tenant_id=tenant_id,
        pec_request_id=pec_id,
        type=type,
        contenu=contenu,
        created_by=user_id,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def get_relances(db: Session, pec_id: int, tenant_id: int) -> list[Relance]:
    return list(
        db.scalars(
            select(Relance)
            .where(Relance.pec_request_id == pec_id, Relance.tenant_id == tenant_id)
            .order_by(Relance.date_envoi.desc())
        ).all()
    )
