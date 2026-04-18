"""Router for Cosium invoices — read-only listing of synced Cosium data."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.cosium_invoices import (
    CosiumInvoiceListResponse,
    CosiumInvoiceTotals,
    CosiumInvoiceTotalsByType,
)
from app.services import cosium_invoice_service

router = APIRouter(prefix="/api/v1", tags=["cosium-invoices"])


# ---------------------------------------------------------------------------
# Convenience endpoints filtered by type
# ---------------------------------------------------------------------------


@router.get(
    "/cosium/factures-cosium",
    response_model=CosiumInvoiceListResponse,
    summary="Factures Cosium (type INVOICE uniquement)",
)
def list_cosium_factures(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    settled: bool | None = Query(None),
    search: str | None = Query(None, max_length=100),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    archived: bool | None = Query(None, description="Filtrer factures archivees"),
    has_outstanding: bool | None = Query(None, description="True = encours > 0"),
    min_amount: float | None = Query(None, description="Montant min EUR"),
    max_amount: float | None = Query(None, description="Montant max EUR"),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> CosiumInvoiceListResponse:
    return cosium_invoice_service.list_invoices(
        db, tenant_id=tenant_ctx.tenant_id, page=page, page_size=page_size,
        type_filter="INVOICE", settled=settled, search=search,
        date_from=date_from, date_to=date_to,
        archived=archived, has_outstanding=has_outstanding,
        min_amount=min_amount, max_amount=max_amount,
    )


@router.get(
    "/cosium/devis-cosium",
    response_model=CosiumInvoiceListResponse,
    summary="Devis Cosium (type QUOTE uniquement)",
)
def list_cosium_devis(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    settled: bool | None = Query(None),
    search: str | None = Query(None, max_length=100),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> CosiumInvoiceListResponse:
    return cosium_invoice_service.list_invoices(
        db, tenant_id=tenant_ctx.tenant_id, page=page, page_size=page_size,
        type_filter="QUOTE", settled=settled, search=search,
        date_from=date_from, date_to=date_to,
    )


@router.get(
    "/cosium/avoirs",
    response_model=CosiumInvoiceListResponse,
    summary="Avoirs Cosium (type CREDIT_NOTE uniquement)",
)
def list_cosium_avoirs(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    settled: bool | None = Query(None),
    search: str | None = Query(None, max_length=100),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> CosiumInvoiceListResponse:
    return cosium_invoice_service.list_invoices(
        db, tenant_id=tenant_ctx.tenant_id, page=page, page_size=page_size,
        type_filter="CREDIT_NOTE", settled=settled, search=search,
        date_from=date_from, date_to=date_to,
    )


@router.get(
    "/cosium/commandes-fournisseur",
    response_model=CosiumInvoiceListResponse,
    summary="Commandes fournisseur Cosium (type SUPPLIER_ORDER_FORM uniquement)",
)
def list_cosium_commandes_fournisseur(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: str | None = Query(None, max_length=100),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> CosiumInvoiceListResponse:
    return cosium_invoice_service.list_invoices(
        db, tenant_id=tenant_ctx.tenant_id, page=page, page_size=page_size,
        type_filter="SUPPLIER_ORDER_FORM", search=search,
        date_from=date_from, date_to=date_to,
    )


@router.get(
    "/cosium/invoices/{invoice_cosium_id}/payment-links",
    summary="Liens de paiement en ligne (live)",
    description="Recupere les URLs de paiement en ligne d'une facture Cosium si disponibles.",
)
def get_invoice_payment_links(
    invoice_cosium_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> dict:
    from app.core.exceptions import BusinessError, ExternalServiceError
    from app.integrations.cosium.cosium_connector import CosiumConnector
    from app.services.erp_auth_service import _authenticate_connector, _get_connector_for_tenant
    connector, tenant = _get_connector_for_tenant(db, tenant_ctx.tenant_id)
    if not isinstance(connector, CosiumConnector):
        raise BusinessError("Le tenant n'utilise pas Cosium comme ERP")
    _authenticate_connector(connector, tenant)
    try:
        return connector.get_invoice_payment_links(invoice_cosium_id)
    except Exception as e:
        raise ExternalServiceError(f"Liens paiement Cosium {invoice_cosium_id} indisponibles : {str(e)[:100]}") from e


@router.get(
    "/cosium/invoice-payments/{payment_id}",
    summary="Detail reglement Cosium (live)",
    description="Recupere un reglement de facture Cosium en live (montant, banque, date valeur, code comptable, ...).",
)
def get_invoice_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> dict:
    from app.core.exceptions import BusinessError, ExternalServiceError
    from app.integrations.cosium.cosium_connector import CosiumConnector
    from app.services.erp_auth_service import _authenticate_connector, _get_connector_for_tenant
    connector, tenant = _get_connector_for_tenant(db, tenant_ctx.tenant_id)
    if not isinstance(connector, CosiumConnector):
        raise BusinessError("Le tenant n'utilise pas Cosium comme ERP")
    _authenticate_connector(connector, tenant)
    try:
        return connector.get_invoice_payment(payment_id)
    except Exception as e:
        raise ExternalServiceError(f"Reglement Cosium {payment_id} indisponible : {str(e)[:100]}") from e


@router.get(
    "/cosium-invoices/totals-by-type",
    response_model=CosiumInvoiceTotalsByType,
    summary="Totaux par type de document Cosium",
    description="Retourne les totaux (montant, nombre) ventiles par type (INVOICE, QUOTE, CREDIT_NOTE, etc.).",
)
def get_cosium_invoice_totals_by_type(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> CosiumInvoiceTotalsByType:
    return cosium_invoice_service.get_totals_by_type(
        db, tenant_id=tenant_ctx.tenant_id,
    )


@router.get(
    "/cosium-invoices",
    response_model=CosiumInvoiceListResponse,
    summary="Lister les factures Cosium",
    description="Retourne la liste paginee des factures synchronisees depuis Cosium.",
)
def list_cosium_invoices(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    type_filter: str | None = Query(None, description="Filtrer par type : INVOICE, QUOTE, CREDIT_NOTE"),
    settled: bool | None = Query(None, description="Filtrer par statut de reglement"),
    search: str | None = Query(None, max_length=100, description="Recherche par numero ou nom client"),
    date_from: date | None = Query(None, description="Date de debut (YYYY-MM-DD)"),
    date_to: date | None = Query(None, description="Date de fin (YYYY-MM-DD)"),
    archived: bool | None = Query(None, description="Filtrer factures archivees"),
    has_outstanding: bool | None = Query(None, description="True = encours > 0"),
    min_amount: float | None = Query(None, description="Montant min EUR"),
    max_amount: float | None = Query(None, description="Montant max EUR"),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> CosiumInvoiceListResponse:
    return cosium_invoice_service.list_invoices(
        db,
        tenant_id=tenant_ctx.tenant_id,
        page=page,
        page_size=page_size,
        type_filter=type_filter,
        settled=settled,
        search=search,
        date_from=date_from,
        date_to=date_to,
        archived=archived,
        has_outstanding=has_outstanding,
        min_amount=min_amount,
        max_amount=max_amount,
    )


@router.get(
    "/cosium-invoices/totals",
    response_model=CosiumInvoiceTotals,
    summary="Totaux des factures Cosium",
    description="Retourne les totaux agreg pour les filtres actuels (toutes pages).",
)
def get_cosium_invoice_totals(
    type_filter: str | None = Query(None),
    settled: bool | None = Query(None),
    search: str | None = Query(None, max_length=100),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> CosiumInvoiceTotals:
    return cosium_invoice_service.get_totals(
        db,
        tenant_id=tenant_ctx.tenant_id,
        type_filter=type_filter,
        settled=settled,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )
