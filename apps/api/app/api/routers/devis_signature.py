"""Endpoints signature electronique devis (admin + public)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_role
from app.core.request_ip import client_ip as resolve_client_ip
from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.devis import DevisResponse
from app.models import User
from app.services import devis_signature_service

# Public (sans tenant context) : lookup par public_token
public_router = APIRouter(prefix="/api/public/v1/devis", tags=["public-devis"])

# Admin : generation lien public + statut
admin_router = APIRouter(prefix="/api/v1/devis", tags=["devis-signature"])


class SignaturePayload(BaseModel):
    consent_text: str = Field(..., min_length=10, max_length=2000)


class PublicLinkResponse(BaseModel):
    public_token: str
    public_url: str


class PublicDevisView(BaseModel):
    """Vue limitee du devis pour la page de signature publique.

    Pas de donnees PII sensibles (email, telephone, adresse). Juste le
    necessaire pour informer le client : numero, montants, lignes.
    """

    id: int
    numero: str
    status: str
    montant_ht: float
    tva: float
    montant_ttc: float
    part_secu: float
    part_mutuelle: float
    reste_a_charge: float
    valid_until: str | None
    created_at: str
    is_signed: bool


@public_router.get(
    "/{public_token}",
    response_model=PublicDevisView,
    summary="Recupere un devis pour signature publique",
)
def get_devis_public(
    public_token: str,
    db: Session = Depends(get_db),
) -> PublicDevisView:
    devis = devis_signature_service.get_devis_by_public_token(db, public_token)
    if devis is None:
        raise HTTPException(status_code=404, detail="Lien invalide ou expire")
    return PublicDevisView(
        id=devis.id,
        numero=devis.numero,
        status=devis.status,
        montant_ht=float(devis.montant_ht or 0),
        tva=float(devis.tva or 0),
        montant_ttc=float(devis.montant_ttc or 0),
        part_secu=float(devis.part_secu or 0),
        part_mutuelle=float(devis.part_mutuelle or 0),
        reste_a_charge=float(devis.reste_a_charge or 0),
        valid_until=devis.valid_until.isoformat() if devis.valid_until else None,
        created_at=devis.created_at.isoformat(),
        is_signed=bool(devis.signed_at),
    )


@public_router.post(
    "/{public_token}/sign",
    response_model=DevisResponse,
    summary="Signe le devis (eIDAS Simple)",
)
def sign_devis_public(
    public_token: str,
    payload: SignaturePayload,
    request: Request,
    db: Session = Depends(get_db),
) -> DevisResponse:
    # Capture IP / User-Agent — X-Forwarded-For est honore UNIQUEMENT si le
    # proxy direct est dans TRUSTED_PROXIES, sinon signature_ip serait
    # forgeable depuis n'importe quel client (Codex M4).
    user_agent = request.headers.get("user-agent", "")
    return devis_signature_service.sign_devis_public(
        db,
        public_token=public_token,
        consent_text=payload.consent_text,
        client_ip=resolve_client_ip(request),
        user_agent=user_agent,
    )


@admin_router.post(
    "/{devis_id}/public-link",
    response_model=PublicLinkResponse,
    summary="Genere un lien public de signature electronique",
    dependencies=[Depends(require_role("admin", "manager"))],
)
def generate_public_link(
    devis_id: int,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
    current_user: User = Depends(get_current_user),
) -> PublicLinkResponse:
    token = devis_signature_service.ensure_public_link(
        db, ctx.tenant_id, devis_id, current_user.id
    )
    # URL relative ; le frontend prefixe avec FRONTEND_BASE_URL si necessaire
    return PublicLinkResponse(
        public_token=token, public_url=f"/devis/sign/{token}"
    )
