"""Seed de donnees de demo enrichies pour presentations.

Usage manuel:
    docker compose exec api python -c \\
        "from tests.factories.seed import seed_demo_data; \\
         from app.db.session import SessionLocal; seed_demo_data(SessionLocal())"

Egalement appele depuis l'endpoint admin POST /api/v1/sync/seed-demo.
"""

from sqlalchemy.orm import Session

from app.models import Customer, Tenant
from tests.factories.seed_data import (
    seed_bank_transactions,
    seed_interactions,
    seed_marketing_and_notifications,
    seed_pec_requests,
)
from tests.factories.seed_entities import (
    seed_cases,
    seed_customers,
    seed_devis,
    seed_factures_and_payments,
    seed_organizations,
)


def seed_demo_data(db: Session) -> dict:
    """Generate rich demo data: 50 clients, 30 cases, 15 devis, factures, payments, PEC, banking, marketing."""
    stats = {
        "clients": 0, "cases": 0, "devis": 0, "factures": 0,
        "payments": 0, "pec": 0, "bank_transactions": 0,
        "campaigns": 0, "interactions": 0,
    }

    if db.query(Customer).count() > 5:
        return {"status": "skipped", "reason": "Demo data already exists"}

    tenant = db.query(Tenant).filter(Tenant.slug == "default").first()
    tenant_id = tenant.id if tenant else 1

    orgs = seed_organizations(db, tenant_id)
    customers = seed_customers(db, tenant_id, stats)
    cases = seed_cases(db, tenant_id, customers, stats)
    devis_list = seed_devis(db, tenant_id, cases, stats)
    factures_created = seed_factures_and_payments(db, tenant_id, devis_list, stats)

    seed_interactions(db, tenant_id, customers)
    stats["interactions"] = 20

    seed_pec_requests(db, tenant_id, factures_created, orgs, stats)
    seed_bank_transactions(db, tenant_id, stats)
    seed_marketing_and_notifications(db, tenant_id, customers, factures_created, stats)

    db.commit()
    return stats
