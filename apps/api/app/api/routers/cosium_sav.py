"""Routes de lecture des dossiers SAV Cosium — LECTURE SEULE.

Expose au frontend le suivi apres-vente (reparations, garanties).
Workflow statut : TO_REPAIR -> IN_PROCESS -> REPAIR_IN_PROCESS -> FINISHED
Resolution : RESOLVED / SOLD_OUT
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.sav import AfterSalesServiceResponse
from app.integrations.cosium.adapter import cosium_after_sales_to_optiflow
from app.integrations.cosium.cosium_connector import CosiumConnector
from app.services.erp_auth_service import _authenticate_connector, _get_connector_for_tenant

router = APIRouter(prefix="/api/v1/cosium/sav", tags=["cosium-sav"])


def _get_cosium_connector(db: Session, tenant_id: int) -> CosiumConnector:
    connector, tenant = _get_connector_for_tenant(db, tenant_id)
    if not isinstance(connector, CosiumConnector):
        from app.core.exceptions import BusinessError
        raise BusinessError("Le tenant n'utilise pas Cosium comme ERP")
    _authenticate_connector(connector, tenant)
    return connector


@router.get(
    "",
    response_model=list[AfterSalesServiceResponse],
    summary="Liste les dossiers SAV",
    description="Recupere les dossiers SAV Cosium avec filtres optionnels (statut, date, site).",
)
def list_sav(
    status: str | None = Query(None, description="TO_REPAIR, IN_PROCESS, REPAIR_IN_PROCESS, FINISHED"),
    resolution_status: str | None = Query(None, description="RESOLVED, SOLD_OUT"),
    creation_date: str | None = Query(None, description="Format yyyy-mm-dd"),
    site_name: str | None = None,
    page: int = Query(0, ge=0),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[AfterSalesServiceResponse]:
    connector = _get_cosium_connector(db, tenant_ctx.tenant_id)
    items = connector.list_after_sales_services(
        status=status,
        resolution_status=resolution_status,
        creation_date=creation_date,
        site_name=site_name,
        page=page,
        page_size=page_size,
        max_pages=1,
    )
    return [AfterSalesServiceResponse(**cosium_after_sales_to_optiflow(i)) for i in items]


@router.get(
    "/{sav_id}",
    response_model=AfterSalesServiceResponse,
    summary="Detail dossier SAV",
    description="Retourne le detail d'un dossier SAV Cosium.",
)
def get_sav(
    sav_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> AfterSalesServiceResponse:
    connector = _get_cosium_connector(db, tenant_ctx.tenant_id)
    raw = connector.get_after_sales_service(sav_id)
    return AfterSalesServiceResponse(**cosium_after_sales_to_optiflow(raw))
