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


@router.post(
    "/payments",
    response_model=SyncResultResponse,
    summary="Synchroniser les paiements",
    description="Lance une synchronisation des paiements de factures depuis l'ERP.",
)
def sync_payments(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> SyncResultResponse:
    return erp_sync_service.sync_payments(
        db,
        tenant_id=tenant_ctx.tenant_id,
        user_id=tenant_ctx.user_id,
    )


@router.post(
    "/third-party-payments",
    response_model=SyncResultResponse,
    summary="Synchroniser les tiers payants",
    description="Lance une synchronisation des tiers payants (secu + mutuelle) depuis l'ERP.",
)
def sync_third_party_payments(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> SyncResultResponse:
    return erp_sync_service.sync_third_party_payments(
        db,
        tenant_id=tenant_ctx.tenant_id,
        user_id=tenant_ctx.user_id,
    )


@router.post(
    "/prescriptions",
    response_model=SyncResultResponse,
    summary="Synchroniser les ordonnances",
    description="Lance une synchronisation des ordonnances optiques depuis l'ERP.",
)
def sync_prescriptions(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> SyncResultResponse:
    return erp_sync_service.sync_prescriptions(
        db,
        tenant_id=tenant_ctx.tenant_id,
        user_id=tenant_ctx.user_id,
    )


@router.post(
    "/all",
    response_model=dict,
    summary="Synchroniser tout",
    description="Lance une synchronisation complete de toutes les donnees ERP.",
)
def sync_all(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> dict:
    results = {}
    for sync_name, sync_fn in [
        ("customers", erp_sync_service.sync_customers),
        ("invoices", erp_sync_service.sync_invoices),
        ("payments", erp_sync_service.sync_payments),
        ("prescriptions", erp_sync_service.sync_prescriptions),
    ]:
        try:
            results[sync_name] = sync_fn(db, tenant_id=tenant_ctx.tenant_id, user_id=tenant_ctx.user_id)
        except Exception as e:
            results[sync_name] = {"error": str(e)}

    # Sync reference data (calendar, mutuelles, doctors, etc.)
    try:
        from app.services.cosium_reference_sync import sync_all_reference

        ref_results = sync_all_reference(db, tenant_id=tenant_ctx.tenant_id, user_id=tenant_ctx.user_id)
        results["reference"] = ref_results
    except Exception as e:
        results["reference"] = {"error": str(e)}

    return results


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
