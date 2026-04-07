"""Service for OCAM operators."""

import json

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.domain.schemas.ocam_operator import OcamOperatorCreate, OcamOperatorResponse
from app.repositories import ocam_operator_repo

logger = get_logger("ocam_operator_service")


def _to_response(op: object) -> OcamOperatorResponse:
    """Convert ORM to response, deserializing JSON fields."""
    required_fields = None
    required_documents = None
    specific_rules = None

    if op.required_fields:
        try:
            required_fields = json.loads(op.required_fields)
        except (json.JSONDecodeError, TypeError):
            pass

    if op.required_documents:
        try:
            required_documents = json.loads(op.required_documents)
        except (json.JSONDecodeError, TypeError):
            pass

    if op.specific_rules:
        try:
            specific_rules = json.loads(op.specific_rules)
        except (json.JSONDecodeError, TypeError):
            pass

    return OcamOperatorResponse(
        id=op.id,
        tenant_id=op.tenant_id,
        name=op.name,
        code=op.code,
        portal_url=op.portal_url,
        required_fields=required_fields,
        required_documents=required_documents,
        specific_rules=specific_rules,
        active=op.active,
        created_at=op.created_at,
        updated_at=op.updated_at,
    )


def list_operators(
    db: Session,
    tenant_id: int,
    active_only: bool = True,
) -> list[OcamOperatorResponse]:
    """List all OCAM operators for a tenant."""
    operators = ocam_operator_repo.list_all(db, tenant_id, active_only=active_only)
    return [_to_response(op) for op in operators]


def create_operator(
    db: Session,
    tenant_id: int,
    payload: OcamOperatorCreate,
) -> OcamOperatorResponse:
    """Create a new OCAM operator."""
    op = ocam_operator_repo.create(
        db,
        tenant_id=tenant_id,
        name=payload.name,
        code=payload.code,
        portal_url=payload.portal_url,
        required_fields=json.dumps(payload.required_fields) if payload.required_fields else None,
        required_documents=json.dumps(payload.required_documents) if payload.required_documents else None,
        specific_rules=json.dumps(payload.specific_rules) if payload.specific_rules else None,
        active=payload.active,
    )
    logger.info("ocam_operator_created", operator_id=op.id, name=op.name)
    return _to_response(op)


def seed_default_operators(db: Session, tenant_id: int) -> int:
    """Seed default OCAM operators if none exist. Returns count created."""
    existing = ocam_operator_repo.list_all(db, tenant_id, active_only=False)
    if existing:
        return 0

    defaults = [
        {
            "name": "Almerys",
            "code": "ALMERYS",
            "portal_url": "https://www.almerys.com/espace-pro",
            "required_fields": ["nom", "prenom", "date_naissance", "numero_secu", "mutuelle_numero_adherent", "date_ordonnance", "montant_ttc"],
            "required_documents": ["ordonnance", "devis"],
            "specific_rules": {"max_amount": 10000, "requires_prescriber_rpps": False},
        },
        {
            "name": "SP Sante",
            "code": "SP_SANTE",
            "portal_url": "https://www.spsante.fr/professionnels",
            "required_fields": ["nom", "prenom", "date_naissance", "numero_secu", "mutuelle_numero_adherent", "mutuelle_code_organisme", "date_ordonnance", "montant_ttc", "part_mutuelle"],
            "required_documents": ["ordonnance", "devis", "attestation_mutuelle"],
            "specific_rules": {"max_amount": 8000, "requires_prescriber_rpps": True},
        },
        {
            "name": "Visilab",
            "code": "VISILAB",
            "portal_url": "https://pro.visilab.fr",
            "required_fields": ["nom", "prenom", "date_naissance", "numero_secu", "mutuelle_numero_adherent", "date_ordonnance", "montant_ttc"],
            "required_documents": ["ordonnance", "devis"],
            "specific_rules": {"max_amount": 5000},
        },
        {
            "name": "Direct Assurance",
            "code": "DIRECT_ASSURANCE",
            "portal_url": None,
            "required_fields": ["nom", "prenom", "date_naissance", "numero_secu", "mutuelle_numero_adherent", "date_ordonnance", "montant_ttc", "part_secu"],
            "required_documents": ["ordonnance", "devis", "attestation_mutuelle"],
            "specific_rules": {"max_amount": 6000, "requires_prescriber_rpps": True},
        },
    ]

    count = 0
    for d in defaults:
        ocam_operator_repo.create(
            db,
            tenant_id=tenant_id,
            name=d["name"],
            code=d["code"],
            portal_url=d["portal_url"],
            required_fields=json.dumps(d["required_fields"]),
            required_documents=json.dumps(d["required_documents"]),
            specific_rules=json.dumps(d["specific_rules"]),
        )
        count += 1

    logger.info("ocam_operators_seeded", tenant_id=tenant_id, count=count)
    return count
