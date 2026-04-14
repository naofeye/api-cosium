"""Routes de lecture du catalogue optique Cosium — LECTURE SEULE.

Expose au frontend le catalogue montures + verres pour navigation et selection.
Pas de persistance locale — lecture live via Cosium.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.optical_catalog import OpticalFrameResponse, OpticalLensResponse
from app.integrations.cosium.adapter import (
    cosium_optical_frame_to_optiflow,
    cosium_optical_lens_to_optiflow,
)
from app.integrations.cosium.cosium_connector import CosiumConnector
from app.services.erp_auth_service import _authenticate_connector, _get_connector_for_tenant

router = APIRouter(prefix="/api/v1/cosium/catalog", tags=["cosium-catalog"])


def _get_cosium_connector(db: Session, tenant_id: int) -> CosiumConnector:
    connector, tenant = _get_connector_for_tenant(db, tenant_id)
    if not isinstance(connector, CosiumConnector):
        from app.core.exceptions import BusinessError
        raise BusinessError("Le tenant n'utilise pas Cosium comme ERP")
    _authenticate_connector(connector, tenant)
    return connector


@router.get(
    "/frames",
    response_model=list[OpticalFrameResponse],
    summary="Catalogue montures",
    description="Liste les montures du catalogue Cosium (paginee).",
)
def list_frames(
    page: int = Query(0, ge=0),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[OpticalFrameResponse]:
    connector = _get_cosium_connector(db, tenant_ctx.tenant_id)
    items = connector.list_optical_frames(page=page, page_size=page_size, max_pages=1)
    return [OpticalFrameResponse(**cosium_optical_frame_to_optiflow(i)) for i in items]


@router.get(
    "/frames/{frame_id}",
    response_model=OpticalFrameResponse,
    summary="Detail monture",
    description="Retourne le detail d'une monture du catalogue Cosium.",
)
def get_frame(
    frame_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> OpticalFrameResponse:
    connector = _get_cosium_connector(db, tenant_ctx.tenant_id)
    raw = connector.get_optical_frame(frame_id)
    return OpticalFrameResponse(**cosium_optical_frame_to_optiflow(raw))


@router.get(
    "/lenses",
    response_model=list[OpticalLensResponse],
    summary="Catalogue verres",
    description="Liste les verres du catalogue Cosium (paginee).",
)
def list_lenses(
    page: int = Query(0, ge=0),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[OpticalLensResponse]:
    connector = _get_cosium_connector(db, tenant_ctx.tenant_id)
    items = connector.list_optical_lenses(page=page, page_size=page_size, max_pages=1)
    return [OpticalLensResponse(**cosium_optical_lens_to_optiflow(i)) for i in items]


@router.get(
    "/lenses/{lens_id}",
    response_model=OpticalLensResponse,
    summary="Detail verre",
    description="Retourne le detail d'un verre du catalogue Cosium.",
)
def get_lens(
    lens_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> OpticalLensResponse:
    connector = _get_cosium_connector(db, tenant_ctx.tenant_id)
    raw = connector.get_optical_lens(lens_id)
    return OpticalLensResponse(**cosium_optical_lens_to_optiflow(raw))


@router.get(
    "/lenses/{lens_id}/options",
    summary="Options disponibles pour un verre",
    description="Retourne les options (traitement, teinte, ...) disponibles pour un verre.",
)
def get_lens_options(
    lens_id: int,
    code: str | None = Query(None, description="Code d'option specifique"),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> dict:
    connector = _get_cosium_connector(db, tenant_ctx.tenant_id)
    return connector.get_optical_lens_options(lens_id, code=code)
