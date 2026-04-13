"""Helpers internes pour la detection de mutuelles client.

Sources de detection (par confiance decroissante) :
1. CosiumThirdPartyPayment avec montant AMC > 0 (1.0)
2. CosiumInvoice avec share_private_insurance > 0 (0.7)
3. OCR : attestation_mutuelle ou carte_mutuelle extraits (0.9)

Helpers :
- recuperation des invoices/TPP du client
- parsing JSON tolerant pour DocumentExtraction.structured_data
- matching d'un nom detecte avec un CosiumMutuelle de reference
"""
import json

from sqlalchemy import func as sa_func
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cosium_data import CosiumDocument, CosiumInvoice, CosiumThirdPartyPayment
from app.models.cosium_reference import CosiumMutuelle
from app.models.document_extraction import DocumentExtraction


def get_customer_invoices(
    db: Session, tenant_id: int, customer_id: int, cosium_id: str | int | None,
) -> list[CosiumInvoice]:
    """Charge les factures Cosium d'un client (par id interne ou cosium_id)."""
    q = select(CosiumInvoice).where(CosiumInvoice.tenant_id == tenant_id)
    if cosium_id:
        q = q.where(
            (CosiumInvoice.customer_id == customer_id)
            | (CosiumInvoice.customer_cosium_id == str(cosium_id))
        )
    else:
        q = q.where(CosiumInvoice.customer_id == customer_id)
    return list(db.scalars(q).all())


def detect_from_third_party_payments(
    db: Session, tenant_id: int, invoice_cosium_ids: list[str],
) -> dict | None:
    """Source 1 : tiers payant avec montant complementaire > 0. None si aucun."""
    if not invoice_cosium_ids:
        return None
    tpp_rows = db.scalars(
        select(CosiumThirdPartyPayment).where(
            CosiumThirdPartyPayment.tenant_id == tenant_id,
            CosiumThirdPartyPayment.invoice_cosium_id.in_(invoice_cosium_ids),
            CosiumThirdPartyPayment.additional_health_care_amount > 0,
        )
    ).all()
    if not tpp_rows:
        return None
    return {
        "mutuelle_name": "Mutuelle (tiers payant detecte)",
        "source": "cosium_tpp",
        "confidence": 1.0,
        "extra": {
            "total_amc_amount": round(sum(t.additional_health_care_amount for t in tpp_rows), 2),
            "tpp_count": len(tpp_rows),
        },
    }


def detect_from_invoice_insurance(invoices: list[CosiumInvoice]) -> dict | None:
    """Source 2 : factures avec part_complementaire > 0. None si aucune."""
    with_insurance = [inv for inv in invoices if inv.share_private_insurance > 0]
    if not with_insurance:
        return None
    return {
        "mutuelle_name": "Mutuelle (part complementaire facturee)",
        "source": "cosium_invoice",
        "confidence": 0.7,
        "extra": {
            "total_share_private_insurance": round(sum(i.share_private_insurance for i in with_insurance), 2),
            "invoice_count": len(with_insurance),
        },
    }


def _parse_structured_data(raw: str | None) -> dict | None:
    """Safely parse JSON structured_data from a DocumentExtraction."""
    if not raw:
        return None
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, TypeError):
        pass
    return None


def detect_from_ocr_documents(
    db: Session, tenant_id: int, cosium_id: str | int | None,
) -> list[dict]:
    """Source 3 : extraction OCR d'attestation/carte mutuelle. Liste possiblement vide."""
    if not cosium_id:
        return []

    doc_extractions = db.scalars(
        select(DocumentExtraction).join(
            CosiumDocument,
            (CosiumDocument.cosium_document_id == DocumentExtraction.cosium_document_id)
            & (CosiumDocument.tenant_id == DocumentExtraction.tenant_id),
        ).where(
            DocumentExtraction.tenant_id == tenant_id,
            DocumentExtraction.document_type.in_(["attestation_mutuelle", "carte_mutuelle"]),
            CosiumDocument.customer_cosium_id == int(cosium_id),
        ).order_by(DocumentExtraction.extracted_at.desc())
    ).all()

    detected: list[dict] = []
    seen_mutuelles: set[str] = set()

    for extraction in doc_extractions:
        structured = _parse_structured_data(extraction.structured_data)
        if not structured:
            continue
        nom_mutuelle = (
            structured.get("nom_mutuelle")
            or structured.get("mutuelle")
            or structured.get("organisme")
            or ""
        )
        if not nom_mutuelle:
            continue
        key = nom_mutuelle.upper().strip()
        if key in seen_mutuelles:
            continue
        seen_mutuelles.add(key)

        detected.append({
            "mutuelle_name": nom_mutuelle.strip(),
            "source": "document_ocr",
            "confidence": 0.9,
            "numero_adherent": (
                structured.get("numero_adherent")
                or structured.get("num_adherent")
                or structured.get("numero_contrat")
            ),
            "extra": {
                "document_type": extraction.document_type,
                "code_organisme": structured.get("code_organisme") or structured.get("code_amc"),
                "extraction_id": extraction.id,
            },
        })
    return detected


def try_match_cosium_mutuelle(db: Session, tenant_id: int, detection: dict) -> None:
    """Mute la detection en lui ajoutant `mutuelle_id` si trouve dans CosiumMutuelle."""
    mutuelle_name = detection.get("mutuelle_name", "")
    if not mutuelle_name:
        return

    cosium_mut = db.scalars(
        select(CosiumMutuelle).where(
            CosiumMutuelle.tenant_id == tenant_id,
            CosiumMutuelle.hidden.is_(False),
            sa_func.upper(CosiumMutuelle.name).contains(mutuelle_name.upper().strip()),
        ).limit(1)
    ).first()

    if not cosium_mut:
        code_organisme = (detection.get("extra") or {}).get("code_organisme")
        if code_organisme:
            cosium_mut = db.scalars(
                select(CosiumMutuelle).where(
                    CosiumMutuelle.tenant_id == tenant_id,
                    CosiumMutuelle.hidden.is_(False),
                    CosiumMutuelle.code == str(code_organisme),
                ).limit(1)
            ).first()

    if cosium_mut:
        detection["mutuelle_id"] = cosium_mut.id
        detection["mutuelle_name"] = cosium_mut.name or detection["mutuelle_name"]
