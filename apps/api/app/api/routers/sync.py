from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import require_tenant_role
from app.core.exceptions import BusinessError
from app.core.logging import get_logger
from app.core.redis_cache import acquire_lock, cache_delete_pattern, release_lock
from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.sync import ERPTypeItem, SeedDemoResponse, SyncAllResult, SyncResultResponse, SyncStatusResponse
from app.services import erp_sync_service

logger = get_logger("sync")

router = APIRouter(prefix="/api/v1/sync", tags=["sync"])


def _invalidate_tenant_caches(tenant_id: int) -> None:
    """Invalidate all cached data for a tenant after sync operations."""
    cache_delete_pattern(f"analytics:*:{tenant_id}*")
    cache_delete_pattern(f"admin:metrics:{tenant_id}")
    cache_delete_pattern(f"admin:data_quality:{tenant_id}")
    cache_delete_pattern(f"client:quick:{tenant_id}:*")
    cache_delete_pattern(f"dashboard:*:{tenant_id}*")


def _acquire_sync_lock(lock_key: str, message: str, ttl: int = 1200) -> None:
    if not acquire_lock(lock_key, ttl=ttl):
        raise BusinessError(message=message, code="SYNC_IN_PROGRESS")


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
    _acquire_sync_lock(
        lock_key,
        "Une synchronisation des clients est deja en cours. Veuillez patienter.",
        ttl=600,
    )
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
    description=(
        "Lance une synchronisation des factures depuis l'ERP. "
        "Par defaut, sync incrementale (uniquement les recentes). "
        "Passer full=true pour re-telecharger tout."
    ),
)
def sync_invoices(
    full: bool = False,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> SyncResultResponse:
    lock_key = f"sync:invoices:{tenant_ctx.tenant_id}"
    _acquire_sync_lock(
        lock_key,
        "Une synchronisation des factures est deja en cours. Veuillez patienter.",
        ttl=1200,
    )
    try:
        result = erp_sync_service.sync_invoices(
            db,
            tenant_id=tenant_ctx.tenant_id,
            user_id=tenant_ctx.user_id,
            full=full,
        )
        _invalidate_tenant_caches(tenant_ctx.tenant_id)
        return result
    finally:
        release_lock(lock_key)


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
    lock_key = f"sync:products:{tenant_ctx.tenant_id}"
    _acquire_sync_lock(
        lock_key,
        "Une synchronisation des produits est deja en cours. Veuillez patienter.",
        ttl=1200,
    )
    try:
        return erp_sync_service.sync_products(
            db,
            tenant_id=tenant_ctx.tenant_id,
            user_id=tenant_ctx.user_id,
        )
    finally:
        release_lock(lock_key)


@router.post(
    "/invoiced-items",
    summary="Synchroniser les lignes de factures (invoiced-items)",
    description=(
        "Sync Cosium `/invoiced-items` → table locale `cosium_invoiced_items`. "
        "Permet ensuite la ventilation par famille produit via /dashboard/product-mix."
    ),
)
def sync_invoiced_items(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> dict:
    from app.services import cosium_invoiced_items_sync

    lock_key = f"sync:invoiced-items:{tenant_ctx.tenant_id}"
    _acquire_sync_lock(
        lock_key,
        "Une synchronisation des lignes factures est deja en cours. Veuillez patienter.",
        ttl=1800,
    )
    try:
        return cosium_invoiced_items_sync.sync_invoiced_items(
            db, tenant_id=tenant_ctx.tenant_id, user_id=tenant_ctx.user_id
        )
    finally:
        release_lock(lock_key)


@router.post(
    "/payments",
    response_model=SyncResultResponse,
    summary="Synchroniser les paiements",
    description=(
        "Lance une synchronisation des paiements depuis l'ERP. "
        "Par defaut, sync incrementale. Passer full=true pour tout re-telecharger."
    ),
)
def sync_payments(
    full: bool = False,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> SyncResultResponse:
    lock_key = f"sync:payments:{tenant_ctx.tenant_id}"
    _acquire_sync_lock(
        lock_key,
        "Une synchronisation des paiements est deja en cours. Veuillez patienter.",
        ttl=1200,
    )
    try:
        result = erp_sync_service.sync_payments(
            db,
            tenant_id=tenant_ctx.tenant_id,
            user_id=tenant_ctx.user_id,
            full=full,
        )
        _invalidate_tenant_caches(tenant_ctx.tenant_id)
        return result
    finally:
        release_lock(lock_key)


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
    lock_key = f"sync:third-party-payments:{tenant_ctx.tenant_id}"
    _acquire_sync_lock(
        lock_key,
        "Une synchronisation des tiers payants est deja en cours. Veuillez patienter.",
        ttl=1200,
    )
    try:
        return erp_sync_service.sync_third_party_payments(
            db,
            tenant_id=tenant_ctx.tenant_id,
            user_id=tenant_ctx.user_id,
        )
    finally:
        release_lock(lock_key)


@router.post(
    "/prescriptions",
    response_model=SyncResultResponse,
    summary="Synchroniser les ordonnances",
    description=(
        "Lance une synchronisation des ordonnances optiques depuis l'ERP. "
        "Par defaut, sync incrementale. Passer full=true pour tout re-telecharger."
    ),
)
def sync_prescriptions(
    full: bool = False,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> SyncResultResponse:
    lock_key = f"sync:prescriptions:{tenant_ctx.tenant_id}"
    _acquire_sync_lock(
        lock_key,
        "Une synchronisation des ordonnances est deja en cours. Veuillez patienter.",
        ttl=1200,
    )
    try:
        return erp_sync_service.sync_prescriptions(
            db,
            tenant_id=tenant_ctx.tenant_id,
            user_id=tenant_ctx.user_id,
            full=full,
        )
    finally:
        release_lock(lock_key)


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
    limit: int = Query(500, ge=1, le=1000),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> dict:
    lock_key = f"sync:enrich:{tenant_ctx.tenant_id}"
    _acquire_sync_lock(
        lock_key,
        "Un enrichissement est deja en cours. Veuillez patienter.",
        ttl=1200,
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
    summary="Synchroniser tout (incremental)",
    description=(
        "Lance une synchronisation incrementale de toutes les donnees ERP. "
        "Seules les nouvelles donnees sont telechargees. "
        "Passer full=true pour forcer un re-telechargement complet."
    ),
)
def sync_all(
    full: bool = False,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
):
    lock_key = f"sync:all:{tenant_ctx.tenant_id}"
    _acquire_sync_lock(
        lock_key,
        "Une synchronisation complete est deja en cours. Veuillez patienter.",
        ttl=1200,
    )
    try:
        results: dict[str, object] = {}
        has_errors = False

        # Customers sync (deja incremental par nature — upsert par cosium_id)
        for sync_name, sync_fn in [
            ("customers", erp_sync_service.sync_customers),
        ]:
            try:
                results[sync_name] = sync_fn(db, tenant_id=tenant_ctx.tenant_id, user_id=tenant_ctx.user_id)
            except Exception as e:
                logger.error("sync_domain_failed", domain=sync_name, error=str(e))
                results[sync_name] = {"error": "Echec de la synchronisation. Consultez les logs pour plus de details."}
                has_errors = True

        # Sync with incremental support
        for sync_name, sync_fn in [
            ("invoices", erp_sync_service.sync_invoices),
            ("payments", erp_sync_service.sync_payments),
            ("prescriptions", erp_sync_service.sync_prescriptions),
        ]:
            try:
                results[sync_name] = sync_fn(
                    db, tenant_id=tenant_ctx.tenant_id, user_id=tenant_ctx.user_id, full=full,
                )
            except Exception as e:
                logger.error("sync_domain_failed", domain=sync_name, error=str(e))
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
        result = SyncAllResult(**results, has_errors=has_errors)
        if has_errors:
            return JSONResponse(
                status_code=207,
                content=result.model_dump(mode="json"),
            )
        return result
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
    _acquire_sync_lock(
        lock_key,
        "Un import de devis est deja en cours. Veuillez patienter.",
        ttl=1200,
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
