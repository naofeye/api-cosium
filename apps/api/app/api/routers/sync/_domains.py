"""Endpoints de synchronisation per-domain (customers, invoices, payments, etc.).

Chaque endpoint :
- acquiert un lock Redis dédié (TTL variable selon le domaine)
- délègue au service `erp_sync_*`
- invalide les caches tenant si besoin
- libère le lock en finally
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import require_tenant_role
from app.core.redis_cache import release_lock
from app.core.tenant_context import TenantContext
from app.db.session import get_db
from app.domain.schemas.sync import SyncResultResponse
from app.services import erp_sync_service

from ._helpers import acquire_sync_lock, invalidate_tenant_caches

router = APIRouter(prefix="/api/v1/sync", tags=["sync"])


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
    acquire_sync_lock(
        lock_key,
        "Une synchronisation des clients est deja en cours. Veuillez patienter.",
        ttl=600,
    )
    try:
        result = erp_sync_service.sync_customers(
            db, tenant_id=tenant_ctx.tenant_id, user_id=tenant_ctx.user_id,
        )
        invalidate_tenant_caches(tenant_ctx.tenant_id)
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
    acquire_sync_lock(
        lock_key,
        "Une synchronisation des factures est deja en cours. Veuillez patienter.",
        ttl=1200,
    )
    try:
        result = erp_sync_service.sync_invoices(
            db, tenant_id=tenant_ctx.tenant_id, user_id=tenant_ctx.user_id, full=full,
        )
        invalidate_tenant_caches(tenant_ctx.tenant_id)
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
    acquire_sync_lock(
        lock_key,
        "Une synchronisation des produits est deja en cours. Veuillez patienter.",
        ttl=1200,
    )
    try:
        return erp_sync_service.sync_products(
            db, tenant_id=tenant_ctx.tenant_id, user_id=tenant_ctx.user_id,
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
    acquire_sync_lock(
        lock_key,
        "Une synchronisation des lignes factures est deja en cours. Veuillez patienter.",
        ttl=1800,
    )
    try:
        return cosium_invoiced_items_sync.sync_invoiced_items(
            db, tenant_id=tenant_ctx.tenant_id, user_id=tenant_ctx.user_id,
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
    acquire_sync_lock(
        lock_key,
        "Une synchronisation des paiements est deja en cours. Veuillez patienter.",
        ttl=1200,
    )
    try:
        result = erp_sync_service.sync_payments(
            db, tenant_id=tenant_ctx.tenant_id, user_id=tenant_ctx.user_id, full=full,
        )
        invalidate_tenant_caches(tenant_ctx.tenant_id)
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
    acquire_sync_lock(
        lock_key,
        "Une synchronisation des tiers payants est deja en cours. Veuillez patienter.",
        ttl=1200,
    )
    try:
        return erp_sync_service.sync_third_party_payments(
            db, tenant_id=tenant_ctx.tenant_id, user_id=tenant_ctx.user_id,
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
    acquire_sync_lock(
        lock_key,
        "Une synchronisation des ordonnances est deja en cours. Veuillez patienter.",
        ttl=1200,
    )
    try:
        return erp_sync_service.sync_prescriptions(
            db, tenant_id=tenant_ctx.tenant_id, user_id=tenant_ctx.user_id, full=full,
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
    acquire_sync_lock(
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
    acquire_sync_lock(
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
        invalidate_tenant_caches(tenant_ctx.tenant_id)
        return result
    finally:
        release_lock(lock_key)
