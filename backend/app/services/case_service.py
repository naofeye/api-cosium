from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.domain.schemas.cases import CaseCreate, CaseDetail, CaseResponse
from app.domain.schemas.documents import DocumentResponse
from app.domain.schemas.payments import PaymentResponse
from app.models import Document, DocumentType
from app.repositories import case_repo, document_repo, payment_repo
from app.services import audit_service, event_service

logger = get_logger("case_service")


def list_cases(db: Session, tenant_id: int, limit: int = 25, offset: int = 0) -> list[CaseResponse]:
    rows = case_repo.list_cases(db, tenant_id, limit=limit, offset=offset)
    required_count = (
        db.scalar(select(func.count()).select_from(DocumentType).where(DocumentType.is_required.is_(True))) or 0
    )
    case_ids = [r["id"] for r in rows]
    present_counts: dict[int, int] = {}
    if case_ids and required_count > 0:
        required_codes = [
            code for (code,) in db.execute(select(DocumentType.code).where(DocumentType.is_required.is_(True))).all()
        ]
        present_rows = db.execute(
            select(Document.case_id, func.count(func.distinct(Document.type)))
            .where(Document.case_id.in_(case_ids), Document.type.in_(required_codes))
            .group_by(Document.case_id)
        ).all()
        for case_id, cnt in present_rows:
            present_counts[case_id] = cnt

    results = []
    for r in rows:
        present = present_counts.get(r["id"], 0)
        results.append(CaseResponse(**r, missing_docs=required_count - present))
    logger.info("cases_listed", tenant_id=tenant_id, count=len(results))
    return results


def get_case_detail(db: Session, tenant_id: int, case_id: int) -> CaseDetail:
    case = case_repo.get_case(db, case_id=case_id, tenant_id=tenant_id)
    if not case:
        logger.warning("case_not_found", tenant_id=tenant_id, case_id=case_id)
        raise NotFoundError("case", case_id)
    docs = document_repo.list_by_case(db, case_id=case_id, tenant_id=tenant_id)
    payments = payment_repo.list_by_case(db, case_id=case_id, tenant_id=tenant_id)
    logger.info("case_detail_loaded", tenant_id=tenant_id, case_id=case_id)
    return CaseDetail(
        **case,
        documents=[DocumentResponse.model_validate(d) for d in docs],
        payments=[PaymentResponse.model_validate(p) for p in payments],
    )


def create_case(db: Session, tenant_id: int, payload: CaseCreate, user_id: int) -> CaseResponse:
    case = case_repo.create_case(
        db,
        tenant_id=tenant_id,
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone=payload.phone,
        email=payload.email,
        source=payload.source,
    )
    if user_id:
        audit_service.log_action(
            db, user_id, "create", "case", case.id, new_value={"source": payload.source}, tenant_id=tenant_id
        )
    event_service.emit_event(db, tenant_id, "DossierCree", "case", case.id, user_id)
    logger.info("case_created", tenant_id=tenant_id, case_id=case.id)
    return CaseResponse(
        id=case.id,
        customer_name=f"{payload.first_name} {payload.last_name}",
        status=case.status,
        source=case.source,
        created_at=case.created_at,
    )
