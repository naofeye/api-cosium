"""Service de recherche globale multi-entites."""

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models import Case, Customer, Devis, Facture
from app.models.cosium_data import CosiumInvoice

logger = get_logger("search_service")


def global_search(db: Session, tenant_id: int, query: str, limit: int = 10) -> dict:
    """Recherche dans clients, dossiers, devis, factures, factures Cosium."""
    if not query or len(query) < 2:
        return {"clients": [], "dossiers": [], "devis": [], "factures": [], "cosium_factures": []}

    pattern = f"%{query}%"
    results: dict = {"clients": [], "dossiers": [], "devis": [], "factures": [], "cosium_factures": []}

    # Clients (nom, prenom, email, telephone)
    clients = db.scalars(
        select(Customer)
        .where(
            Customer.tenant_id == tenant_id,
            Customer.deleted_at.is_(None),
            or_(
                Customer.first_name.ilike(pattern),
                Customer.last_name.ilike(pattern),
                Customer.email.ilike(pattern),
                Customer.phone.ilike(pattern),
            ),
        )
        .limit(limit)
    ).all()
    client_ids_found: set[int] = set()
    for c in clients:
        client_ids_found.add(c.id)
        results["clients"].append(
            {"id": c.id, "type": "client", "label": f"{c.last_name} {c.first_name}", "detail": c.email or c.phone or ""}
        )

    # Clients par numero de securite sociale (requetes >= 5 caracteres)
    if len(query) >= 5:
        ssn_customers = db.scalars(
            select(Customer)
            .where(
                Customer.tenant_id == tenant_id,
                Customer.social_security_number.ilike(pattern),
                Customer.deleted_at.is_(None),
            )
            .limit(limit)
        ).all()
        for c in ssn_customers:
            if c.id not in client_ids_found:
                client_ids_found.add(c.id)
                results["clients"].append(
                    {
                        "id": c.id,
                        "type": "client",
                        "label": f"{c.last_name} {c.first_name}",
                        "detail": f"SS: {c.social_security_number}",
                    }
                )

    # Dossiers (via customer name)
    cases = db.scalars(
        select(Case)
        .join(Customer, Case.customer_id == Customer.id)
        .where(
            Case.tenant_id == tenant_id,
            or_(
                Customer.first_name.ilike(pattern),
                Customer.last_name.ilike(pattern),
            ),
        )
        .limit(limit)
    ).all()
    results["dossiers"] = [
        {"id": c.id, "type": "dossier", "label": f"Dossier #{c.id}", "detail": c.status} for c in cases
    ]

    # Devis
    devis = db.scalars(
        select(Devis).where(Devis.tenant_id == tenant_id, Devis.numero.ilike(pattern)).limit(limit)
    ).all()
    results["devis"] = [{"id": d.id, "type": "devis", "label": d.numero, "detail": d.status} for d in devis]

    # Factures OptiFlow
    factures = db.scalars(
        select(Facture).where(Facture.tenant_id == tenant_id, Facture.numero.ilike(pattern)).limit(limit)
    ).all()
    results["factures"] = [{"id": f.id, "type": "facture", "label": f.numero, "detail": f.status} for f in factures]

    # Factures Cosium (par numero de facture)
    cosium_invoices = db.scalars(
        select(CosiumInvoice)
        .where(
            CosiumInvoice.tenant_id == tenant_id,
            CosiumInvoice.invoice_number.ilike(pattern),
        )
        .limit(limit)
    ).all()
    results["cosium_factures"] = [
        {
            "id": ci.id,
            "type": "cosium_facture",
            "label": ci.invoice_number,
            "detail": f"{ci.customer_name} — {ci.total_ti} EUR",
        }
        for ci in cosium_invoices
    ]

    total = sum(len(v) for v in results.values())
    logger.info("global_search", tenant_id=tenant_id, query=query, total_results=total)
    return results
