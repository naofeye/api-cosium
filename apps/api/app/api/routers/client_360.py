from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.http import content_disposition
from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.client_360 import Client360Response, CosiumDataBundle
from app.domain.schemas.client_360_live import Client360CosiumLive
from app.services import (
    audit_service,
    client_360_live_service,
    client_360_service,
    export_pdf,
    pdf_service,
)

router = APIRouter(prefix="/api/v1", tags=["client-360"])


@router.get(
    "/clients/{client_id}/360",
    response_model=Client360Response,
    summary="Vue 360 d'un client",
    description="Retourne la vision complete d'un client avec ses dossiers, finances et interactions.",
)
def get_client_360(
    client_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> Client360Response:
    result = client_360_service.get_client_360(
        db,
        tenant_id=tenant_ctx.tenant_id,
        client_id=client_id,
    )
    # RGPD : tracer la consultation de donnees personnelles (PII) pour audit.
    # On loggue uniquement la vue "360" complete (pas les listes), pour eviter
    # un volume excessif d'evenements. Le log est best-effort : un echec ne doit
    # pas casser la requete utilisateur.
    try:
        audit_service.log_action(
            db,
            tenant_ctx.tenant_id,
            tenant_ctx.user_id,
            "view_pii",
            "client",
            client_id,
        )
        db.commit()
    except Exception:
        db.rollback()
    return result


@router.get(
    "/clients/{client_id}/cosium-data",
    response_model=CosiumDataBundle,
    summary="Donnees Cosium d'un client",
    description="Retourne toutes les donnees Cosium d'un client en un seul appel : ordonnances, paiements, RDV, equipements, CA total.",
)
def get_client_cosium_data(
    client_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> CosiumDataBundle:
    return client_360_service.get_client_cosium_data(
        db,
        tenant_id=tenant_ctx.tenant_id,
        client_id=client_id,
    )


@router.get(
    "/clients/{client_id}/cosium-live",
    response_model=Client360CosiumLive,
    summary="Donnees Cosium LIVE d'un client (non cachees)",
    description="Agrege fidelity-cards + sponsorships + notes en temps reel depuis Cosium. Lent (3 appels reseaux), pour fiche client detaillee.",
)
def get_client_cosium_live(
    client_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> Client360CosiumLive:
    return client_360_live_service.get_client_cosium_live(
        db, tenant_id=tenant_ctx.tenant_id, client_id=client_id,
    )


@router.get(
    "/clients/{client_id}/360/pdf",
    summary="PDF vue 360",
    description="Genere et retourne le fichier PDF de la vue 360 d'un client.",
)
def download_client_360_pdf(
    client_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> Response:
    pdf_bytes = pdf_service.generate_client_360_pdf(db, client_id, tenant_ctx.tenant_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": content_disposition(f"client_{client_id}_360.pdf")},
    )


@router.get(
    "/clients/{client_id}/export-pdf",
    summary="Telecharger la fiche client PDF",
    description="Genere et telecharge un PDF complet de la fiche client avec toutes ses donnees.",
)
def export_client_pdf_endpoint(
    client_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> Response:
    pdf_bytes = export_pdf.export_client_pdf(db, client_id, tenant_ctx.tenant_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": content_disposition(f"fiche_client_{client_id}.pdf")},
    )
