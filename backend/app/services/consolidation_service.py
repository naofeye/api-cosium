"""Multi-source consolidation engine for PEC preparation.

Aggregates data from Cosium client, prescriptions, devis, client mutuelles,
and document extractions to produce a single consolidated client profile.

Priority rules per domain:
- Identity fields: Cosium client is PRIMARY, OCR attestation is alternative
- Optical fields: Cosium prescription is PRIMARY, OCR ordonnance is alternative
- Mutuelle fields: OCR attestation is PRIMARY, Cosium TPP confirms
- Financial fields: Devis is PRIMARY (always)
"""

import json
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.domain.schemas.consolidation import (
    ConsolidatedClientProfile,
    ConsolidatedField,
    FieldStatus,
)
from app.models.client import Customer
from app.models.client_mutuelle import ClientMutuelle
from app.models.cosium_data import CosiumPrescription
from app.models.devis import Devis, DevisLigne
from app.models.document_extraction import DocumentExtraction

logger = get_logger("consolidation_service")

# Fields required for a complete PEC submission
PEC_REQUIRED_FIELDS = [
    "nom",
    "prenom",
    "numero_secu",
    "mutuelle_nom",
    "mutuelle_numero_adherent",
    "date_ordonnance",
    "sphere_od",
    "sphere_og",
    "montant_ttc",
    "part_secu",
    "part_mutuelle",
    "reste_a_charge",
]

# Tolerances for conflict detection
TOLERANCE_SPHERE = 0.25  # Dioptres
TOLERANCE_CYLINDER = 0.25  # Dioptres
TOLERANCE_AXIS = 5  # Degrees
TOLERANCE_ADDITION = 0.25  # Dioptres
TOLERANCE_AMOUNT = 1.00  # EUR


def _make_field(
    value: object,
    source: str,
    source_label: str,
    confidence: float = 1.0,
    status: FieldStatus = FieldStatus.EXTRACTED,
    alternatives: list[dict] | None = None,
    last_updated: datetime | None = None,
) -> ConsolidatedField:
    return ConsolidatedField(
        value=value,
        source=source,
        source_label=source_label,
        confidence=confidence,
        status=status,
        alternatives=alternatives,
        last_updated=last_updated or datetime.now(UTC),
    )


def _make_missing_field() -> ConsolidatedField:
    """Create a field marked as MISSING."""
    return _make_field(
        value=None,
        source="",
        source_label="",
        confidence=0.0,
        status=FieldStatus.MISSING,
    )


def _normalize_date(value: object) -> date | None:
    """Try to parse a date from various formats for comparison."""
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    return None


def _values_equal(a: object, b: object) -> bool:
    """Compare two values, normalizing dates if both look like dates."""
    if a == b:
        return True
    # Try date normalization
    da = _normalize_date(a)
    db = _normalize_date(b)
    if da is not None and db is not None:
        return da == db
    return False


def _resolve_field(
    primary_value: object,
    primary_source: str,
    primary_label: str,
    primary_confidence: float,
    secondary_value: object | None = None,
    secondary_source: str = "",
    secondary_label: str = "",
    secondary_confidence: float = 0.0,
    tolerance: float | None = None,
) -> ConsolidatedField:
    """Resolve a field from two sources, detecting conflicts.

    The primary source is used unless absent. If the secondary source
    provides a different value, a CONFLICT status is set (unless within
    tolerance for numeric fields). Date values are normalized before
    comparison to avoid false conflicts from format differences.
    """
    if primary_value is not None:
        field = _make_field(
            primary_value, primary_source, primary_label,
            primary_confidence, FieldStatus.EXTRACTED,
        )
        if secondary_value is not None and not _values_equal(primary_value, secondary_value):
            if tolerance is not None:
                try:
                    diff = abs(float(primary_value) - float(secondary_value))
                    if diff <= tolerance:
                        field.status = FieldStatus.EXTRACTED
                    else:
                        field.status = FieldStatus.CONFLICT
                        field.alternatives = [
                            {"value": secondary_value, "source": secondary_source, "confidence": secondary_confidence}
                        ]
                except (ValueError, TypeError):
                    field.status = FieldStatus.CONFLICT
                    field.alternatives = [
                        {"value": secondary_value, "source": secondary_source, "confidence": secondary_confidence}
                    ]
            else:
                field.status = FieldStatus.CONFLICT
                field.alternatives = [
                    {"value": secondary_value, "source": secondary_source, "confidence": secondary_confidence}
                ]
        return field
    elif secondary_value is not None:
        return _make_field(
            secondary_value, secondary_source, secondary_label,
            secondary_confidence, FieldStatus.DEDUCED,
        )
    else:
        return _make_missing_field()



def _load_cosium_client(
    db: Session, tenant_id: int, customer_id: int
) -> Customer | None:
    return db.scalars(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.tenant_id == tenant_id,
        )
    ).first()


def _load_latest_prescription(
    db: Session, tenant_id: int, customer_id: int
) -> CosiumPrescription | None:
    return db.scalars(
        select(CosiumPrescription)
        .where(
            CosiumPrescription.customer_id == customer_id,
            CosiumPrescription.tenant_id == tenant_id,
        )
        .order_by(CosiumPrescription.file_date.desc().nullslast(), CosiumPrescription.id.desc())
        .limit(1)
    ).first()


def _load_devis(
    db: Session, tenant_id: int, customer_id: int, devis_id: int | None
) -> Devis | None:
    if devis_id:
        return db.scalars(
            select(Devis).where(
                Devis.id == devis_id,
                Devis.tenant_id == tenant_id,
            )
        ).first()
    # Find latest devis for any case of this customer
    from app.models.case import Case

    return db.scalars(
        select(Devis)
        .join(Case, Case.id == Devis.case_id)
        .where(
            Case.customer_id == customer_id,
            Devis.tenant_id == tenant_id,
        )
        .order_by(Devis.created_at.desc())
        .limit(1)
    ).first()


def _load_devis_lignes(
    db: Session, tenant_id: int, devis_id: int
) -> list[DevisLigne]:
    return list(
        db.scalars(
            select(DevisLigne).where(
                DevisLigne.devis_id == devis_id,
                DevisLigne.tenant_id == tenant_id,
            )
        ).all()
    )


def _load_client_mutuelles(
    db: Session, tenant_id: int, customer_id: int
) -> list[ClientMutuelle]:
    return list(
        db.scalars(
            select(ClientMutuelle).where(
                ClientMutuelle.customer_id == customer_id,
                ClientMutuelle.tenant_id == tenant_id,
                ClientMutuelle.active.is_(True),
            )
            .order_by(ClientMutuelle.confidence.desc())
        ).all()
    )


def _load_document_extractions(
    db: Session, tenant_id: int, customer_id: int
) -> list[DocumentExtraction]:
    """Load document extractions linked to this customer's documents."""
    from app.models.case import Case
    from app.models.document import Document

    return list(
        db.scalars(
            select(DocumentExtraction)
            .join(Document, Document.id == DocumentExtraction.document_id)
            .join(Case, Case.id == Document.case_id)
            .where(
                Case.customer_id == customer_id,
                DocumentExtraction.tenant_id == tenant_id,
                DocumentExtraction.structured_data.isnot(None),
            )
            .order_by(DocumentExtraction.created_at.desc())
        ).all()
    )



def _parse_structured_data(extraction: DocumentExtraction) -> dict | None:
    """Parse JSON structured_data from a DocumentExtraction."""
    if not extraction.structured_data:
        return None
    try:
        return json.loads(extraction.structured_data)
    except (json.JSONDecodeError, TypeError):
        return None


def _calculate_completude(profile: ConsolidatedClientProfile) -> float:
    """Calculate completude score (0-100) based on required fields.

    A field counts as filled only if it is a ConsolidatedField with a non-None value.
    """
    filled = 0
    for field_name in PEC_REQUIRED_FIELDS:
        field = getattr(profile, field_name, None)
        if field is not None and isinstance(field, ConsolidatedField) and field.value is not None:
            filled += 1
    total = len(PEC_REQUIRED_FIELDS)
    return round((filled / total) * 100, 1) if total > 0 else 0.0


def _collect_ocr_data(
    extractions: list[DocumentExtraction],
) -> dict[str, tuple[dict, str, str, float]]:
    """Collect the best OCR data per document type.

    Returns a dict keyed by doc_type with (parsed_data, source_id, source_label, confidence).
    Only the first (most recent) extraction per type is kept.
    """
    result: dict[str, tuple[dict, str, str, float]] = {}
    for extraction in extractions:
        doc_type = extraction.document_type or "unknown"
        if doc_type in result:
            continue  # Keep only the most recent per type
        data = _parse_structured_data(extraction)
        if not data:
            continue
        src = f"document_ocr_{extraction.id}"
        src_label = f"Document OCR ({doc_type})"
        confidence = extraction.ocr_confidence or 0.7
        result[doc_type] = (data, src, src_label, confidence)
    return result


def _consolidate_identity(
    profile: ConsolidatedClientProfile,
    customer: Customer | None,
    ocr_map: dict[str, tuple[dict, str, str, float]],
) -> None:
    """Consolidate identity fields. Cosium client is PRIMARY."""
    ocr_att = ocr_map.get("attestation_mutuelle")
    ocr_att_data = ocr_att[0] if ocr_att else {}
    ocr_src = ocr_att[1] if ocr_att else ""
    ocr_label = ocr_att[2] if ocr_att else ""
    ocr_conf = ocr_att[3] if ocr_att else 0.0

    now = (customer.updated_at or customer.created_at) if customer else None

    profile.nom = _resolve_field(
        customer.last_name if customer else None, "cosium_client", "Cosium", 1.0,
        ocr_att_data.get("nom"), ocr_src, ocr_label, ocr_conf,
    )
    if profile.nom.status == FieldStatus.MISSING:
        profile.nom = None

    profile.prenom = _resolve_field(
        customer.first_name if customer else None, "cosium_client", "Cosium", 1.0,
        ocr_att_data.get("prenom"), ocr_src, ocr_label, ocr_conf,
    )
    if profile.prenom.status == FieldStatus.MISSING:
        profile.prenom = None

    if customer and customer.birth_date:
        profile.date_naissance = _make_field(
            str(customer.birth_date), "cosium_client", "Cosium", 1.0,
            last_updated=now,
        )

    profile.numero_secu = _resolve_field(
        customer.social_security_number if customer else None, "cosium_client", "Cosium", 1.0,
        ocr_att_data.get("numero_secu"), ocr_src, ocr_label, ocr_conf,
    )
    if profile.numero_secu.status == FieldStatus.MISSING:
        profile.numero_secu = None


def _consolidate_optical(
    profile: ConsolidatedClientProfile,
    prescription: CosiumPrescription | None,
    ocr_map: dict[str, tuple[dict, str, str, float]],
) -> None:
    """Consolidate optical fields. Cosium prescription is PRIMARY, OCR ordonnance is alternative."""
    p_src = ""
    p_label = ""
    p_conf = 0.95
    if prescription:
        p_src = f"cosium_prescription_{prescription.id}"
        p_label = "Ordonnance Cosium"
        if prescription.prescription_date:
            p_label = f"Ordonnance du {prescription.prescription_date}"

    ocr_ord = ocr_map.get("ordonnance")
    ocr_data: dict = {}
    ocr_src = ""
    ocr_label = ""
    ocr_conf = 0.0
    if ocr_ord:
        ocr_data, ocr_src, ocr_label, ocr_conf = ocr_ord
    od_data = ocr_data.get("od", {}) if isinstance(ocr_data.get("od"), dict) else {}
    og_data = ocr_data.get("og", {}) if isinstance(ocr_data.get("og"), dict) else {}

    def _ocr_val(flat_key: str, nested_dict: dict, nested_keys: list[str]) -> object:
        val = ocr_data.get(flat_key)
        if val is not None:
            return val
        for k in nested_keys:
            val = nested_dict.get(k)
            if val is not None:
                return val
        return None

    # Sphere OD/OG
    profile.sphere_od = _resolve_field(
        prescription.sphere_right if prescription and prescription.sphere_right is not None else None,
        p_src, p_label, p_conf,
        _ocr_val("sphere_od", od_data, ["sphere"]), ocr_src, ocr_label, ocr_conf,
        tolerance=TOLERANCE_SPHERE,
    )
    if profile.sphere_od.status == FieldStatus.MISSING:
        profile.sphere_od = None

    profile.sphere_og = _resolve_field(
        prescription.sphere_left if prescription and prescription.sphere_left is not None else None,
        p_src, p_label, p_conf,
        _ocr_val("sphere_og", og_data, ["sphere"]), ocr_src, ocr_label, ocr_conf,
        tolerance=TOLERANCE_SPHERE,
    )
    if profile.sphere_og.status == FieldStatus.MISSING:
        profile.sphere_og = None

    # Cylinder OD/OG
    profile.cylinder_od = _resolve_field(
        prescription.cylinder_right if prescription and prescription.cylinder_right is not None else None,
        p_src, p_label, p_conf,
        _ocr_val("cylinder_od", od_data, ["cylindre", "cylinder"]), ocr_src, ocr_label, ocr_conf,
        tolerance=TOLERANCE_CYLINDER,
    )
    if profile.cylinder_od.status == FieldStatus.MISSING:
        profile.cylinder_od = None

    profile.cylinder_og = _resolve_field(
        prescription.cylinder_left if prescription and prescription.cylinder_left is not None else None,
        p_src, p_label, p_conf,
        _ocr_val("cylinder_og", og_data, ["cylindre", "cylinder"]), ocr_src, ocr_label, ocr_conf,
        tolerance=TOLERANCE_CYLINDER,
    )
    if profile.cylinder_og.status == FieldStatus.MISSING:
        profile.cylinder_og = None

    # Axis OD/OG
    profile.axis_od = _resolve_field(
        prescription.axis_right if prescription and prescription.axis_right is not None else None,
        p_src, p_label, p_conf,
        _ocr_val("axis_od", od_data, ["axe", "axis"]), ocr_src, ocr_label, ocr_conf,
        tolerance=TOLERANCE_AXIS,
    )
    if profile.axis_od.status == FieldStatus.MISSING:
        profile.axis_od = None

    profile.axis_og = _resolve_field(
        prescription.axis_left if prescription and prescription.axis_left is not None else None,
        p_src, p_label, p_conf,
        _ocr_val("axis_og", og_data, ["axe", "axis"]), ocr_src, ocr_label, ocr_conf,
        tolerance=TOLERANCE_AXIS,
    )
    if profile.axis_og.status == FieldStatus.MISSING:
        profile.axis_og = None

    # Addition OD/OG
    profile.addition_od = _resolve_field(
        prescription.addition_right if prescription and prescription.addition_right is not None else None,
        p_src, p_label, p_conf,
        _ocr_val("addition_od", od_data, ["addition"]), ocr_src, ocr_label, ocr_conf,
        tolerance=TOLERANCE_ADDITION,
    )
    if profile.addition_od.status == FieldStatus.MISSING:
        profile.addition_od = None

    profile.addition_og = _resolve_field(
        prescription.addition_left if prescription and prescription.addition_left is not None else None,
        p_src, p_label, p_conf,
        _ocr_val("addition_og", og_data, ["addition"]), ocr_src, ocr_label, ocr_conf,
        tolerance=TOLERANCE_ADDITION,
    )
    if profile.addition_og.status == FieldStatus.MISSING:
        profile.addition_og = None

    # Ecart pupillaire (OCR only typically)
    ep_ocr = ocr_data.get("ecart_pupillaire") if ocr_data else None
    if ep_ocr is not None:
        profile.ecart_pupillaire = _make_field(ep_ocr, ocr_src, ocr_label, ocr_conf, FieldStatus.DEDUCED)

    # Prescripteur
    profile.prescripteur = _resolve_field(
        prescription.prescriber_name if prescription and prescription.prescriber_name else None,
        p_src, p_label, p_conf,
        ocr_data.get("prescripteur"), ocr_src, ocr_label, ocr_conf,
    )
    if profile.prescripteur.status == FieldStatus.MISSING:
        profile.prescripteur = None

    # Date ordonnance
    profile.date_ordonnance = _resolve_field(
        prescription.prescription_date if prescription and prescription.prescription_date else None,
        p_src, p_label, p_conf,
        ocr_data.get("date_ordonnance"), ocr_src, ocr_label, ocr_conf,
    )
    if profile.date_ordonnance.status == FieldStatus.MISSING:
        profile.date_ordonnance = None


def _consolidate_mutuelle(
    profile: ConsolidatedClientProfile,
    mutuelles: list[ClientMutuelle],
    ocr_map: dict[str, tuple[dict, str, str, float]],
) -> None:
    """Consolidate mutuelle fields. OCR attestation is PRIMARY (most detail), Cosium TPP confirms."""
    ocr_att = ocr_map.get("attestation_mutuelle")
    ocr_data = ocr_att[0] if ocr_att else {}
    ocr_src = ocr_att[1] if ocr_att else ""
    ocr_label = ocr_att[2] if ocr_att else ""
    ocr_conf = ocr_att[3] if ocr_att else 0.0

    best = mutuelles[0] if mutuelles else None
    m_src = f"mutuelle_{best.source}" if best else ""
    m_label = f"Mutuelle ({best.source})" if best else ""
    m_conf = best.confidence if best else 0.0

    # For mutuelle, OCR attestation is PRIMARY
    profile.mutuelle_nom = _resolve_field(
        ocr_data.get("mutuelle_nom"), ocr_src, ocr_label, ocr_conf,
        best.mutuelle_name if best else None, m_src, m_label, m_conf,
    )
    if profile.mutuelle_nom.status == FieldStatus.MISSING:
        profile.mutuelle_nom = None

    profile.mutuelle_numero_adherent = _resolve_field(
        ocr_data.get("numero_adherent"), ocr_src, ocr_label, ocr_conf,
        best.numero_adherent if best else None, m_src, m_label, m_conf,
    )
    if profile.mutuelle_numero_adherent.status == FieldStatus.MISSING:
        profile.mutuelle_numero_adherent = None

    if ocr_data.get("code_organisme"):
        profile.mutuelle_code_organisme = _make_field(
            ocr_data["code_organisme"], ocr_src, ocr_label, ocr_conf, FieldStatus.EXTRACTED,
        )
    elif best and getattr(best, "code_organisme", None):
        profile.mutuelle_code_organisme = _make_field(
            best.code_organisme, m_src, m_label, m_conf, FieldStatus.DEDUCED,
        )

    # Type beneficiaire
    if best and best.type_beneficiaire:
        profile.type_beneficiaire = _make_field(
            best.type_beneficiaire, m_src, m_label, m_conf, FieldStatus.EXTRACTED,
        )

    # Date fin droits
    date_fin_ocr = ocr_data.get("date_fin_droits")
    date_fin_mut = str(best.date_fin) if best and best.date_fin else None
    profile.date_fin_droits = _resolve_field(
        date_fin_ocr, ocr_src, ocr_label, ocr_conf,
        date_fin_mut, m_src, m_label, m_conf,
    )
    if profile.date_fin_droits.status == FieldStatus.MISSING:
        profile.date_fin_droits = None


def _consolidate_financial(
    profile: ConsolidatedClientProfile,
    devis: Devis | None,
    devis_lignes: list[DevisLigne],
    ocr_map: dict[str, tuple[dict, str, str, float]],
) -> None:
    """Consolidate financial fields. Devis is ALWAYS the PRIMARY source."""
    d_src = ""
    d_label = ""
    if devis:
        d_src = f"devis_{devis.id}"
        d_label = f"Devis {devis.numero}"

    ocr_devis = ocr_map.get("devis")
    ocr_data = ocr_devis[0] if ocr_devis else {}
    ocr_src = ocr_devis[1] if ocr_devis else ""
    ocr_label = ocr_devis[2] if ocr_devis else ""
    ocr_conf = ocr_devis[3] if ocr_devis else 0.0

    # montant_ttc
    profile.montant_ttc = _resolve_field(
        float(devis.montant_ttc) if devis else None, d_src, d_label, 1.0,
        ocr_data.get("montant_ttc"), ocr_src, ocr_label, ocr_conf,
        tolerance=TOLERANCE_AMOUNT,
    )
    if profile.montant_ttc.status == FieldStatus.MISSING:
        profile.montant_ttc = None

    # part_secu
    profile.part_secu = _resolve_field(
        float(devis.part_secu) if devis else None, d_src, d_label, 1.0,
        ocr_data.get("part_secu"), ocr_src, ocr_label, ocr_conf,
        tolerance=TOLERANCE_AMOUNT,
    )
    if profile.part_secu.status == FieldStatus.MISSING:
        profile.part_secu = None

    # part_mutuelle
    profile.part_mutuelle = _resolve_field(
        float(devis.part_mutuelle) if devis else None, d_src, d_label, 1.0,
        ocr_data.get("part_mutuelle"), ocr_src, ocr_label, ocr_conf,
        tolerance=TOLERANCE_AMOUNT,
    )
    if profile.part_mutuelle.status == FieldStatus.MISSING:
        profile.part_mutuelle = None

    # reste_a_charge
    profile.reste_a_charge = _resolve_field(
        float(devis.reste_a_charge) if devis else None, d_src, d_label, 1.0,
        ocr_data.get("reste_a_charge"), ocr_src, ocr_label, ocr_conf,
        tolerance=TOLERANCE_AMOUNT,
    )
    if profile.reste_a_charge.status == FieldStatus.MISSING:
        profile.reste_a_charge = None

    # Equipment from devis lignes
    if devis and devis_lignes:
        for ligne in devis_lignes:
            designation = ligne.designation.lower()
            if "monture" in designation or "cadre" in designation:
                profile.monture = _make_field(
                    ligne.designation, d_src, d_label, 1.0, FieldStatus.EXTRACTED,
                )
            else:
                profile.verres.append(
                    _make_field(ligne.designation, d_src, d_label, 1.0, FieldStatus.EXTRACTED)
                )


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
    customer = _load_cosium_client(db, tenant_id, customer_id)
    if customer:
        sources_used.append("cosium_client")

    prescription = _load_latest_prescription(db, tenant_id, customer_id)
    if prescription:
        sources_used.append(f"cosium_prescription_{prescription.id}")

    devis = _load_devis(db, tenant_id, customer_id, devis_id)
    devis_lignes: list[DevisLigne] = []
    if devis:
        sources_used.append(f"devis_{devis.id}")
        devis_lignes = _load_devis_lignes(db, tenant_id, devis.id)

    mutuelles = _load_client_mutuelles(db, tenant_id, customer_id)
    if mutuelles:
        src = f"mutuelle_{mutuelles[0].source}"
        if src not in sources_used:
            sources_used.append(src)

    extractions = _load_document_extractions(db, tenant_id, customer_id)
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
