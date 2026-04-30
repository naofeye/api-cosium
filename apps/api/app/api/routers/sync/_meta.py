"""Endpoints méta (status, erp-types, seed-demo)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import require_tenant_role
from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.sync import ERPTypeItem, SeedDemoResponse, SyncStatusResponse
from app.services import erp_sync_service

router = APIRouter(prefix="/api/v1/sync", tags=["sync"])

_SEED_DEMO_ALLOWED_ENVS = ("local", "development", "test")


@router.post(
    "/seed-demo",
    response_model=SeedDemoResponse,
    summary="Injecter des donnees de demo",
    description="Cree un jeu de donnees de demonstration (admin uniquement).",
)
def seed_demo(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin")),
) -> SeedDemoResponse:
    # Garde-fou : seed-demo importe tests.factories.seed et n a aucune
    # raison d etre exposable en staging/production. Refus dur si APP_ENV
    # n est pas un environnement de developpement.
    if settings.app_env not in _SEED_DEMO_ALLOWED_ENVS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Endpoint indisponible en environnement non-dev.",
        )
    from tests.factories.seed import seed_demo_data

    return seed_demo_data(db)


@router.get(
    "/status",
    response_model=SyncStatusResponse,
    summary="Statut de synchronisation",
    description="Retourne le statut de la derniere synchronisation ERP.",
)
def get_sync_status(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> SyncStatusResponse:
    return erp_sync_service.get_sync_status(db, tenant_ctx.tenant_id)


@router.get(
    "/erp-types",
    response_model=list[ERPTypeItem],
    summary="Types d'ERP supportes",
    description="Liste les types d'ERP supportes et prevus.",
)
def list_erp_types(
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[ERPTypeItem]:
    from app.integrations.erp_factory import list_erp_types as _list_erp_types

    return _list_erp_types()
