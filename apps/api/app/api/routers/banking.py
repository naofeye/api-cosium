from fastapi import APIRouter, Depends, File, Header, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import require_tenant_role
from app.core.exceptions import ValidationError
from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.banking import (
    BankTransactionListResponse,
    BankTransactionResponse,
    ImportStatementResult,
    PaymentCreate,
    PaymentResponse,
    ReconcileRequest,
    ReconcileResult,
)
from app.services import banking_service

router = APIRouter(prefix="/api/v1", tags=["banking"])


@router.post(
    "/paiements",
    response_model=PaymentResponse,
    status_code=201,
    summary="Enregistrer un paiement",
    description="Enregistre un nouveau paiement avec controle d'idempotence.",
)
def create_payment(
    payload: PaymentCreate,
    x_idempotency_key: str | None = Header(None),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager", "operator")),
) -> PaymentResponse:
    return banking_service.create_payment(
        db,
        tenant_id=tenant_ctx.tenant_id,
        payload=payload,
        user_id=tenant_ctx.user_id,
        idempotency_key=x_idempotency_key,
    )


@router.post(
    "/banking/import-statement",
    response_model=ImportStatementResult,
    summary="Importer un releve bancaire",
    description="Importe un fichier de releve bancaire et cree les transactions.",
)
async def import_statement(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> ImportStatementResult:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise ValidationError("file", "Le fichier doit etre au format CSV.")
    imported, skipped = banking_service.import_statement(
        db, tenant_id=tenant_ctx.tenant_id, file=file, user_id=tenant_ctx.user_id
    )
    return ImportStatementResult(imported=imported, skipped=skipped)


@router.post(
    "/banking/reconcile",
    response_model=ReconcileResult,
    summary="Rapprochement automatique",
    description="Lance le rapprochement automatique entre transactions et paiements.",
)
def auto_reconcile(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> ReconcileResult:
    return banking_service.auto_reconcile(db, tenant_id=tenant_ctx.tenant_id, user_id=tenant_ctx.user_id)


@router.get(
    "/banking/unmatched",
    response_model=list[BankTransactionResponse],
    summary="Transactions non rapprochees",
    description="Retourne les transactions bancaires non encore rapprochees.",
)
def get_unmatched(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[BankTransactionResponse]:
    return banking_service.get_unmatched(db, tenant_id=tenant_ctx.tenant_id)


@router.post(
    "/banking/match",
    response_model=BankTransactionResponse,
    summary="Rapprochement manuel",
    description="Associe manuellement une transaction bancaire a un paiement.",
)
def manual_match(
    payload: ReconcileRequest,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> BankTransactionResponse:
    return banking_service.manual_match(
        db,
        tenant_id=tenant_ctx.tenant_id,
        transaction_id=payload.transaction_id,
        payment_id=payload.payment_id,
        user_id=tenant_ctx.user_id,
    )


@router.get(
    "/banking/unreconciled-payments",
    response_model=list[PaymentResponse],
    summary="Paiements non rapproches",
    description="Retourne les paiements non encore associes a une transaction bancaire.",
)
def get_unreconciled_payments(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[PaymentResponse]:
    return banking_service.get_unreconciled_payments(db, tenant_id=tenant_ctx.tenant_id)


@router.get(
    "/banking/transactions",
    response_model=BankTransactionListResponse,
    summary="Lister les transactions bancaires",
    description="Retourne la liste paginee des transactions bancaires avec filtre optionnel.",
)
def list_transactions(
    reconciled: bool | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> BankTransactionListResponse:
    return banking_service.list_transactions(
        db, tenant_id=tenant_ctx.tenant_id, reconciled=reconciled, limit=limit, offset=offset
    )
