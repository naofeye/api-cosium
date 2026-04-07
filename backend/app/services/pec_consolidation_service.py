"""PEC Consolidation — field correction, refresh, and PEC submission logic.

Extracted from pec_preparation_service to keep each file under 300 lines.
"""

import json
from datetime import UTC, datetime

from sqlalchemy import select as sa_select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError, NotFoundError
from app.core.logging import get_logger
from app.domain.schemas.consolidation import ConsolidatedClientProfile, ConsolidatedField, FieldStatus
from app.domain.schemas.pec_preparation import PecPreparationResponse
from app.repositories import pec_audit_repo, pec_preparation_repo
from app.services import consolidation_service
from app.services.incoherence_detector import detect_incoherences

logger = get_logger("pec_consolidation_service")


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
        ocam_operator_id=getattr(prep, "ocam_operator_id", None),
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


def correct_field(
    db: Session,
    tenant_id: int,
    preparation_id: int,
    field_name: str,
    new_value: object,
    corrected_by: int,
    reason: str | None = None,
) -> PecPreparationResponse:
    """Correct a field value and recalculate alerts."""
    prep = pec_preparation_repo.get_by_id(db, preparation_id, tenant_id)
    if not prep:
        raise NotFoundError("pec_preparation", preparation_id)

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
    correction_entry: dict = {
        "original": original_value,
        "corrected": new_value,
        "by": corrected_by,
        "at": datetime.now(UTC).isoformat(),
    }
    if reason:
        correction_entry["reason"] = reason
    corrections[field_name] = correction_entry

    # Apply correction to profile
    if hasattr(profile, field_name):
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

    # PEC audit trail
    audit_new_value = {"value": new_value}
    if reason:
        audit_new_value["reason"] = reason
    pec_audit_repo.create(
        db,
        tenant_id=tenant_id,
        preparation_id=preparation_id,
        action="field_corrected",
        user_id=corrected_by,
        field_name=field_name,
        old_value=original_value,
        new_value=audit_new_value,
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

    profile = consolidation_service.consolidate_client_for_pec(
        db, tenant_id, prep.customer_id, prep.devis_id
    )

    # Apply any existing user corrections
    if prep.user_corrections:
        corrections = json.loads(prep.user_corrections)
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


