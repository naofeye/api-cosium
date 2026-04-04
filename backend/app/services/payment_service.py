from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.domain.schemas.payments import PaymentResponse, PaymentSummary
from app.repositories import payment_repo

logger = get_logger("payment_service")


def get_payment_summary(db: Session, tenant_id: int, case_id: int) -> PaymentSummary:
    summary = payment_repo.get_summary(db, case_id=case_id, tenant_id=tenant_id)
    logger.info("payment_summary_loaded", tenant_id=tenant_id, case_id=case_id, total_due=summary["total_due"])
    return PaymentSummary(
        case_id=summary["case_id"],
        total_due=summary["total_due"],
        total_paid=summary["total_paid"],
        remaining=summary["remaining"],
        items=[PaymentResponse.model_validate(p) for p in summary["items"]],
    )
