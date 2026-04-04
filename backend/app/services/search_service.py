"""Service de recherche globale multi-entites."""

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models import Case, Customer, Devis, Facture

logger = get_logger("search_service")


def global_search(db: Session, tenant_id: int, query: str, limit: int = 10) -> dict:
    """Recherche dans clients, dossiers, devis, factures."""
    if not query or len(query) < 2:
        return {"clients": [], "dossiers": [], "devis": [], "factures": []}

    pattern = f"%{query}%"
    results: dict = {"clients": [], "dossiers": [], "devis": [], "factures": []}

    # Clients
    clients = db.scalars(
        select(Customer)
        .where(
            Customer.tenant_id == tenant_id,
            or_(
                Customer.first_name.ilike(pattern),
                Customer.last_name.ilike(pattern),
                Customer.email.ilike(pattern),
                Customer.phone.ilike(pattern),
            ),
        )
        .limit(limit)
    ).all()
    results["clients"] = [
        {"id": c.id, "type": "client", "label": f"{c.last_name} {c.first_name}", "detail": c.email or c.phone or ""}
        for c in clients
    ]

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

    # Factures
    factures = db.scalars(
        select(Facture).where(Facture.tenant_id == tenant_id, Facture.numero.ilike(pattern)).limit(limit)
    ).all()
    results["factures"] = [{"id": f.id, "type": "facture", "label": f.numero, "detail": f.status} for f in factures]

    total = sum(len(v) for v in results.values())
    logger.info("global_search", tenant_id=tenant_id, query=query, total_results=total)
    return results
