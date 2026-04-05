from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.client_360 import Client360Response, CosiumDataBundle
from app.domain.schemas.interactions import InteractionCreate, InteractionListResponse, InteractionResponse
from app.services import client_360_service, interaction_service, pdf_service
from app.services import export_pdf

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
    return client_360_service.get_client_360(
        db,
        tenant_id=tenant_ctx.tenant_id,
        client_id=client_id,
    )


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
        headers={"Content-Disposition": f"attachment; filename=client_{client_id}_360.pdf"},
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
    from io import BytesIO

    pdf_bytes = export_pdf.export_client_pdf(db, client_id, tenant_ctx.tenant_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=fiche_client_{client_id}.pdf"},
    )


@router.get(
    "/clients/{client_id}/interactions",
    response_model=InteractionListResponse,
    summary="Historique des interactions",
    description="Retourne la chronologie des interactions avec un client.",
)
def list_interactions(
    client_id: int,
    type: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> InteractionListResponse:
    items, total = interaction_service.get_client_timeline(
        db,
        tenant_id=tenant_ctx.tenant_id,
        client_id=client_id,
        type=type,
        limit=limit,
    )
    return InteractionListResponse(items=items, total=total)


@router.post(
    "/interactions",
    response_model=InteractionResponse,
    status_code=201,
    summary="Ajouter une interaction",
    description="Enregistre une nouvelle interaction avec un client.",
)
def create_interaction(
    payload: InteractionCreate,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> InteractionResponse:
    return interaction_service.add_interaction(
        db,
        tenant_id=tenant_ctx.tenant_id,
        payload=payload,
        user_id=tenant_ctx.user_id,
    )


@router.delete(
    "/interactions/{interaction_id}",
    status_code=200,
    summary="Supprimer une interaction",
    description="Supprime une interaction du journal.",
)
def delete_interaction(
    interaction_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> dict[str, str]:
    interaction_service.delete_interaction(
        db,
        tenant_id=tenant_ctx.tenant_id,
        interaction_id=interaction_id,
        user_id=tenant_ctx.user_id,
    )
    return {"message": "Interaction supprimee avec succes"}
