from fastapi import APIRouter, Depends, File, Header, Query, UploadFile
from sqlalchemy.orm import Session

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


@router.post("/paiements", response_model=PaymentResponse, status_code=201)
def create_payment(
    payload: PaymentCreate,
    x_idempotency_key: str | None = Header(None),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> PaymentResponse:
    return banking_service.create_payment(
        db,
        tenant_id=tenant_ctx.tenant_id,
        payload=payload,
        user_id=tenant_ctx.user_id,
        idempotency_key=x_idempotency_key,
    )


@router.post("/banking/import-statement", response_model=ImportStatementResult)
async def import_statement(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> ImportStatementResult:
    count = banking_service.import_statement(db, tenant_id=tenant_ctx.tenant_id, file=file, user_id=tenant_ctx.user_id)
    return ImportStatementResult(imported=count)


@router.post("/banking/reconcile", response_model=ReconcileResult)
def auto_reconcile(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> ReconcileResult:
    return banking_service.auto_reconcile(db, tenant_id=tenant_ctx.tenant_id, user_id=tenant_ctx.user_id)


@router.get("/banking/unmatched", response_model=list[BankTransactionResponse])
def get_unmatched(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[BankTransactionResponse]:
    return banking_service.get_unmatched(db, tenant_id=tenant_ctx.tenant_id)


@router.post("/banking/match", response_model=BankTransactionResponse)
def manual_match(
    payload: ReconcileRequest,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> BankTransactionResponse:
    return banking_service.manual_match(
        db,
        tenant_id=tenant_ctx.tenant_id,
        transaction_id=payload.transaction_id,
        payment_id=payload.payment_id,
        user_id=tenant_ctx.user_id,
    )


@router.get("/banking/unreconciled-payments", response_model=list[PaymentResponse])
def get_unreconciled_payments(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[PaymentResponse]:
    return banking_service.get_unreconciled_payments(db, tenant_id=tenant_ctx.tenant_id)


@router.get("/banking/transactions", response_model=BankTransactionListResponse)
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
