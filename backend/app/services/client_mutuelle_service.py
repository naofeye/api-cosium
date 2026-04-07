"""Service for detecting and managing client-mutuelle associations."""

import json

from sqlalchemy import func as sa_func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.domain.schemas.client_mutuelle import (
    ClientMutuelleCreate,
    ClientMutuelleResponse,
    MutuelleDetectionResult,
)
from app.models.client import Customer
from app.models.cosium_data import CosiumDocument, CosiumInvoice, CosiumThirdPartyPayment
from app.models.cosium_reference import CosiumMutuelle
from app.models.document_extraction import DocumentExtraction
from app.repositories import client_mutuelle_repo

logger = get_logger("client_mutuelle_service")


def get_client_mutuelles(
    db: Session, tenant_id: int, customer_id: int
) -> list[ClientMutuelleResponse]:
    """Return all mutuelles for a client."""
    customer = db.get(Customer, customer_id)
    if not customer or customer.tenant_id != tenant_id:
        raise NotFoundError("client", customer_id)
    records = client_mutuelle_repo.get_by_customer(db, customer_id, tenant_id)
    return [ClientMutuelleResponse.model_validate(r) for r in records]


def add_client_mutuelle(
    db: Session, tenant_id: int, customer_id: int, payload: ClientMutuelleCreate
) -> ClientMutuelleResponse:
    """Manually add a mutuelle to a client."""
    customer = db.get(Customer, customer_id)
    if not customer or customer.tenant_id != tenant_id:
        raise NotFoundError("client", customer_id)

    data = payload.model_dump()
    data["tenant_id"] = tenant_id
    data["customer_id"] = customer_id

    record = client_mutuelle_repo.create(db, data)
    logger.info(
        "client_mutuelle_created",
        customer_id=customer_id,
        mutuelle_name=payload.mutuelle_name,
        source=payload.source,
    )
    return ClientMutuelleResponse.model_validate(record)


def delete_client_mutuelle(
    db: Session, tenant_id: int, customer_id: int, mutuelle_id: int
) -> bool:
    """Remove a mutuelle from a client."""
    record = client_mutuelle_repo.get_by_id(db, mutuelle_id, tenant_id)
    if not record or record.customer_id != customer_id:
        raise NotFoundError("client_mutuelle", mutuelle_id)
    deleted = client_mutuelle_repo.delete(db, mutuelle_id, tenant_id)
    if deleted:
        logger.info(
            "client_mutuelle_deleted",
            customer_id=customer_id,
            mutuelle_id=mutuelle_id,
        )
    return deleted


def detect_client_mutuelles(
    db: Session, tenant_id: int, customer_id: int
) -> list[dict]:
    """Auto-detect mutuelles for a client from multiple Cosium sources."""
    customer = db.get(Customer, customer_id)
    if not customer or customer.tenant_id != tenant_id:
        raise NotFoundError("client", customer_id)

    detected: list[dict] = []
    cosium_id = getattr(customer, "cosium_id", None)
    f"{customer.last_name} {customer.first_name}".strip()

    # --- Get client's Cosium invoices ---
    inv_query = select(CosiumInvoice).where(CosiumInvoice.tenant_id == tenant_id)
    if cosium_id:
        inv_query = inv_query.where(
            (CosiumInvoice.customer_id == customer_id)
            | (CosiumInvoice.customer_cosium_id == str(cosium_id))
        )
    else:
        inv_query = inv_query.where(CosiumInvoice.customer_id == customer_id)
    invoices = db.scalars(inv_query).all()
    invoice_cosium_ids = [inv.cosium_id for inv in invoices]

    # --- Source 1: CosiumThirdPartyPayment with additional_health_care_amount > 0 ---
    if invoice_cosium_ids:
        tpp_query = select(CosiumThirdPartyPayment).where(
            CosiumThirdPartyPayment.tenant_id == tenant_id,
            CosiumThirdPartyPayment.invoice_cosium_id.in_(invoice_cosium_ids),
            CosiumThirdPartyPayment.additional_health_care_amount > 0,
        )
        tpp_rows = db.scalars(tpp_query).all()
        if tpp_rows:
            total_amc = sum(t.additional_health_care_amount for t in tpp_rows)
            detected.append({
                "mutuelle_name": "Mutuelle (tiers payant detecte)",
                "source": "cosium_tpp",
                "confidence": 1.0,
                "extra": {
                    "total_amc_amount": round(total_amc, 2),
                    "tpp_count": len(tpp_rows),
                },
            })

    # --- Source 2: CosiumInvoice with share_private_insurance > 0 ---
    invoices_with_insurance = [
        inv for inv in invoices if inv.share_private_insurance > 0
    ]
    if invoices_with_insurance and not detected:
        total_insurance = sum(
            inv.share_private_insurance for inv in invoices_with_insurance
        )
        detected.append({
            "mutuelle_name": "Mutuelle (part complementaire facturee)",
            "source": "cosium_invoice",
            "confidence": 0.7,
            "extra": {
                "total_share_private_insurance": round(total_insurance, 2),
                "invoice_count": len(invoices_with_insurance),
            },
        })

    # --- Source 3: OCR extracted documents (attestation_mutuelle, carte_mutuelle) ---
    ocr_detections = _detect_from_ocr_documents(db, tenant_id, customer_id, cosium_id)
    detected.extend(ocr_detections)

    # --- Try to match all detections with known CosiumMutuelle ---
    for det in detected:
        _try_match_cosium_mutuelle(db, tenant_id, det)

    return detected


def _detect_from_ocr_documents(
    db: Session, tenant_id: int, customer_id: int, cosium_id: str | int | None
) -> list[dict]:
    """Detect mutuelles from OCR-extracted attestation_mutuelle and carte_mutuelle documents."""
    if not cosium_id:
        return []

    # Find DocumentExtraction rows linked to this customer's CosiumDocuments
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

    if not doc_extractions:
        return []

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

        # Deduplicate by mutuelle name (case-insensitive)
        key = nom_mutuelle.upper().strip()
        if key in seen_mutuelles:
            continue
        seen_mutuelles.add(key)

        numero_adherent = (
            structured.get("numero_adherent")
            or structured.get("num_adherent")
            or structured.get("numero_contrat")
        )
        code_organisme = (
            structured.get("code_organisme")
            or structured.get("code_amc")
        )

        detected.append({
            "mutuelle_name": nom_mutuelle.strip(),
            "source": "document_ocr",
            "confidence": 0.9,
            "numero_adherent": numero_adherent,
            "extra": {
                "document_type": extraction.document_type,
                "code_organisme": code_organisme,
                "extraction_id": extraction.id,
            },
        })

    return detected


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


def _try_match_cosium_mutuelle(
    db: Session, tenant_id: int, detection: dict
) -> None:
    """Attempt to match a detection with a known CosiumMutuelle record."""
    mutuelle_name = detection.get("mutuelle_name", "")
    if not mutuelle_name:
        return

    # Try ILIKE match on name
    cosium_mut = db.scalars(
        select(CosiumMutuelle).where(
            CosiumMutuelle.tenant_id == tenant_id,
            CosiumMutuelle.hidden.is_(False),
            sa_func.upper(CosiumMutuelle.name).contains(mutuelle_name.upper().strip()),
        ).limit(1)
    ).first()

    # Fallback: try matching by code_organisme from OCR extra data
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


def detect_all_clients_mutuelles(
    db: Session, tenant_id: int
) -> MutuelleDetectionResult:
    """Batch detect mutuelles for ALL clients with Cosium invoices."""
    result = MutuelleDetectionResult()

    # Get all customers that have Cosium invoices in this tenant
    customer_ids_with_invoices = db.scalars(
        select(CosiumInvoice.customer_id)
        .where(
            CosiumInvoice.tenant_id == tenant_id,
            CosiumInvoice.customer_id.isnot(None),
        )
        .group_by(CosiumInvoice.customer_id)
    ).all()

    # Also get customers with OCR-extracted mutuelle documents
    customer_ids_with_ocr_docs = db.scalars(
        select(CosiumDocument.customer_id).join(
            DocumentExtraction,
            (CosiumDocument.cosium_document_id == DocumentExtraction.cosium_document_id)
            & (CosiumDocument.tenant_id == DocumentExtraction.tenant_id),
        ).where(
            CosiumDocument.tenant_id == tenant_id,
            CosiumDocument.customer_id.isnot(None),
            DocumentExtraction.document_type.in_(["attestation_mutuelle", "carte_mutuelle"]),
        ).group_by(CosiumDocument.customer_id)
    ).all()

    unique_customer_ids = list(
        {cid for cid in customer_ids_with_invoices if cid}
        | {cid for cid in customer_ids_with_ocr_docs if cid}
    )
    result.total_clients_scanned = len(unique_customer_ids)

    for cust_id in unique_customer_ids:
        try:
            detections = detect_client_mutuelles(db, tenant_id, cust_id)
            if not detections:
                continue

            result.clients_with_mutuelle += 1

            for det in detections:
                existing = client_mutuelle_repo.find_existing(
                    db,
                    customer_id=cust_id,
                    tenant_id=tenant_id,
                    mutuelle_name=det["mutuelle_name"],
                    source=det["source"],
                )
                if existing:
                    result.existing_mutuelles_skipped += 1
                    continue

                create_data: dict = {
                    "tenant_id": tenant_id,
                    "customer_id": cust_id,
                    "mutuelle_id": det.get("mutuelle_id"),
                    "mutuelle_name": det["mutuelle_name"],
                    "source": det["source"],
                    "confidence": det["confidence"],
                    "active": True,
                }
                if det.get("numero_adherent"):
                    create_data["numero_adherent"] = det["numero_adherent"]
                client_mutuelle_repo.create(db, create_data)
                result.new_mutuelles_created += 1

        except Exception as exc:
            logger.warning(
                "mutuelle_detection_error",
                customer_id=cust_id,
                error=str(exc),
            )
            result.errors += 1

    logger.info(
        "batch_mutuelle_detection_complete",
        tenant_id=tenant_id,
        total_scanned=result.total_clients_scanned,
        with_mutuelle=result.clients_with_mutuelle,
        new_created=result.new_mutuelles_created,
    )
    return result
