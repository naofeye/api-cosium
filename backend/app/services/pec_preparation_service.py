"""PEC Preparation service — orchestrates consolidation, incoherence detection, and the full PEC preparation workflow."""

import json
from datetime import UTC, datetime

from sqlalchemy import select as sa_select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError, NotFoundError
from app.core.logging import get_logger, log_operation
from app.domain.schemas.consolidation import ConsolidatedClientProfile
from app.domain.schemas.pec_preparation import (
    PecPreparationDocumentResponse,
    PecPreparationResponse,
    PecPreparationSummary,
)
from app.models.client import Customer
from app.models.document_extraction import DocumentExtraction
from app.repositories import pec_audit_repo, pec_preparation_repo, pec_repo
from app.services import audit_service, consolidation_service, event_service
from app.services.incoherence_detector import detect_incoherences

logger = get_logger("pec_preparation_service")


def _serialize_profile(profile: ConsolidatedClientProfile) -> str:
    """Serialize a consolidated profile to JSON string."""
    return profile.model_dump_json()


def _deserialize_profile(data: str) -> ConsolidatedClientProfile:
    """Deserialize a JSON string to consolidated profile."""
    return ConsolidatedClientProfile.model_validate_json(data)


def _profile_to_dict(data: str | None) -> dict | None:
    """Convert stored JSON string to dict for response."""
    if not data:
        return None
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return None


def _to_response(prep: object) -> PecPreparationResponse:
    """Convert a PecPreparation ORM object to a response schema."""
    return PecPreparationResponse(
        id=prep.id,
        tenant_id=prep.tenant_id,
        customer_id=prep.customer_id,
        devis_id=prep.devis_id,
        pec_request_id=prep.pec_request_id,
        consolidated_data=_profile_to_dict(prep.consolidated_data),
        status=prep.status,
        completude_score=prep.completude_score,
        errors_count=prep.errors_count,
        warnings_count=prep.warnings_count,
        user_validations=_profile_to_dict(prep.user_validations),
        user_corrections=_profile_to_dict(prep.user_corrections),
        created_at=prep.created_at,
        updated_at=prep.updated_at,
        created_by=prep.created_by,
    )


def _auto_attach_documents(
    db: Session,
    tenant_id: int,
    customer_id: int,
    preparation_id: int,
    devis_id: int | None = None,
) -> int:
    """Auto-attach the most recent documents by type for PEC.

    Finds the latest ordonnance, attestation_mutuelle, and devis extractions
    linked to the customer's cases, and attaches them to the preparation.
    Returns the number of documents attached.
    """
    from app.models.case import Case
    from app.models.document import Document

    # Map extraction document_type -> document_role for PEC
    role_map = {
        "ordonnance": "ordonnance",
        "attestation_mutuelle": "attestation_mutuelle",
        "devis": "devis",
    }

    attached_count = 0

    for doc_type, doc_role in role_map.items():
        # Build query for most recent extraction of this type
        stmt = (
            sa_select(DocumentExtraction)
            .join(Document, Document.id == DocumentExtraction.document_id)
            .join(Case, Case.id == Document.case_id)
            .where(
                Case.customer_id == customer_id,
                DocumentExtraction.tenant_id == tenant_id,
                DocumentExtraction.document_type == doc_type,
            )
        )

        # If devis_id specified and we're looking for devis, try to match
        if doc_type == "devis" and devis_id:
            from app.models.devis import Devis

            devis_obj = db.scalars(
                sa_select(Devis).where(
                    Devis.id == devis_id,
                    Devis.tenant_id == tenant_id,
                )
            ).first()
            if devis_obj:
                # Still get the most recent devis extraction for this customer
                pass

        stmt = stmt.order_by(DocumentExtraction.created_at.desc()).limit(1)
        extraction = db.scalars(stmt).first()

        if extraction:
            pec_preparation_repo.add_document(
                db,
                preparation_id=preparation_id,
                document_id=extraction.document_id,
                cosium_document_id=extraction.cosium_document_id,
                document_role=doc_role,
                extraction_id=extraction.id,
            )
            attached_count += 1
            logger.info(
                "pec_document_auto_attached",
                preparation_id=preparation_id,
                document_role=doc_role,
                extraction_id=extraction.id,
            )

    return attached_count


def _validate_customer(db: Session, tenant_id: int, customer_id: int) -> None:
    """Ensure the customer exists and belongs to the tenant."""
    from sqlalchemy import select

    customer = db.scalars(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.tenant_id == tenant_id,
        )
    ).first()
    if not customer:
        raise NotFoundError("customer", customer_id)


def list_all_preparations(
    db: Session,
    tenant_id: int,
    status: str | None = None,
    limit: int = 25,
    offset: int = 0,
) -> dict:
    """List all PEC preparations for a tenant with KPI counts."""
    from sqlalchemy import select as sa_select

    from app.models.client import Customer as CustomerModel

    preps = pec_preparation_repo.list_all(db, tenant_id, status=status, limit=limit, offset=offset)
    total = pec_preparation_repo.count_all(db, tenant_id, status=status)
    counts = pec_preparation_repo.count_by_status(db, tenant_id)

    # Collect customer IDs and fetch names
    customer_ids = list({p.customer_id for p in preps})
    customers_map: dict[int, str] = {}
    if customer_ids:
        rows = db.execute(
            sa_select(CustomerModel.id, CustomerModel.first_name, CustomerModel.last_name).where(
                CustomerModel.id.in_(customer_ids),
                CustomerModel.tenant_id == tenant_id,
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
    """Prepare a full PEC assistance worksheet for a client.

    1. Validate customer exists
    2. Run multi-source consolidation
    3. Detect incoherences
    4. Calculate completude score
    5. Create/update PecPreparation record
    6. Return the structured response
    """
    _validate_customer(db, tenant_id, customer_id)

    # Run consolidation
    profile = consolidation_service.consolidate_client_for_pec(
        db, tenant_id, customer_id, devis_id
    )

    # Run incoherence detection
    alerts = detect_incoherences(profile)
    profile.alertes = alerts

    # Count errors and warnings
    errors_count = sum(1 for a in alerts if a.severity == "error")
    warnings_count = sum(1 for a in alerts if a.severity == "warning")

    # Determine status
    status = "prete" if errors_count == 0 else "en_preparation"

    # Recalculate completude with alerts
    score = profile.score_completude

    # Persist
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

    # Auto-attach supporting documents from OCR extractions
    docs_attached = _auto_attach_documents(
        db, tenant_id, customer_id, prep.id, devis_id
    )

    # PEC audit trail: log creation
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

    # PEC audit trail: log field validation
    pec_audit_repo.create(
        db,
        tenant_id=tenant_id,
        preparation_id=preparation_id,
        action="field_validated",
        user_id=validated_by,
        field_name=field_name,
    )

    logger.info(
        "pec_field_validated",
        preparation_id=preparation_id,
        field=field_name,
        user_id=validated_by,
    )

    return _to_response(prep)


def correct_field(
    db: Session,
    tenant_id: int,
    preparation_id: int,
    field_name: str,
    new_value: object,
    corrected_by: int,
) -> PecPreparationResponse:
    """Correct a field value and recalculate alerts."""
    prep = pec_preparation_repo.get_by_id(db, preparation_id, tenant_id)
    if not prep:
        raise NotFoundError("pec_preparation", preparation_id)

    # Load current consolidated data
    if not prep.consolidated_data:
        raise BusinessError(
            "NO_CONSOLIDATED_DATA",
            "Pas de donnees consolidees — relancez la preparation",
        )

    profile = _deserialize_profile(prep.consolidated_data)

    # Record the correction
    corrections = json.loads(prep.user_corrections) if prep.user_corrections else {}
    original_field = getattr(profile, field_name, None)
    original_value = original_field.value if original_field else None
    corrections[field_name] = {
        "original": original_value,
        "corrected": new_value,
        "by": corrected_by,
        "at": datetime.now(UTC).isoformat(),
    }

    # Apply correction to profile
    if hasattr(profile, field_name):
        from app.domain.schemas.consolidation import ConsolidatedField, FieldStatus

        setattr(
            profile,
            field_name,
            ConsolidatedField(
                value=new_value,
                source="manual",
                source_label="Correction manuelle",
                confidence=1.0,
                status=FieldStatus.MANUAL,
                last_updated=datetime.now(UTC),
            ),
        )

    # Re-run incoherence detection
    alerts = detect_incoherences(profile)
    profile.alertes = alerts
    errors_count = sum(1 for a in alerts if a.severity == "error")
    warnings_count = sum(1 for a in alerts if a.severity == "warning")
    status = "prete" if errors_count == 0 else "en_preparation"

    # Recalculate completude
    from app.services.consolidation_service import _calculate_completude

    profile.score_completude = _calculate_completude(profile)

    pec_preparation_repo.update(
        db,
        prep,
        consolidated_data=_serialize_profile(profile),
        user_corrections=json.dumps(corrections),
        errors_count=errors_count,
        warnings_count=warnings_count,
        completude_score=profile.score_completude,
        status=status,
    )

    # PEC audit trail: log field correction
    pec_audit_repo.create(
        db,
        tenant_id=tenant_id,
        preparation_id=preparation_id,
        action="field_corrected",
        user_id=corrected_by,
        field_name=field_name,
        old_value=original_value,
        new_value=new_value,
        source="manual",
    )

    logger.info(
        "pec_field_corrected",
        preparation_id=preparation_id,
        field=field_name,
        user_id=corrected_by,
    )

    return _to_response(prep)


def refresh_preparation(
    db: Session,
    tenant_id: int,
    preparation_id: int,
) -> PecPreparationResponse:
    """Re-run consolidation and incoherence detection on an existing preparation."""
    prep = pec_preparation_repo.get_by_id(db, preparation_id, tenant_id)
    if not prep:
        raise NotFoundError("pec_preparation", preparation_id)

    # Re-run consolidation
    profile = consolidation_service.consolidate_client_for_pec(
        db, tenant_id, prep.customer_id, prep.devis_id
    )

    # Apply any existing user corrections
    if prep.user_corrections:
        corrections = json.loads(prep.user_corrections)
        from app.domain.schemas.consolidation import ConsolidatedField, FieldStatus

        for field_name, correction in corrections.items():
            if hasattr(profile, field_name):
                setattr(
                    profile,
                    field_name,
                    ConsolidatedField(
                        value=correction["corrected"],
                        source="manual",
                        source_label="Correction manuelle",
                        confidence=1.0,
                        status=FieldStatus.MANUAL,
                        last_updated=datetime.now(UTC),
                    ),
                )

    # Re-run incoherence detection
    alerts = detect_incoherences(profile)
    profile.alertes = alerts
    errors_count = sum(1 for a in alerts if a.severity == "error")
    warnings_count = sum(1 for a in alerts if a.severity == "warning")
    status = "prete" if errors_count == 0 else "en_preparation"

    from app.services.consolidation_service import _calculate_completude

    profile.score_completude = _calculate_completude(profile)

    pec_preparation_repo.update(
        db,
        prep,
        consolidated_data=_serialize_profile(profile),
        errors_count=errors_count,
        warnings_count=warnings_count,
        completude_score=profile.score_completude,
        status=status,
    )

    # PEC audit trail: log refresh
    pec_audit_repo.create(
        db,
        tenant_id=tenant_id,
        preparation_id=preparation_id,
        action="refreshed",
        user_id=0,
        new_value={"score": profile.score_completude, "errors": errors_count},
    )

    logger.info(
        "pec_preparation_refreshed",
        preparation_id=preparation_id,
        score=profile.score_completude,
    )

    return _to_response(prep)


@log_operation("create_pec_from_preparation")
def create_pec_from_preparation(
    db: Session,
    tenant_id: int,
    preparation_id: int,
    user_id: int,
) -> dict:
    """Create a PecRequest from a validated preparation.

    The preparation must be in 'prete' status (no blocking errors).
    """
    prep = pec_preparation_repo.get_by_id(db, preparation_id, tenant_id)
    if not prep:
        raise NotFoundError("pec_preparation", preparation_id)

    if prep.status not in ("prete",):
        raise BusinessError(
            "PREPARATION_NOT_READY",
            f"La preparation est en statut '{prep.status}' — "
            "elle doit etre 'prete' pour soumettre une PEC",
        )

    # FIX 3: Validate required documents before submission
    doc_roles = {d.document_role for d in (prep.documents or [])}
    if "ordonnance" not in doc_roles:
        raise BusinessError(
            "MISSING_ORDONNANCE",
            "L'ordonnance est obligatoire pour soumettre une PEC optique",
        )
    if "devis" not in doc_roles:
        raise BusinessError(
            "MISSING_DEVIS",
            "Le devis signe est obligatoire pour soumettre une PEC",
        )
    if "attestation_mutuelle" not in doc_roles:
        logger.warning(
            "pec_submit_missing_attestation",
            preparation_id=preparation_id,
        )

    if not prep.consolidated_data:
        raise BusinessError(
            "NO_CONSOLIDATED_DATA",
            "Pas de donnees consolidees",
        )

    profile = _deserialize_profile(prep.consolidated_data)

    # Determine montant from consolidated data
    montant = 0.0
    if profile.part_mutuelle and profile.part_mutuelle.value:
        try:
            montant = float(profile.part_mutuelle.value)
        except (ValueError, TypeError):
            pass

    # Find or create a payer organization from the mutuelle
    from sqlalchemy import select as sa_select

    from app.models.pec import PayerOrganization

    org = None
    if profile.mutuelle_nom:
        org = db.scalars(
            sa_select(PayerOrganization).where(
                PayerOrganization.tenant_id == tenant_id,
                PayerOrganization.name == profile.mutuelle_nom.value,
            )
        ).first()
        if not org:
            org = PayerOrganization(
                tenant_id=tenant_id,
                name=str(profile.mutuelle_nom.value),
                type="mutuelle",
                code=str(profile.mutuelle_code_organisme.value) if profile.mutuelle_code_organisme else "UNKNOWN",
            )
            db.add(org)
            db.flush()

    if not org:
        raise BusinessError(
            "NO_MUTUELLE",
            "Impossible de creer la PEC : aucune mutuelle identifiee",
        )

    # Find a case for this customer
    from app.models.case import Case

    case = db.scalars(
        sa_select(Case).where(
            Case.customer_id == prep.customer_id,
            Case.tenant_id == tenant_id,
            Case.deleted_at.is_(None),
        )
        .order_by(Case.created_at.desc())
        .limit(1)
    ).first()

    if not case:
        raise BusinessError(
            "NO_CASE",
            "Aucun dossier trouve pour ce client",
        )

    # Create the PEC request
    pec = pec_repo.create_pec(
        db,
        tenant_id=tenant_id,
        case_id=case.id,
        organization_id=org.id,
        facture_id=None,
        montant_demande=montant,
    )
    pec_repo.add_history(
        db, tenant_id, pec.id, "", "soumise", "PEC creee depuis preparation assistee"
    )

    # Link prep to pec
    pec_preparation_repo.update(
        db, prep, pec_request_id=pec.id, status="soumise"
    )

    # PEC audit trail: log submission
    pec_audit_repo.create(
        db,
        tenant_id=tenant_id,
        preparation_id=preparation_id,
        action="submitted",
        user_id=user_id,
        new_value={"pec_request_id": pec.id, "montant": montant},
    )

    if user_id:
        audit_service.log_action(
            db, tenant_id, user_id, "create", "pec_request", pec.id,
            new_value={"from_preparation": preparation_id, "montant": montant},
        )
        event_service.emit_event(
            db, tenant_id, "PECSoumise", "pec_request", pec.id, user_id
        )

    logger.info(
        "pec_created_from_preparation",
        preparation_id=preparation_id,
        pec_id=pec.id,
        montant=montant,
    )

    return {
        "pec_request_id": pec.id,
        "preparation_id": preparation_id,
        "status": "soumise",
        "montant_demande": montant,
    }


# --- Document management ---


def list_documents(
    db: Session, tenant_id: int, preparation_id: int
) -> list[PecPreparationDocumentResponse]:
    """List documents linked to a preparation."""
    prep = pec_preparation_repo.get_by_id(db, preparation_id, tenant_id)
    if not prep:
        raise NotFoundError("pec_preparation", preparation_id)
    docs = pec_preparation_repo.list_documents(db, preparation_id)
    return [PecPreparationDocumentResponse.model_validate(d) for d in docs]


def add_document(
    db: Session,
    tenant_id: int,
    preparation_id: int,
    document_id: int | None = None,
    cosium_document_id: int | None = None,
    document_role: str = "autre",
    extraction_id: int | None = None,
    user_id: int = 0,
) -> PecPreparationDocumentResponse:
    """Attach a document to a preparation."""
    prep = pec_preparation_repo.get_by_id(db, preparation_id, tenant_id)
    if not prep:
        raise NotFoundError("pec_preparation", preparation_id)
    doc = pec_preparation_repo.add_document(
        db,
        preparation_id=preparation_id,
        document_id=document_id,
        cosium_document_id=cosium_document_id,
        document_role=document_role,
        extraction_id=extraction_id,
    )

    # PEC audit trail: log document attachment
    pec_audit_repo.create(
        db,
        tenant_id=tenant_id,
        preparation_id=preparation_id,
        action="document_attached",
        user_id=user_id,
        field_name=document_role,
        new_value={"document_id": document_id, "document_role": document_role},
    )

    return PecPreparationDocumentResponse.model_validate(doc)


# --- Audit trail ---


def get_audit_trail(
    db: Session,
    tenant_id: int,
    preparation_id: int,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """Get structured audit trail for a PEC preparation."""
    prep = pec_preparation_repo.get_by_id(db, preparation_id, tenant_id)
    if not prep:
        raise NotFoundError("pec_preparation", preparation_id)

    entries = pec_audit_repo.list_by_preparation(
        db, preparation_id, tenant_id, limit=limit, offset=offset
    )

    import json as _json

    return [
        {
            "id": e.id,
            "preparation_id": e.preparation_id,
            "action": e.action,
            "field_name": e.field_name,
            "old_value": _json.loads(e.old_value) if e.old_value else None,
            "new_value": _json.loads(e.new_value) if e.new_value else None,
            "source": e.source,
            "user_id": e.user_id,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in entries
    ]


# --- Pre-control ---


def run_precontrol_for_preparation(
    db: Session,
    tenant_id: int,
    preparation_id: int,
) -> dict:
    """Run pre-submission control and return result as dict."""
    from app.services.pec_precontrol import run_precontrol

    prep = pec_preparation_repo.get_by_id(db, preparation_id, tenant_id)
    if not prep:
        raise NotFoundError("pec_preparation", preparation_id)

    result = run_precontrol(prep)
    return result.model_dump()
