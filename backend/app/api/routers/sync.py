from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import require_tenant_role
from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.sync import ERPTypeItem, SeedDemoResponse, SyncResultResponse, SyncStatusResponse
from app.services import erp_sync_service

router = APIRouter(prefix="/api/v1/sync", tags=["sync"])


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
    from app.seed_demo import seed_demo_data

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


@router.post(
    "/customers",
    response_model=SyncResultResponse,
    summary="Synchroniser les clients",
    description="Lance une synchronisation des clients depuis l'ERP.",
)
def sync_customers(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> SyncResultResponse:
    return erp_sync_service.sync_customers(
        db,
        tenant_id=tenant_ctx.tenant_id,
        user_id=tenant_ctx.user_id,
    )


@router.post(
    "/invoices",
    response_model=SyncResultResponse,
    summary="Synchroniser les factures",
    description="Lance une synchronisation des factures depuis l'ERP.",
)
def sync_invoices(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> SyncResultResponse:
    return erp_sync_service.sync_invoices(
        db,
        tenant_id=tenant_ctx.tenant_id,
        user_id=tenant_ctx.user_id,
    )


@router.post(
    "/products",
    response_model=SyncResultResponse,
    summary="Synchroniser les produits",
    description="Lance une synchronisation des produits depuis l'ERP.",
)
def sync_products(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> SyncResultResponse:
    return erp_sync_service.sync_products(
        db,
        tenant_id=tenant_ctx.tenant_id,
        user_id=tenant_ctx.user_id,
    )


@router.get(
    "/erp-types",
    response_model=list[ERPTypeItem],
    summary="Types d'ERP supportes",
    description="Liste les types d'ERP supportes et prevus.",
)
def list_erp_types(
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[ERPTypeItem]:
    """Liste les types d'ERP supportes et prevus."""
    from app.integrations.erp_factory import list_erp_types

    return list_erp_types()
