"""PEC pre-control checks, audit trail, document management, and PEC submission.

Extracted from pec_preparation_service to keep each file under 300 lines.
"""

import json

from sqlalchemy import select as sa_select
from sqlalchemy.orm import Session

from app.core.constants import PEC_PRETE, PEC_SOUMISE
from app.core.exceptions import BusinessError, NotFoundError
from app.core.logging import get_logger, log_operation
from app.domain.schemas.pec_preparation import PecPreparationDocumentResponse
from app.models.client import Customer
from app.models.document_extraction import DocumentExtraction
from app.repositories import pec_audit_repo, pec_preparation_repo

logger = get_logger("pec_precontrol_service")


def _validate_customer(db: Session, tenant_id: int, customer_id: int) -> None:
    """Ensure the customer exists and belongs to the tenant."""
    customer = db.scalars(
        sa_select(Customer).where(
            Customer.id == customer_id,
            Customer.tenant_id == tenant_id,
        )
    ).first()
    if not customer:
        raise NotFoundError("customer", customer_id)


def _auto_attach_documents(
    db: Session,
    tenant_id: int,
    customer_id: int,
    preparation_id: int,
    devis_id: int | None = None,
) -> int:
    """Auto-attach the most recent documents by type for PEC."""
    from app.models.case import Case
    from app.models.document import Document

    role_map = {
        "ordonnance": "ordonnance",
        "attestation_mutuelle": "attestation_mutuelle",
        "devis": "devis",
    }
    attached_count = 0
    for doc_type, doc_role in role_map.items():
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
        if doc_type == "devis" and devis_id:
            from app.models.devis import Devis
            db.scalars(
                sa_select(Devis).where(Devis.id == devis_id, Devis.tenant_id == tenant_id)
            ).first()
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

    pec_audit_repo.create(
        db,
        tenant_id=tenant_id,
        preparation_id=preparation_id,
        action="document_attached",
        user_id=user_id,
        field_name=document_role,
        new_value={"document_id": document_id, "document_role": document_role},
    )
    db.commit()

    return PecPreparationDocumentResponse.model_validate(doc)


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

    return [
        {
            "id": e.id,
            "preparation_id": e.preparation_id,
            "action": e.action,
            "field_name": e.field_name,
            "old_value": json.loads(e.old_value) if e.old_value else None,
            "new_value": json.loads(e.new_value) if e.new_value else None,
            "source": e.source,
            "user_id": e.user_id,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in entries
    ]


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


@log_operation("create_pec_from_preparation")
def create_pec_from_preparation(
    db: Session, tenant_id: int, preparation_id: int, user_id: int,
) -> dict:
    """Create a PecRequest from a validated preparation.

    The preparation must be in 'prete' status (no blocking errors).
    """
    from app.domain.schemas.consolidation import ConsolidatedClientProfile
    from app.repositories import pec_repo
    from app.services import audit_service, event_service

    prep = pec_preparation_repo.get_by_id(db, preparation_id, tenant_id)
    if not prep:
        raise NotFoundError("pec_preparation", preparation_id)

    if prep.status not in (PEC_PRETE,):
        raise BusinessError(
            "PREPARATION_NOT_READY",
            f"La preparation est en statut '{prep.status}' — "
            "elle doit etre 'prete' pour soumettre une PEC",
        )

    # Validate required documents
    doc_roles = {d.document_role for d in (prep.documents or [])}
    if "ordonnance" not in doc_roles:
        raise BusinessError(
            "L'ordonnance est obligatoire pour soumettre une PEC optique",
            code="MISSING_ORDONNANCE",
        )
    if "devis" not in doc_roles:
        raise BusinessError(
            "Le devis signe est obligatoire pour soumettre une PEC",
            code="MISSING_DEVIS",
        )
    if "attestation_mutuelle" not in doc_roles:
        logger.warning("pec_submit_missing_attestation", preparation_id=preparation_id)

    if not prep.consolidated_data:
        raise BusinessError("Pas de donnees consolidees", code="NO_CONSOLIDATED_DATA")

    profile = ConsolidatedClientProfile.model_validate_json(prep.consolidated_data)

    montant = 0.0
    if profile.part_mutuelle and profile.part_mutuelle.value:
        try:
            montant = float(profile.part_mutuelle.value)
        except (ValueError, TypeError):
            pass

    # Find or create payer organization
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
                tenant_id=tenant_id, name=str(profile.mutuelle_nom.value),
                type="mutuelle",
                code=str(profile.mutuelle_code_organisme.value) if profile.mutuelle_code_organisme else "UNKNOWN",
            )
            db.add(org)
            db.flush()
    if not org:
        raise BusinessError("Impossible de creer la PEC : aucune mutuelle identifiee", code="NO_MUTUELLE")

    # Find a case for this customer
    from app.models.case import Case

    case = db.scalars(
        sa_select(Case).where(
            Case.customer_id == prep.customer_id,
            Case.tenant_id == tenant_id, Case.deleted_at.is_(None),
        ).order_by(Case.created_at.desc()).limit(1)
    ).first()
    if not case:
        raise BusinessError("Aucun dossier trouve pour ce client", code="NO_CASE")

    pec = pec_repo.create_pec(
        db, tenant_id=tenant_id, case_id=case.id,
        organization_id=org.id, facture_id=None, montant_demande=montant,
    )
    pec_repo.add_history(db, tenant_id, pec.id, "", PEC_SOUMISE,
                         "PEC creee depuis preparation assistee")
    pec_preparation_repo.update(db, prep, pec_request_id=pec.id, status=PEC_SOUMISE)

    pec_audit_repo.create(
        db, tenant_id=tenant_id, preparation_id=preparation_id,
        action="submitted", user_id=user_id,
        new_value={"pec_request_id": pec.id, "montant": montant},
    )
    if user_id:
        audit_service.log_action(
            db, tenant_id, user_id, "create", "pec_request", pec.id,
            new_value={"from_preparation": preparation_id, "montant": montant},
        )
        event_service.emit_event(db, tenant_id, "PECSoumise", "pec_request", pec.id, user_id)

    db.commit()
    logger.info("pec_created_from_preparation", preparation_id=preparation_id,
                pec_id=pec.id, montant=montant)
    return {
        "pec_request_id": pec.id, "preparation_id": preparation_id,
        "status": "soumise", "montant_demande": montant,
    }
