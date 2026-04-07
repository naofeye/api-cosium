"""Router for reconciliation — payment linking and dossier reconciliation."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.reconciliation import (
    BatchReconciliationResult,
    DossierReconciliationResponse,
    LinkPaymentsResult,
    ReconciliationSummary,
)
from app.services import reconciliation_service

router = APIRouter(prefix="/api/v1/reconciliation", tags=["reconciliation"])


@router.post(
    "/link-payments",
    response_model=LinkPaymentsResult,
    summary="Lier les paiements aux clients par correspondance de noms",
)
def link_payments(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> LinkPaymentsResult:
    return reconciliation_service.link_payments_to_customers(db, tenant_ctx.tenant_id)


@router.post(
    "/run",
    response_model=BatchReconciliationResult,
    summary="Lancer le rapprochement pour tous les clients",
)
def run_reconciliation(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> BatchReconciliationResult:
    return reconciliation_service.reconcile_all_customers(db, tenant_ctx.tenant_id)


@router.get(
    "/summary",
    response_model=ReconciliationSummary,
    summary="Resume global du rapprochement (compteurs par statut)",
)
def get_summary(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> ReconciliationSummary:
    return reconciliation_service.get_reconciliation_summary(db, tenant_ctx.tenant_id)


@router.get(
    "/customer/{customer_id}",
    response_model=DossierReconciliationResponse,
    summary="Rapprochement d'un client specifique",
)
def get_customer_reconciliation(
    customer_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> DossierReconciliationResponse:
    result = reconciliation_service.get_customer_reconciliation(
        db, tenant_ctx.tenant_id, customer_id,
    )
    if result is None:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Reconciliation", customer_id)
    return result


@router.get(
    "/anomalies",
    summary="Liste des anomalies detectees",
)
def list_anomalies(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> dict:
    import json
    from app.repositories import reconciliation_repo
    items, total = reconciliation_repo.get_anomalous_reconciliations(
        db, tenant_ctx.tenant_id, page, page_size,
    )
    results = []
    for recon in items:
        anomalies = json.loads(recon.anomalies) if recon.anomalies else []
        results.append({
            "customer_id": recon.customer_id,
            "status": recon.status,
            "anomalies": anomalies,
            "total_facture": recon.total_facture,
            "total_outstanding": recon.total_outstanding,
        })
    return {"items": results, "total": total, "page": page, "page_size": page_size}


@router.get(
    "/unsettled",
    summary="Liste des dossiers non soldes",
)
def list_unsettled(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> dict:
    from app.repositories import reconciliation_repo
    # Get all non-solde statuses
    unsettled_statuses = ["partiellement_paye", "en_attente", "incoherent"]
    all_items = []
    total = 0
    for status in unsettled_statuses:
        items, count = reconciliation_repo.get_reconciliations_by_status(
            db, tenant_ctx.tenant_id, status, page, page_size,
        )
        all_items.extend(items)
        total += count

    results = []
    for recon in all_items[:page_size]:
        results.append({
            "customer_id": recon.customer_id,
            "status": recon.status,
            "total_facture": recon.total_facture,
            "total_outstanding": recon.total_outstanding,
            "total_paid": recon.total_paid,
            "explanation": recon.explanation,
        })
    return {"items": results, "total": total, "page": page, "page_size": page_size}
