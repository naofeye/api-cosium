from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.domain.schemas.audit import CompletenessItem, CompletenessResponse
from app.models import Case, Document, DocumentType


def get_completeness(db: Session, tenant_id: int, case_id: int) -> CompletenessResponse:
    case = db.get(Case, case_id)
    if not case or case.tenant_id != tenant_id:
        raise NotFoundError("case", case_id)

    doc_types = db.scalars(select(DocumentType)).all()
    docs = db.scalars(select(Document).where(Document.case_id == case_id)).all()
    present_types = {d.type for d in docs}

    items: list[CompletenessItem] = []
    for dt in doc_types:
        items.append(
            CompletenessItem(
                code=dt.code,
                label=dt.label,
                category=dt.category,
                is_required=dt.is_required,
                present=dt.code in present_types,
            )
        )

    required = [i for i in items if i.is_required]
    present_required = [i for i in required if i.present]

    return CompletenessResponse(
        case_id=case_id,
        total_required=len(required),
        total_present=len(present_required),
        total_missing=len(required) - len(present_required),
        items=items,
    )
