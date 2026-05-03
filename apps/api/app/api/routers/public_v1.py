"""API publique REST v1 (read-only).

Authentifie par token Bearer (X-API-Token alternativement). Tenant fixe
par le token, pas de switch. Scopes verifies par dependency.

Endpoints V1 :
- GET /api/public/v1/clients (read:clients)
- GET /api/public/v1/clients/{id}
- GET /api/public/v1/devis (read:devis)
- GET /api/public/v1/factures (read:factures)
- GET /api/public/v1/pec-requests (read:pec)

Le format des reponses utilise les memes Pydantic schemas que l'API
interne (compatibilite OpenAPI). Pagination basique limit/offset.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.api_token_auth import ApiTokenContext, require_api_scope
from app.db.session import get_db
from app.models import Customer, Devis, Facture
from app.models.pec import PecRequest

router = APIRouter(prefix="/api/public/v1", tags=["public-api"])


# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------


@router.get(
    "/clients",
    summary="Liste des clients (read:clients)",
)
def list_clients_public(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    ctx: ApiTokenContext = Depends(require_api_scope("read:clients")),
) -> dict:
    base = select(Customer).where(Customer.tenant_id == ctx.tenant_id)
    if hasattr(Customer, "deleted_at"):
        base = base.where(Customer.deleted_at.is_(None))

    total = (
        db.scalar(select(func.count()).select_from(base.subquery())) or 0
    )
    rows = list(
        db.scalars(
            base.order_by(Customer.id).limit(limit).offset(offset)
        ).all()
    )

    return {
        "items": [
            {
                "id": c.id,
                "first_name": c.first_name,
                "last_name": c.last_name,
                "email": c.email,
                "phone": c.phone,
                "cosium_id": c.cosium_id,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in rows
        ],
        "total": int(total),
        "limit": limit,
        "offset": offset,
    }


@router.get(
    "/clients/{client_id}",
    summary="Detail client (read:clients)",
)
def get_client_public(
    client_id: int,
    db: Session = Depends(get_db),
    ctx: ApiTokenContext = Depends(require_api_scope("read:clients")),
) -> dict:
    customer = db.scalars(
        select(Customer).where(
            Customer.id == client_id, Customer.tenant_id == ctx.tenant_id
        )
    ).first()
    if customer is None:
        raise HTTPException(status_code=404, detail="Client introuvable")
    return {
        "id": customer.id,
        "first_name": customer.first_name,
        "last_name": customer.last_name,
        "email": customer.email,
        "phone": customer.phone,
        "cosium_id": customer.cosium_id,
        "created_at": customer.created_at.isoformat() if customer.created_at else None,
    }


# ---------------------------------------------------------------------------
# Devis
# ---------------------------------------------------------------------------


@router.get(
    "/devis",
    summary="Liste des devis (read:devis)",
)
def list_devis_public(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status_filter: str | None = Query(None, alias="status", max_length=50),
    db: Session = Depends(get_db),
    ctx: ApiTokenContext = Depends(require_api_scope("read:devis")),
) -> dict:
    base = select(Devis).where(Devis.tenant_id == ctx.tenant_id)
    if status_filter:
        base = base.where(Devis.status == status_filter)

    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = list(
        db.scalars(
            base.order_by(Devis.created_at.desc()).limit(limit).offset(offset)
        ).all()
    )

    return {
        "items": [
            {
                "id": d.id,
                "case_id": d.case_id,
                "status": d.status,
                "montant_ht": float(d.montant_ht or 0),
                "tva": float(d.tva or 0),
                "montant_ttc": float(d.montant_ttc or 0),
                "created_at": d.created_at.isoformat() if d.created_at else None,
                "valid_until": d.valid_until.isoformat() if getattr(d, "valid_until", None) else None,
            }
            for d in rows
        ],
        "total": int(total),
        "limit": limit,
        "offset": offset,
    }


# ---------------------------------------------------------------------------
# Factures
# ---------------------------------------------------------------------------


@router.get(
    "/factures",
    summary="Liste des factures (read:factures)",
)
def list_factures_public(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status_filter: str | None = Query(None, alias="status", max_length=50),
    db: Session = Depends(get_db),
    ctx: ApiTokenContext = Depends(require_api_scope("read:factures")),
) -> dict:
    base = select(Facture).where(Facture.tenant_id == ctx.tenant_id)
    if status_filter:
        base = base.where(Facture.status == status_filter)

    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = list(
        db.scalars(
            base.order_by(Facture.created_at.desc()).limit(limit).offset(offset)
        ).all()
    )

    return {
        "items": [
            {
                "id": f.id,
                "numero": f.numero,
                "case_id": f.case_id,
                "devis_id": f.devis_id,
                "status": f.status,
                "montant_ht": float(f.montant_ht or 0),
                "tva": float(f.tva or 0),
                "montant_ttc": float(f.montant_ttc or 0),
                "original_facture_id": getattr(f, "original_facture_id", None),
                "motif_avoir": getattr(f, "motif_avoir", None),
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
            for f in rows
        ],
        "total": int(total),
        "limit": limit,
        "offset": offset,
    }


# ---------------------------------------------------------------------------
# PEC requests
# ---------------------------------------------------------------------------


@router.get(
    "/pec-requests",
    summary="Liste des demandes PEC (read:pec)",
)
def list_pec_requests_public(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status_filter: str | None = Query(None, alias="status", max_length=50),
    db: Session = Depends(get_db),
    ctx: ApiTokenContext = Depends(require_api_scope("read:pec")),
) -> dict:
    base = select(PecRequest).where(PecRequest.tenant_id == ctx.tenant_id)
    if status_filter:
        base = base.where(PecRequest.status == status_filter)

    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = list(
        db.scalars(
            base.order_by(PecRequest.created_at.desc()).limit(limit).offset(offset)
        ).all()
    )

    return {
        "items": [
            {
                "id": p.id,
                "case_id": p.case_id,
                "customer_id": p.customer_id,
                "status": p.status,
                "amount_requested": float(p.amount_requested or 0) if hasattr(p, "amount_requested") else None,
                "amount_accepted": float(p.amount_accepted or 0) if getattr(p, "amount_accepted", None) is not None else None,
                "submitted_at": p.submitted_at.isoformat() if getattr(p, "submitted_at", None) else None,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in rows
        ],
        "total": int(total),
        "limit": limit,
        "offset": offset,
    }
