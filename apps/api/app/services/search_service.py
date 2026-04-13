"""Service de recherche globale multi-entites."""

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models import Case, Customer, Devis, Facture
from app.models.cosium_data import CosiumDocument, CosiumInvoice, CosiumPrescription
from app.models.document_extraction import DocumentExtraction

logger = get_logger("search_service")

EMPTY_RESULT: dict[str, list] = {
    "clients": [], "dossiers": [], "devis": [], "factures": [],
    "cosium_factures": [], "ordonnances": [], "documents_ocr": [],
}


def _fmt_diopter(val: float | None) -> str:
    if val is None:
        return "-"
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:.2f}"


def _build_correction_summary(prescription: CosiumPrescription) -> str | None:
    """Build a short OD/OG summary string from a prescription."""
    parts: list[str] = []
    if hasattr(prescription, "sphere_right") and prescription.sphere_right is not None:
        parts.append(f"OD {_fmt_diopter(prescription.sphere_right)}")
    if hasattr(prescription, "sphere_left") and prescription.sphere_left is not None:
        parts.append(f"OG {_fmt_diopter(prescription.sphere_left)}")
    return " | ".join(parts) if parts else None


def _search_clients(db: Session, tenant_id: int, pattern: str, limit: int) -> tuple[list[dict], set[int]]:
    """Recherche clients par nom/prenom/email/telephone. Retourne (results, ids_trouves)."""
    clients = db.scalars(
        select(Customer).where(
            Customer.tenant_id == tenant_id,
            Customer.deleted_at.is_(None),
            or_(
                Customer.first_name.ilike(pattern),
                Customer.last_name.ilike(pattern),
                Customer.email.ilike(pattern),
                Customer.phone.ilike(pattern),
            ),
        ).limit(limit)
    ).all()
    found: set[int] = {c.id for c in clients}
    results = [{
        "id": c.id, "type": "client",
        "label": f"{c.last_name} {c.first_name}",
        "detail": c.email or c.phone or "",
        "phone": c.phone,
        "city": c.city if hasattr(c, "city") else None,
    } for c in clients]
    return results, found


def _search_clients_by_ssn(
    db: Session, tenant_id: int, pattern: str, limit: int, already_found: set[int],
) -> list[dict]:
    """Recherche clients par numero securite sociale (>= 5 chars)."""
    ssn_customers = db.scalars(
        select(Customer).where(
            Customer.tenant_id == tenant_id,
            Customer.social_security_number.ilike(pattern),
            Customer.deleted_at.is_(None),
        ).limit(limit)
    ).all()
    results = []
    for c in ssn_customers:
        if c.id in already_found:
            continue
        already_found.add(c.id)
        ssn_masked = (
            f"SS: ***{c.social_security_number[-4:]}"
            if c.social_security_number and len(c.social_security_number) >= 4
            else "SS: ***"
        )
        results.append({
            "id": c.id, "type": "client",
            "label": f"{c.last_name} {c.first_name}",
            "detail": ssn_masked,
        })
    return results


def _search_cases(db: Session, tenant_id: int, pattern: str, limit: int) -> list[dict]:
    cases = db.scalars(
        select(Case)
        .join(Customer, Case.customer_id == Customer.id)
        .where(
            Case.tenant_id == tenant_id,
            or_(Customer.first_name.ilike(pattern), Customer.last_name.ilike(pattern)),
        )
        .limit(limit)
    ).all()
    return [
        {"id": c.id, "type": "dossier", "label": f"Dossier #{c.id}", "detail": c.status}
        for c in cases
    ]


def _search_devis(db: Session, tenant_id: int, pattern: str, limit: int) -> list[dict]:
    devis = db.scalars(
        select(Devis).where(Devis.tenant_id == tenant_id, Devis.numero.ilike(pattern)).limit(limit)
    ).all()
    return [{
        "id": d.id, "type": "devis",
        "label": d.numero, "detail": d.status,
        "amount": float(d.montant_ttc) if hasattr(d, "montant_ttc") and d.montant_ttc else None,
    } for d in devis]


def _search_factures(db: Session, tenant_id: int, pattern: str, limit: int) -> list[dict]:
    factures = db.scalars(
        select(Facture).where(Facture.tenant_id == tenant_id, Facture.numero.ilike(pattern)).limit(limit)
    ).all()
    return [{
        "id": f.id, "type": "facture", "label": f.numero, "detail": f.status,
        "amount": float(f.montant_ttc) if hasattr(f, "montant_ttc") and f.montant_ttc else None,
        "date": str(f.date_emission) if hasattr(f, "date_emission") and f.date_emission else None,
    } for f in factures]


def _search_cosium_invoices(db: Session, tenant_id: int, pattern: str, limit: int) -> list[dict]:
    cosium_invoices = db.scalars(
        select(CosiumInvoice).where(
            CosiumInvoice.tenant_id == tenant_id,
            or_(
                CosiumInvoice.invoice_number.ilike(pattern),
                CosiumInvoice.customer_name.ilike(pattern),
            ),
        ).limit(limit)
    ).all()
    return [{
        "id": ci.id, "type": "cosium_facture",
        "label": ci.invoice_number,
        "detail": f"{ci.customer_name} — {ci.total_ti} EUR",
        "amount": float(ci.total_ti) if ci.total_ti else None,
        "client_name": ci.customer_name,
        "date": str(ci.invoice_date) if hasattr(ci, "invoice_date") and ci.invoice_date else None,
    } for ci in cosium_invoices]


def _search_prescriptions(db: Session, tenant_id: int, pattern: str, limit: int) -> list[dict]:
    ordonnances = db.scalars(
        select(CosiumPrescription).where(
            CosiumPrescription.tenant_id == tenant_id,
            CosiumPrescription.prescriber_name.ilike(pattern),
        ).limit(limit)
    ).all()
    return [{
        "id": o.id, "type": "ordonnance",
        "label": f"Ordonnance #{o.id}",
        "detail": f"Dr. {o.prescriber_name}" if o.prescriber_name else "",
        "date": str(o.prescription_date) if hasattr(o, "prescription_date") and o.prescription_date else None,
        "prescriber_name": o.prescriber_name,
        "correction_summary": _build_correction_summary(o),
    } for o in ordonnances]


def _search_ocr_documents(db: Session, tenant_id: int, pattern: str, limit: int) -> list[dict]:
    """Recherche dans le texte extrait OCR. Min 3 chars verifie par l'appelant."""
    ocr_results = db.execute(
        select(
            DocumentExtraction.cosium_document_id,
            DocumentExtraction.document_type,
            CosiumDocument.customer_cosium_id,
            CosiumDocument.name,
        )
        .join(
            CosiumDocument,
            (CosiumDocument.cosium_document_id == DocumentExtraction.cosium_document_id)
            & (CosiumDocument.tenant_id == DocumentExtraction.tenant_id),
        )
        .where(
            DocumentExtraction.tenant_id == tenant_id,
            DocumentExtraction.raw_text.ilike(pattern),
        )
        .limit(limit)
    ).all()

    seen_doc_ids: set[int] = set()
    results: list[dict] = []
    for row in ocr_results:
        doc_id = row[0]
        if doc_id in seen_doc_ids:
            continue
        seen_doc_ids.add(doc_id)

        doc_type = row[1] or "document"
        customer_cosium_id = row[2]
        doc_name = row[3] or ""

        customer_label = ""
        if customer_cosium_id:
            cust = db.scalars(
                select(Customer).where(
                    Customer.tenant_id == tenant_id,
                    Customer.cosium_id == str(customer_cosium_id),
                ).limit(1)
            ).first()
            if cust:
                customer_label = f"{cust.last_name} {cust.first_name}"

        detail_parts = [doc_type]
        if customer_label:
            detail_parts.append(customer_label)
        if doc_name:
            detail_parts.append(doc_name[:60])

        results.append({
            "id": doc_id, "type": "document_ocr",
            "label": f"Document OCR #{doc_id}",
            "detail": " — ".join(detail_parts),
        })
    return results


def global_search(db: Session, tenant_id: int, query: str, limit: int = 10) -> dict:
    """Recherche dans clients, dossiers, devis, factures, factures Cosium, ordonnances, OCR."""
    if not query or len(query) < 2:
        return {k: list(v) for k, v in EMPTY_RESULT.items()}

    pattern = f"%{query}%"
    results: dict = {k: list(v) for k, v in EMPTY_RESULT.items()}

    # Clients (par nom/email/telephone) puis SSN si query >= 5 chars
    clients_results, found_ids = _search_clients(db, tenant_id, pattern, limit)
    results["clients"] = clients_results
    if len(query) >= 5:
        results["clients"].extend(_search_clients_by_ssn(db, tenant_id, pattern, limit, found_ids))

    results["dossiers"] = _search_cases(db, tenant_id, pattern, limit)
    results["devis"] = _search_devis(db, tenant_id, pattern, limit)
    results["factures"] = _search_factures(db, tenant_id, pattern, limit)
    results["cosium_factures"] = _search_cosium_invoices(db, tenant_id, pattern, limit)
    results["ordonnances"] = _search_prescriptions(db, tenant_id, pattern, limit)

    # OCR : min 3 chars (eviter le bruit)
    if len(query) >= 3:
        results["documents_ocr"] = _search_ocr_documents(db, tenant_id, pattern, limit)

    total = sum(len(v) for v in results.values())
    logger.info("global_search", tenant_id=tenant_id, query=query, total_results=total)
    return results
