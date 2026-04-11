from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.payments import PaymentSummary
from app.services import payment_service

router = APIRouter(prefix="/api/v1", tags=["payments"])


@router.get(
    "/cases/{case_id}/payments",
    response_model=PaymentSummary,
    summary="Resume des paiements d'un dossier",
    description="Retourne le resume financier des paiements lies a un dossier.",
)
def get_case_payments(
    case_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> PaymentSummary:
    return payment_service.get_payment_summary(db, tenant_id=tenant_ctx.tenant_id, case_id=case_id)
