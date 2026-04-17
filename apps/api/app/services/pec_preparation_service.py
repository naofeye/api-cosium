"""PEC Preparation service — CRUD, orchestration, and facade.

Heavy logic is delegated to:
- pec_consolidation_service: field correction, refresh, PEC submission
- pec_precontrol_service: pre-control checks, audit trail, document management

All functions are re-exported here for backward compatibility.
"""

import json
from datetime import UTC, datetime

from sqlalchemy import select as sa_select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.domain.schemas.consolidation import ConsolidatedClientProfile
from app.domain.schemas.pec_preparation import (
    PecPreparationResponse,
    PecPreparationSummary,
)
from app.models.client import Customer
from app.repositories import pec_audit_repo, pec_preparation_repo
from app.services import audit_service, consolidation_service
from app.services.incoherence_detector import detect_incoherences

# Re-exports for backward compatibility (API publique historique).
# Les fonctions metier vivent maintenant dans pec_consolidation_service
# et pec_precontrol_service ; ce module garde la facade stable.
from app.services.pec_consolidation_service import (
    _to_response,
    correct_field,
    refresh_preparation,
)
from app.services.pec_precontrol_service import (
    _auto_attach_documents,
    _validate_customer,
    add_document,
    create_pec_from_preparation,
    list_documents,
)

__all__ = [
    "list_all_preparations",
    "prepare_pec",
    "get_preparation",
    "list_preparations_for_customer",
    "validate_field",
    # Re-exports pec_consolidation_service
    "correct_field",
    "refresh_preparation",
    # Re-exports pec_precontrol_service
    "add_document",
    "create_pec_from_preparation",
    "list_documents",
]

logger = get_logger("pec_preparation_service")


def _serialize_profile(profile: ConsolidatedClientProfile) -> str:
    return profile.model_dump_json()


def list_all_preparations(
    db: Session,
    tenant_id: int,
    status: str | None = None,
    limit: int = 25,
    offset: int = 0,
) -> dict:
    """List all PEC preparations for a tenant with KPI counts."""
    preps = pec_preparation_repo.list_all(db, tenant_id, status=status, limit=limit, offset=offset)
    total = pec_preparation_repo.count_all(db, tenant_id, status=status)
    counts = pec_preparation_repo.count_by_status(db, tenant_id)

    customer_ids = list({p.customer_id for p in preps})
    customers_map: dict[int, str] = {}
    if customer_ids:
        rows = db.execute(
            sa_select(Customer.id, Customer.first_name, Customer.last_name).where(
                Customer.id.in_(customer_ids),
                Customer.tenant_id == tenant_id,
            )
        ).all()
        for row in rows:
            customers_map[row[0]] = f"{row[1] or ''} {row[2] or ''}".strip()

    items = [
        {
            "id": p.id,
            "customer_id": p.customer_id,
            "customer_name": customers_map.get(p.customer_id, "Inconnu"),
            "devis_id": p.devis_id,
            "status": p.status,
            "completude_score": p.completude_score,
            "errors_count": p.errors_count,
            "warnings_count": p.warnings_count,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in preps
    ]

    page = (offset // limit + 1) if limit else 1
    total_pages = (total + limit - 1) // limit if limit else 0
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": limit,
        "total_pages": total_pages,
        "counts": counts,
    }


def prepare_pec(
    db: Session,
    tenant_id: int,
    customer_id: int,
    devis_id: int | None = None,
    user_id: int = 0,
) -> PecPreparationResponse:
    """Prepare a full PEC assistance worksheet for a client."""
    _validate_customer(db, tenant_id, customer_id)

    profile = consolidation_service.consolidate_client_for_pec(
        db, tenant_id, customer_id, devis_id
    )

    alerts = detect_incoherences(profile)
    profile.alertes = alerts

    errors_count = sum(1 for a in alerts if a.severity == "error")
    warnings_count = sum(1 for a in alerts if a.severity == "warning")
    status = "prete" if errors_count == 0 else "en_preparation"
    score = profile.score_completude

    prep = pec_preparation_repo.create(
        db,
        tenant_id=tenant_id,
        customer_id=customer_id,
        devis_id=devis_id,
        consolidated_data=_serialize_profile(profile),
        status=status,
        completude_score=score,
        errors_count=errors_count,
        warnings_count=warnings_count,
        created_by=user_id if user_id else None,
    )

    docs_attached = _auto_attach_documents(
        db, tenant_id, customer_id, prep.id, devis_id
    )

    pec_audit_repo.create(
        db,
        tenant_id=tenant_id,
        preparation_id=prep.id,
        action="created",
        user_id=user_id or 0,
        new_value={"customer_id": customer_id, "score": score, "docs_attached": docs_attached},
    )

    if user_id:
        audit_service.log_action(
            db, tenant_id, user_id, "create", "pec_preparation", prep.id,
            new_value={"customer_id": customer_id, "score": score, "docs_attached": docs_attached},
        )

    db.commit()

    logger.info(
        "pec_preparation_created",
        tenant_id=tenant_id,
        preparation_id=prep.id,
        customer_id=customer_id,
        score=score,
        errors=errors_count,
        warnings=warnings_count,
        docs_attached=docs_attached,
    )

    return _to_response(prep)


def get_preparation(
    db: Session, tenant_id: int, preparation_id: int
) -> PecPreparationResponse:
    """Get a PEC preparation by ID."""
    prep = pec_preparation_repo.get_by_id(db, preparation_id, tenant_id)
    if not prep:
        raise NotFoundError("pec_preparation", preparation_id)
    return _to_response(prep)


def list_preparations_for_customer(
    db: Session, tenant_id: int, customer_id: int, limit: int = 25, offset: int = 0
) -> list[PecPreparationSummary]:
    """List all PEC preparations for a customer."""
    preps = pec_preparation_repo.list_by_customer(
        db, customer_id, tenant_id, limit=limit, offset=offset
    )
    return [
        PecPreparationSummary(
            id=p.id,
            customer_id=p.customer_id,
            devis_id=p.devis_id,
            status=p.status,
            completude_score=p.completude_score,
            errors_count=p.errors_count,
            warnings_count=p.warnings_count,
            created_at=p.created_at,
        )
        for p in preps
    ]


def validate_field(
    db: Session,
    tenant_id: int,
    preparation_id: int,
    field_name: str,
    validated_by: int,
) -> PecPreparationResponse:
    """Mark a field as validated by a user."""
    prep = pec_preparation_repo.get_by_id(db, preparation_id, tenant_id)
    if not prep:
        raise NotFoundError("pec_preparation", preparation_id)

    validations = json.loads(prep.user_validations) if prep.user_validations else {}
    validations[field_name] = {
        "validated": True,
        "validated_by": validated_by,
        "at": datetime.now(UTC).isoformat(),
    }

    pec_preparation_repo.update(
        db, prep, user_validations=json.dumps(validations)
    )

    pec_audit_repo.create(
        db,
        tenant_id=tenant_id,
        preparation_id=preparation_id,
        action="field_validated",
        user_id=validated_by,
        field_name=field_name,
    )

    db.commit()

    logger.info(
        "pec_field_validated",
        preparation_id=preparation_id,
        field=field_name,
        user_id=validated_by,
    )

    return _to_response(prep)
