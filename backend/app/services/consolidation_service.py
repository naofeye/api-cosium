"""Multi-source consolidation engine for PEC preparation.

Aggregates data from Cosium client, prescriptions, devis, client mutuelles,
and document extractions to produce a single consolidated client profile.

This module is the facade that delegates to domain-specific sub-modules:
- consolidation_helpers: shared utilities, constants, data loaders
- consolidation_identity: identity and mutuelle fields
- consolidation_optical: optical correction fields
- consolidation_financial: financial fields and equipment

Priority rules per domain:
- Identity fields: Cosium client is PRIMARY, OCR attestation is alternative
- Optical fields: Cosium prescription is PRIMARY, OCR ordonnance is alternative
- Mutuelle fields: OCR attestation is PRIMARY, Cosium TPP confirms
- Financial fields: Devis is PRIMARY (always)
"""

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.domain.schemas.consolidation import ConsolidatedClientProfile
from app.models.devis import DevisLigne

# Re-export public API from sub-modules for backward compatibility
from app.services.consolidation_helpers import (  # noqa: F401
    PEC_REQUIRED_FIELDS,
    TOLERANCE_ADDITION,
    TOLERANCE_AMOUNT,
    TOLERANCE_AXIS,
    TOLERANCE_CYLINDER,
    TOLERANCE_SPHERE,
    _calculate_completude,
    _collect_ocr_data,
    _make_field,
    _make_missing_field,
    _normalize_date,
    _resolve_field,
    _values_equal,
    load_client_mutuelles,
    load_cosium_client,
    load_devis,
    load_devis_lignes,
    load_document_extractions,
    load_latest_prescription,
)
from app.services.consolidation_financial import (  # noqa: F401
    consolidate_financial as _consolidate_financial,
)
from app.services.consolidation_identity import (  # noqa: F401
    consolidate_identity as _consolidate_identity,
    consolidate_mutuelle as _consolidate_mutuelle,
)
from app.services.consolidation_optical import (  # noqa: F401
    consolidate_optical as _consolidate_optical,
)

logger = get_logger("consolidation_service")

# Backward-compatible aliases for private loader functions
_load_cosium_client = load_cosium_client
_load_latest_prescription = load_latest_prescription
_load_devis = load_devis
_load_devis_lignes = load_devis_lignes
_load_client_mutuelles = load_client_mutuelles
_load_document_extractions = load_document_extractions


def consolidate_client_for_pec(
    db: Session,
    tenant_id: int,
    customer_id: int,
    devis_id: int | None = None,
) -> ConsolidatedClientProfile:
    """Consolidate ALL data sources for a client to produce a PEC-ready profile.

    Priority rules per domain:
    - Identity: Cosium client PRIMARY, OCR attestation alternative
    - Optical: Cosium prescription PRIMARY, OCR ordonnance alternative
    - Mutuelle: OCR attestation PRIMARY, Cosium TPP confirms
    - Financial: Devis PRIMARY (always)
    """
    sources_used: list[str] = []
    profile = ConsolidatedClientProfile()

    # 1. Load all data sources
    customer = load_cosium_client(db, tenant_id, customer_id)
    if customer:
        sources_used.append("cosium_client")

    prescription = load_latest_prescription(db, tenant_id, customer_id)
    if prescription:
        sources_used.append(f"cosium_prescription_{prescription.id}")

    devis = load_devis(db, tenant_id, customer_id, devis_id)
    devis_lignes: list[DevisLigne] = []
    if devis:
        sources_used.append(f"devis_{devis.id}")
        devis_lignes = load_devis_lignes(db, tenant_id, devis.id)

    mutuelles = load_client_mutuelles(db, tenant_id, customer_id)
    if mutuelles:
        src = f"mutuelle_{mutuelles[0].source}"
        if src not in sources_used:
            sources_used.append(src)

    extractions = load_document_extractions(db, tenant_id, customer_id)
    ocr_map = _collect_ocr_data(extractions)
    for _doc_type, (_, src, _, _) in ocr_map.items():
        sources_used.append(src)

    # 2. Consolidate per domain with proper priority
    _consolidate_identity(profile, customer, ocr_map)
    _consolidate_optical(profile, prescription, ocr_map)
    _consolidate_mutuelle(profile, mutuelles, ocr_map)
    _consolidate_financial(profile, devis, devis_lignes, ocr_map)

    # 3. Detect missing fields
    missing: list[str] = []
    for field_name in PEC_REQUIRED_FIELDS:
        val = getattr(profile, field_name, None)
        if val is None:
            missing.append(field_name)
    profile.champs_manquants = missing

    # 4. Deduplicate sources
    profile.sources_utilisees = list(dict.fromkeys(sources_used))

    # 5. Calculate completude score
    profile.score_completude = _calculate_completude(profile)

    logger.info(
        "consolidation_completed",
        tenant_id=tenant_id,
        customer_id=customer_id,
        score=profile.score_completude,
        missing_count=len(missing),
        sources_count=len(profile.sources_utilisees),
    )

    return profile
