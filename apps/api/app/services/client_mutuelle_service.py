"""Service for detecting and managing client-mutuelle associations.

Helpers de detection : `_client_mutuelle_detection.py`.
"""

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.domain.schemas.client_mutuelle import (
    ClientMutuelleCreate,
    ClientMutuelleResponse,
    MutuelleDetectionResult,
)
from app.models.cosium_data import CosiumDocument, CosiumInvoice
from app.models.document_extraction import DocumentExtraction
from app.repositories import client_mutuelle_repo, client_repo
from app.services._client_mutuelle_detection import (
    detect_from_invoice_insurance,
    detect_from_ocr_documents,
    detect_from_third_party_payments,
    get_customer_invoices,
    try_match_cosium_mutuelle,
)

logger = get_logger("client_mutuelle_service")


def get_client_mutuelles(
    db: Session, tenant_id: int, customer_id: int,
) -> list[ClientMutuelleResponse]:
    """Return all mutuelles for a client."""
    customer = client_repo.get_by_id(db, customer_id, tenant_id)
    if not customer:
        raise NotFoundError("client", customer_id)
    records = client_mutuelle_repo.get_by_customer(db, customer_id, tenant_id)
    return [ClientMutuelleResponse.model_validate(r) for r in records]


def add_client_mutuelle(
    db: Session, tenant_id: int, customer_id: int, payload: ClientMutuelleCreate,
) -> ClientMutuelleResponse:
    """Manually add a mutuelle to a client."""
    customer = client_repo.get_by_id(db, customer_id, tenant_id)
    if not customer:
        raise NotFoundError("client", customer_id)

    data = payload.model_dump()
    data["tenant_id"] = tenant_id
    data["customer_id"] = customer_id

    record = client_mutuelle_repo.create(db, data)
    db.commit()
    logger.info(
        "client_mutuelle_created",
        customer_id=customer_id,
        mutuelle_name=payload.mutuelle_name,
        source=payload.source,
    )
    return ClientMutuelleResponse.model_validate(record)


def delete_client_mutuelle(
    db: Session, tenant_id: int, customer_id: int, mutuelle_id: int,
) -> bool:
    """Remove a mutuelle from a client."""
    record = client_mutuelle_repo.get_by_id(db, mutuelle_id, tenant_id)
    if not record or record.customer_id != customer_id:
        raise NotFoundError("client_mutuelle", mutuelle_id)
    deleted = client_mutuelle_repo.delete(db, mutuelle_id, tenant_id)
    db.commit()
    if deleted:
        logger.info(
            "client_mutuelle_deleted",
            customer_id=customer_id,
            mutuelle_id=mutuelle_id,
        )
    return deleted


def detect_client_mutuelles(
    db: Session, tenant_id: int, customer_id: int,
) -> list[dict]:
    """Auto-detect mutuelles for a client from multiple Cosium sources.

    Sources : tiers payant > facture > OCR documents.
    Stoppe sur le source 2 si source 1 a deja trouve (priorite confiance).
    """
    customer = client_repo.get_by_id(db, customer_id, tenant_id)
    if not customer:
        raise NotFoundError("client", customer_id)

    cosium_id = getattr(customer, "cosium_id", None)
    invoices = get_customer_invoices(db, tenant_id, customer_id, cosium_id)
    invoice_cosium_ids = [inv.cosium_id for inv in invoices]

    detected: list[dict] = []

    # Source 1 : TPP (tiers payant) — confiance 1.0
    tpp = detect_from_third_party_payments(db, tenant_id, invoice_cosium_ids)
    if tpp:
        detected.append(tpp)

    # Source 2 : invoice avec part complementaire — fallback uniquement
    if not detected:
        inv_det = detect_from_invoice_insurance(invoices)
        if inv_det:
            detected.append(inv_det)

    # Source 3 : OCR (toujours ajoute pour enrichir avec nom precis + numero adherent)
    detected.extend(detect_from_ocr_documents(db, tenant_id, cosium_id))

    # Enrichissement : matching avec CosiumMutuelle de reference
    for det in detected:
        try_match_cosium_mutuelle(db, tenant_id, det)

    return detected


def _list_customers_to_scan(db: Session, tenant_id: int) -> list[int]:
    """Recupere tous les clients ayant des factures Cosium ou des documents mutuelle."""
    customer_ids_with_invoices = db.scalars(
        select(CosiumInvoice.customer_id)
        .where(CosiumInvoice.tenant_id == tenant_id, CosiumInvoice.customer_id.isnot(None))
        .group_by(CosiumInvoice.customer_id)
    ).all()

    customer_ids_with_ocr = db.scalars(
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

    return list(
        {cid for cid in customer_ids_with_invoices if cid}
        | {cid for cid in customer_ids_with_ocr if cid}
    )


def _persist_detection(db: Session, tenant_id: int, customer_id: int, det: dict) -> bool:
    """Cree un ClientMutuelle si pas deja en base. True si nouveau, False si existait."""
    existing = client_mutuelle_repo.find_existing(
        db,
        customer_id=customer_id,
        tenant_id=tenant_id,
        mutuelle_name=det["mutuelle_name"],
        source=det["source"],
    )
    if existing:
        return False
    create_data: dict = {
        "tenant_id": tenant_id,
        "customer_id": customer_id,
        "mutuelle_id": det.get("mutuelle_id"),
        "mutuelle_name": det["mutuelle_name"],
        "source": det["source"],
        "confidence": det["confidence"],
        "active": True,
    }
    if det.get("numero_adherent"):
        create_data["numero_adherent"] = det["numero_adherent"]
    client_mutuelle_repo.create(db, create_data)
    return True


def detect_all_clients_mutuelles(db: Session, tenant_id: int) -> MutuelleDetectionResult:
    """Batch detect mutuelles for ALL clients with Cosium invoices or OCR docs."""
    result = MutuelleDetectionResult()
    unique_customer_ids = _list_customers_to_scan(db, tenant_id)
    result.total_clients_scanned = len(unique_customer_ids)

    for cust_id in unique_customer_ids:
        try:
            detections = detect_client_mutuelles(db, tenant_id, cust_id)
            if not detections:
                continue
            result.clients_with_mutuelle += 1
            for det in detections:
                if _persist_detection(db, tenant_id, cust_id, det):
                    result.new_mutuelles_created += 1
                else:
                    result.existing_mutuelles_skipped += 1
        except (SQLAlchemyError, ValueError, KeyError) as exc:
            logger.warning("mutuelle_detection_error", customer_id=cust_id, error=str(exc))
            result.errors += 1

    db.commit()
    logger.info(
        "batch_mutuelle_detection_complete",
        tenant_id=tenant_id,
        total_scanned=result.total_clients_scanned,
        with_mutuelle=result.clients_with_mutuelle,
        new_created=result.new_mutuelles_created,
    )
    return result
