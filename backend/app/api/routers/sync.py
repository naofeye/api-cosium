from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import require_tenant_role
from app.core.exceptions import BusinessError
from app.core.redis_cache import acquire_lock, cache_delete_pattern, release_lock
from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.sync import ERPTypeItem, SeedDemoResponse, SyncAllResult, SyncResultResponse, SyncStatusResponse
from app.services import erp_sync_service

router = APIRouter(prefix="/api/v1/sync", tags=["sync"])


def _invalidate_tenant_caches(tenant_id: int) -> None:
    """Invalidate all cached data for a tenant after sync operations."""
    cache_delete_pattern(f"analytics:*:{tenant_id}*")
    cache_delete_pattern(f"admin:metrics:{tenant_id}")
    cache_delete_pattern(f"admin:data_quality:{tenant_id}")
    cache_delete_pattern(f"client:quick:{tenant_id}:*")
    cache_delete_pattern(f"dashboard:*:{tenant_id}*")


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
    lock_key = f"sync:customers:{tenant_ctx.tenant_id}"
    if not acquire_lock(lock_key, ttl=600):
        raise BusinessError("SYNC_IN_PROGRESS", "Une synchronisation des clients est deja en cours. Veuillez patienter.")
    try:
        result = erp_sync_service.sync_customers(
            db,
            tenant_id=tenant_ctx.tenant_id,
            user_id=tenant_ctx.user_id,
        )
        _invalidate_tenant_caches(tenant_ctx.tenant_id)
        return result
    finally:
        release_lock(lock_key)


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
    result = erp_sync_service.sync_invoices(
        db,
        tenant_id=tenant_ctx.tenant_id,
        user_id=tenant_ctx.user_id,
    )
    _invalidate_tenant_caches(tenant_ctx.tenant_id)
    return result


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
    result = erp_sync_service.sync_payments(
        db,
        tenant_id=tenant_ctx.tenant_id,
        user_id=tenant_ctx.user_id,
    )
    _invalidate_tenant_caches(tenant_ctx.tenant_id)
    return result


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
    "/enrich-clients",
    summary="Enrichir les metadonnees clients",
    description=(
        "Recupere l'opticien referent et l'ophtalmologiste pour les clients "
        "qui n'ont pas encore ces informations. Limité aux N premiers clients "
        "pour eviter de surcharger l'API Cosium (1 appel par client)."
    ),
)
def enrich_clients(
    limit: int = 500,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> dict:
    lock_key = f"sync:enrich:{tenant_ctx.tenant_id}"
    if not acquire_lock(lock_key, ttl=1200):
        raise BusinessError(
            "ENRICH_IN_PROGRESS",
            "Un enrichissement est deja en cours. Veuillez patienter.",
        )
    try:
        return erp_sync_service.enrich_top_clients_metadata(
            db,
            tenant_id=tenant_ctx.tenant_id,
            user_id=tenant_ctx.user_id,
            limit=limit,
        )
    finally:
        release_lock(lock_key)


@router.post(
    "/all",
    response_model=SyncAllResult,
    summary="Synchroniser tout",
    description="Lance une synchronisation complete de toutes les donnees ERP.",
)
def sync_all(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> SyncAllResult:
    lock_key = f"sync:all:{tenant_ctx.tenant_id}"
    if not acquire_lock(lock_key, ttl=1200):
        raise BusinessError("SYNC_IN_PROGRESS", "Une synchronisation complete est deja en cours. Veuillez patienter.")
    try:
        results: dict[str, object] = {}
        has_errors = False
        for sync_name, sync_fn in [
            ("customers", erp_sync_service.sync_customers),
            ("invoices", erp_sync_service.sync_invoices),
            ("payments", erp_sync_service.sync_payments),
            ("prescriptions", erp_sync_service.sync_prescriptions),
        ]:
            try:
                results[sync_name] = sync_fn(db, tenant_id=tenant_ctx.tenant_id, user_id=tenant_ctx.user_id)
            except Exception as e:
                from app.core.logging import get_logger
                get_logger("sync").error("sync_domain_failed", domain=sync_name, error=str(e))
                results[sync_name] = {"error": "Echec de la synchronisation. Consultez les logs pour plus de details."}
                has_errors = True

        # Sync reference data (calendar, mutuelles, doctors, etc.)
        try:
            from app.services.cosium_reference_sync import sync_all_reference

            ref_results = sync_all_reference(db, tenant_id=tenant_ctx.tenant_id, user_id=tenant_ctx.user_id)
            results["reference"] = ref_results
        except Exception as e:
            from app.core.logging import get_logger
            get_logger("sync").error("sync_reference_failed", error=str(e))
            results["reference"] = {"error": "Echec de la synchronisation des donnees de reference."}
            has_errors = True

        # Invalidate cached data after sync
        _invalidate_tenant_caches(tenant_ctx.tenant_id)
        return SyncAllResult(**results, has_errors=has_errors)
    finally:
        release_lock(lock_key)


@router.post(
    "/import-cosium-quotes",
    summary="Importer les devis Cosium",
    description=(
        "Convertit les devis (QUOTE) synchronises depuis Cosium en devis OptiFlow. "
        "Cree les dossiers manquants si necessaire. Idempotent : les devis deja importes sont ignores."
    ),
)
def import_cosium_quotes(
    customer_id: int | None = None,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin")),
) -> dict:
    from app.services.devis_import_service import import_cosium_quotes_as_devis

    lock_key = f"sync:import_quotes:{tenant_ctx.tenant_id}"
    if not acquire_lock(lock_key, ttl=1200):
        raise BusinessError(
            "IMPORT_IN_PROGRESS",
            "Un import de devis est deja en cours. Veuillez patienter.",
        )
    try:
        result = import_cosium_quotes_as_devis(
            db,
            tenant_id=tenant_ctx.tenant_id,
            user_id=tenant_ctx.user_id,
            customer_id=customer_id,
        )
        _invalidate_tenant_caches(tenant_ctx.tenant_id)
        return result
    finally:
        release_lock(lock_key)


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
