"""Multi-source consolidation engine for PEC preparation.

Aggregates data from Cosium client, prescriptions, devis, client mutuelles,
and document extractions to produce a single consolidated client profile.
"""

import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.domain.schemas.consolidation import (
    ConsolidatedClientProfile,
    ConsolidatedField,
    ConsolidationAlert,
)
from app.models.client import Customer
from app.models.client_mutuelle import ClientMutuelle
from app.models.cosium_data import CosiumInvoice, CosiumPrescription
from app.models.devis import Devis, DevisLigne
from app.models.document_extraction import DocumentExtraction

logger = get_logger("consolidation_service")

# ---- Priority constants ----
# Higher number = higher priority
SOURCE_PRIORITY = {
    "manual": 1,
    "document_ocr": 2,
    "cosium_invoice": 3,
    "cosium_tpp": 3,
    "cosium_prescription": 4,
    "devis": 4,
    "cosium_client": 5,
}

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


def _make_field(
    value: object,
    source: str,
    source_label: str,
    confidence: float = 1.0,
    last_updated: datetime | None = None,
) -> ConsolidatedField:
    return ConsolidatedField(
        value=value,
        source=source,
        source_label=source_label,
        confidence=confidence,
        last_updated=last_updated or datetime.now(UTC),
    )


def _pick_best(
    candidates: list[ConsolidatedField],
) -> ConsolidatedField | None:
    """Pick the best field value based on source priority and confidence."""
    if not candidates:
        return None
    # Sort by priority (derived from source prefix) descending, then confidence descending
    def _priority(f: ConsolidatedField) -> tuple[int, float]:
        src_key = f.source.split("_")[0] + "_" + f.source.split("_")[1] if "_" in f.source else f.source
        # Map source string to priority
        for key in SOURCE_PRIORITY:
            if f.source.startswith(key) or f.source == key:
                return (SOURCE_PRIORITY[key], f.confidence)
        return (0, f.confidence)

    candidates.sort(key=_priority, reverse=True)
    return candidates[0]


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
    from app.models.document import Document
    from app.models.case import Case

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


def _load_cosium_invoices(
    db: Session, tenant_id: int, customer_id: int
) -> list[CosiumInvoice]:
    return list(
        db.scalars(
            select(CosiumInvoice).where(
                CosiumInvoice.customer_id == customer_id,
                CosiumInvoice.tenant_id == tenant_id,
            )
            .order_by(CosiumInvoice.invoice_date.desc().nullslast())
            .limit(5)
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
    """Calculate completude score (0-100) based on required fields."""
    filled = 0
    for field_name in PEC_REQUIRED_FIELDS:
        val = getattr(profile, field_name, None)
        if val is not None:
            filled += 1
    total = len(PEC_REQUIRED_FIELDS)
    return round((filled / total) * 100, 1) if total > 0 else 0.0


def consolidate_client_for_pec(
    db: Session,
    tenant_id: int,
    customer_id: int,
    devis_id: int | None = None,
) -> ConsolidatedClientProfile:
    """Consolidate ALL data sources for a client to produce a PEC-ready profile."""
    sources_used: list[str] = []
    profile = ConsolidatedClientProfile()

    # 1. Load Cosium client data
    customer = _load_cosium_client(db, tenant_id, customer_id)
    if customer:
        sources_used.append("cosium_client")
        now = customer.updated_at or customer.created_at
        profile.nom = _make_field(
            customer.last_name, "cosium_client", "Cosium", 1.0, now
        )
        profile.prenom = _make_field(
            customer.first_name, "cosium_client", "Cosium", 1.0, now
        )
        if customer.birth_date:
            profile.date_naissance = _make_field(
                str(customer.birth_date), "cosium_client", "Cosium", 1.0, now
            )
        if customer.social_security_number:
            profile.numero_secu = _make_field(
                customer.social_security_number, "cosium_client", "Cosium", 1.0, now
            )

    # 2. Load latest Cosium prescription
    prescription = _load_latest_prescription(db, tenant_id, customer_id)
    if prescription:
        src = f"cosium_prescription_{prescription.id}"
        src_label = f"Ordonnance Cosium"
        if prescription.prescription_date:
            src_label = f"Ordonnance du {prescription.prescription_date}"
        sources_used.append(src)

        if prescription.sphere_right is not None:
            profile.sphere_od = _make_field(
                prescription.sphere_right, src, src_label, 0.95
            )
        if prescription.cylinder_right is not None:
            profile.cylinder_od = _make_field(
                prescription.cylinder_right, src, src_label, 0.95
            )
        if prescription.axis_right is not None:
            profile.axis_od = _make_field(
                prescription.axis_right, src, src_label, 0.95
            )
        if prescription.addition_right is not None:
            profile.addition_od = _make_field(
                prescription.addition_right, src, src_label, 0.95
            )
        if prescription.sphere_left is not None:
            profile.sphere_og = _make_field(
                prescription.sphere_left, src, src_label, 0.95
            )
        if prescription.cylinder_left is not None:
            profile.cylinder_og = _make_field(
                prescription.cylinder_left, src, src_label, 0.95
            )
        if prescription.axis_left is not None:
            profile.axis_og = _make_field(
                prescription.axis_left, src, src_label, 0.95
            )
        if prescription.addition_left is not None:
            profile.addition_og = _make_field(
                prescription.addition_left, src, src_label, 0.95
            )
        if prescription.prescriber_name:
            profile.prescripteur = _make_field(
                prescription.prescriber_name, src, src_label, 0.95
            )
        if prescription.prescription_date:
            profile.date_ordonnance = _make_field(
                prescription.prescription_date, src, src_label, 0.95
            )

    # 3. Load devis (OptiFlow)
    devis = _load_devis(db, tenant_id, customer_id, devis_id)
    if devis:
        src = f"devis_{devis.id}"
        src_label = f"Devis {devis.numero}"
        sources_used.append(src)

        profile.montant_ttc = _make_field(
            float(devis.montant_ttc), src, src_label, 1.0
        )
        profile.part_secu = _make_field(
            float(devis.part_secu), src, src_label, 1.0
        )
        profile.part_mutuelle = _make_field(
            float(devis.part_mutuelle), src, src_label, 1.0
        )
        profile.reste_a_charge = _make_field(
            float(devis.reste_a_charge), src, src_label, 1.0
        )

        # Load devis lignes for equipment
        lignes = _load_devis_lignes(db, tenant_id, devis.id)
        for ligne in lignes:
            designation = ligne.designation.lower()
            if "monture" in designation or "cadre" in designation:
                profile.monture = _make_field(
                    ligne.designation, src, src_label, 1.0
                )
            else:
                profile.verres.append(
                    _make_field(ligne.designation, src, src_label, 1.0)
                )

    # 4. Load client mutuelles
    mutuelles = _load_client_mutuelles(db, tenant_id, customer_id)
    if mutuelles:
        best = mutuelles[0]  # Highest confidence
        src = f"mutuelle_{best.source}"
        src_label = f"Mutuelle ({best.source})"
        if src not in sources_used:
            sources_used.append(src)

        profile.mutuelle_nom = _make_field(
            best.mutuelle_name, src, src_label, best.confidence
        )
        if best.numero_adherent:
            profile.mutuelle_numero_adherent = _make_field(
                best.numero_adherent, src, src_label, best.confidence
            )
        if best.type_beneficiaire:
            profile.type_beneficiaire = _make_field(
                best.type_beneficiaire, src, src_label, best.confidence
            )
        if best.date_fin:
            profile.date_fin_droits = _make_field(
                str(best.date_fin), src, src_label, best.confidence
            )

    # 5. Load document extractions (OCR) and fill gaps
    extractions = _load_document_extractions(db, tenant_id, customer_id)
    for extraction in extractions:
        data = _parse_structured_data(extraction)
        if not data:
            continue
        doc_type = extraction.document_type or "unknown"
        src = f"document_ocr_{extraction.id}"
        src_label = f"Document OCR ({doc_type})"
        confidence = extraction.ocr_confidence or 0.7
        sources_used.append(src)

        # Fill identity gaps from OCR
        if doc_type == "attestation_mutuelle":
            if not profile.mutuelle_nom and data.get("mutuelle_nom"):
                profile.mutuelle_nom = _make_field(
                    data["mutuelle_nom"], src, src_label, confidence
                )
            if not profile.mutuelle_numero_adherent and data.get("numero_adherent"):
                profile.mutuelle_numero_adherent = _make_field(
                    data["numero_adherent"], src, src_label, confidence
                )
            if not profile.mutuelle_code_organisme and data.get("code_organisme"):
                profile.mutuelle_code_organisme = _make_field(
                    data["code_organisme"], src, src_label, confidence
                )
            if not profile.numero_secu and data.get("numero_secu"):
                profile.numero_secu = _make_field(
                    data["numero_secu"], src, src_label, confidence
                )
            if data.get("date_fin_droits") and not profile.date_fin_droits:
                profile.date_fin_droits = _make_field(
                    data["date_fin_droits"], src, src_label, confidence
                )

        elif doc_type == "ordonnance":
            # Fill optical data from OCR only if not already from Cosium
            if not profile.sphere_od and data.get("sphere_od") is not None:
                profile.sphere_od = _make_field(
                    data["sphere_od"], src, src_label, confidence
                )
            if not profile.sphere_og and data.get("sphere_og") is not None:
                profile.sphere_og = _make_field(
                    data["sphere_og"], src, src_label, confidence
                )
            if not profile.cylinder_od and data.get("cylinder_od") is not None:
                profile.cylinder_od = _make_field(
                    data["cylinder_od"], src, src_label, confidence
                )
            if not profile.cylinder_og and data.get("cylinder_og") is not None:
                profile.cylinder_og = _make_field(
                    data["cylinder_og"], src, src_label, confidence
                )
            if not profile.axis_od and data.get("axis_od") is not None:
                profile.axis_od = _make_field(
                    data["axis_od"], src, src_label, confidence
                )
            if not profile.axis_og and data.get("axis_og") is not None:
                profile.axis_og = _make_field(
                    data["axis_og"], src, src_label, confidence
                )
            if not profile.addition_od and data.get("addition_od") is not None:
                profile.addition_od = _make_field(
                    data["addition_od"], src, src_label, confidence
                )
            if not profile.addition_og and data.get("addition_og") is not None:
                profile.addition_og = _make_field(
                    data["addition_og"], src, src_label, confidence
                )
            if not profile.prescripteur and data.get("prescripteur"):
                profile.prescripteur = _make_field(
                    data["prescripteur"], src, src_label, confidence
                )
            if not profile.date_ordonnance and data.get("date_ordonnance"):
                profile.date_ordonnance = _make_field(
                    data["date_ordonnance"], src, src_label, confidence
                )

    # 6. Detect missing fields
    missing: list[str] = []
    for field_name in PEC_REQUIRED_FIELDS:
        if getattr(profile, field_name, None) is None:
            missing.append(field_name)
    profile.champs_manquants = missing

    # 7. Deduplicate sources
    profile.sources_utilisees = list(dict.fromkeys(sources_used))

    # 8. Calculate completude score
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
