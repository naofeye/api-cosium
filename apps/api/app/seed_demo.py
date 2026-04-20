"""Seed de donnees de demo enrichies pour presentations.

Usage: docker compose exec api python -c "from app.seed_demo import seed_demo_data; from app.db.session import SessionLocal; seed_demo_data(SessionLocal())"
"""

import random
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import (
    Case,
    Customer,
    Devis,
    DevisLigne,
    Document,
    Facture,
    PayerOrganization,
    Payment,
    Tenant,
)
from app.seed_demo_data import (
    CITIES,
    DOC_TYPES,
    FIRST_NAMES,
    LAST_NAMES,
    PRODUCTS,
    SOURCES,
    seed_bank_transactions,
    seed_interactions,
    seed_marketing_and_notifications,
    seed_pec_requests,
)


def seed_demo_data(db: Session) -> dict:
    """Generate rich demo data: 50 clients, 30 cases, 15 devis, factures, payments, PEC, banking, marketing."""
    stats = {
        "clients": 0,
        "cases": 0,
        "devis": 0,
        "factures": 0,
        "payments": 0,
        "pec": 0,
        "bank_transactions": 0,
        "campaigns": 0,
        "interactions": 0,
    }

    if db.query(Customer).count() > 5:
        return {"status": "skipped", "reason": "Demo data already exists"}

    # Get default tenant
    tenant = db.query(Tenant).filter(Tenant.slug == "default").first()
    tenant_id = tenant.id if tenant else 1

    # Organizations
    orgs = []
    for name, type_, code in [
        ("MGEN", "mutuelle", "MGEN"),
        ("Harmonie Mutuelle", "mutuelle", "HARM"),
        ("CPAM Paris", "secu", "CPAM75"),
        ("CPAM Lyon", "secu", "CPAM69"),
    ]:
        existing = db.query(PayerOrganization).filter_by(code=code).first()
        if not existing:
            org = PayerOrganization(
                tenant_id=tenant_id, name=name, type=type_, code=code, contact_email=f"contact@{code.lower()}.fr"
            )
            db.add(org)
            db.flush()
            orgs.append(org)
        else:
            orgs.append(existing)

    # Customers
    customers = []
    for i in range(50):
        fn = random.choice(FIRST_NAMES)
        ln = random.choice(LAST_NAMES)
        city, cp = random.choice(CITIES)
        c = Customer(
            tenant_id=tenant_id,
            first_name=fn,
            last_name=ln,
            email=f"{fn.lower()}.{ln.lower()}{i}@email.com",
            phone=f"06{random.randint(10000000, 99999999)}",
            city=city,
            postal_code=cp,
            address=f"{random.randint(1, 200)} rue {random.choice(['des Lilas', 'Victor Hugo', 'de la Paix', 'Pasteur'])}",
        )
        db.add(c)
        db.flush()
        customers.append(c)
        stats["clients"] += 1

    # Cases + documents
    cases = []
    for _i in range(30):
        customer = random.choice(customers)
        case = Case(
            tenant_id=tenant_id,
            customer_id=customer.id,
            status=random.choice(["draft", "documents_missing", "complet"]),
            source=random.choice(SOURCES),
            created_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=random.randint(0, 90)),
        )
        db.add(case)
        db.flush()
        cases.append(case)
        stats["cases"] += 1

        # Add some documents
        for dt in random.sample(DOC_TYPES, random.randint(0, len(DOC_TYPES))):
            db.add(
                Document(
                    tenant_id=tenant_id,
                    case_id=case.id,
                    type=dt,
                    filename=f"{dt}_{case.id}.pdf",
                    storage_key=f"demo/{dt}_{case.id}.pdf",
                )
            )

    # Devis
    devis_list = []
    existing_devis = db.query(Devis).count()
    devis_num = existing_devis + 1
    for case in random.sample(cases, min(15, len(cases))):
        lignes_data = random.sample(PRODUCTS, random.randint(2, 4))
        total_ht = sum(p[1] * random.randint(1, 2) for p in lignes_data)
        total_ttc = round(total_ht * 1.2, 2)
        tva = round(total_ttc - total_ht, 2)
        part_secu = round(random.uniform(30, 100), 2)
        part_mut = round(random.uniform(50, 200), 2)
        rac = round(max(total_ttc - part_secu - part_mut, 0), 2)
        status = random.choice(["brouillon", "envoye", "signe", "facture"])

        d = Devis(
            tenant_id=tenant_id,
            case_id=case.id,
            numero=f"DEV-{devis_num:05d}",
            status=status,
            montant_ht=total_ht,
            tva=tva,
            montant_ttc=total_ttc,
            part_secu=part_secu,
            part_mutuelle=part_mut,
            reste_a_charge=rac,
            created_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=random.randint(0, 60)),
        )
        db.add(d)
        db.flush()
        devis_list.append(d)
        devis_num += 1
        stats["devis"] += 1

        for name, price in lignes_data:
            qty = random.randint(1, 2)
            lht = price * qty
            lttc = round(lht * 1.2, 2)
            db.add(
                DevisLigne(
                    tenant_id=tenant_id,
                    devis_id=d.id,
                    designation=name,
                    quantite=qty,
                    prix_unitaire_ht=price,
                    taux_tva=20,
                    montant_ht=lht,
                    montant_ttc=lttc,
                )
            )

    # Factures from signed/facture devis
    factures_created = []
    existing_factures = db.query(Facture).count()
    fact_num = existing_factures + 1
    for d in [dv for dv in devis_list if dv.status in ("signe", "facture")]:
        f = Facture(
            tenant_id=tenant_id,
            case_id=d.case_id,
            devis_id=d.id,
            numero=f"F-2026-{fact_num:04d}",
            montant_ht=float(d.montant_ht),
            tva=float(d.tva),
            montant_ttc=float(d.montant_ttc),
            status="emise",
            created_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=random.randint(0, 45)),
        )
        db.add(f)
        db.flush()
        fact_num += 1
        stats["factures"] += 1

        # Payments
        paid_pct = random.choice([0, 0.5, 1.0])
        paid = round(float(d.montant_ttc) * paid_pct, 2)
        status_pay = "paid" if paid_pct == 1 else ("partial" if paid_pct > 0 else "pending")
        factures_created.append(f)
        p = Payment(
            tenant_id=tenant_id,
            case_id=d.case_id,
            facture_id=f.id,
            payer_type=random.choice(["client", "mutuelle", "secu"]),
            mode_paiement=random.choice(["cb", "virement", "cheque"]),
            amount_due=float(d.montant_ttc),
            amount_paid=paid,
            status=status_pay,
            created_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=random.randint(0, 30)),
        )
        db.add(p)
        stats["payments"] += 1

    # Interactions
    seed_interactions(db, tenant_id, customers)
    stats["interactions"] = 20

    # PEC Requests (from factures)
    seed_pec_requests(db, tenant_id, factures_created, orgs, stats)

    # Bank Transactions (mix rapprochees et non rapprochees)
    seed_bank_transactions(db, tenant_id, stats)

    # Marketing, Segments, Campaigns, Notifications, Reminders
    seed_marketing_and_notifications(db, tenant_id, customers, factures_created, stats)

    db.commit()
    return stats
