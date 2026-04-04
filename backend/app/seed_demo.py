"""Seed de donnees de demo enrichies pour presentations.

Usage: docker compose exec api python -c "from app.seed_demo import seed_demo_data; from app.db.session import SessionLocal; seed_demo_data(SessionLocal())"
"""

import random
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import (
    BankTransaction,
    Campaign,
    Case,
    Customer,
    Devis,
    DevisLigne,
    Document,
    Facture,
    Interaction,
    MarketingConsent,
    Notification,
    PayerOrganization,
    Payment,
    PecRequest,
    Reminder,
    Segment,
    Tenant,
)

FIRST_NAMES = [
    "Marie",
    "Jean",
    "Sophie",
    "Pierre",
    "Camille",
    "Thomas",
    "Julie",
    "Nicolas",
    "Isabelle",
    "Laurent",
    "Claire",
    "Francois",
    "Nathalie",
    "Olivier",
    "Catherine",
    "Philippe",
    "Sandrine",
    "Patrick",
    "Valerie",
    "Christophe",
]
LAST_NAMES = [
    "Dupont",
    "Martin",
    "Bernard",
    "Petit",
    "Robert",
    "Richard",
    "Durand",
    "Moreau",
    "Simon",
    "Laurent",
    "Michel",
    "Leroy",
    "Roux",
    "David",
    "Bertrand",
    "Morel",
    "Fournier",
    "Girard",
    "Andre",
    "Mercier",
]
CITIES = [
    ("Paris", "75001"),
    ("Lyon", "69001"),
    ("Marseille", "13001"),
    ("Bordeaux", "33000"),
    ("Toulouse", "31000"),
    ("Nantes", "44000"),
    ("Strasbourg", "67000"),
    ("Lille", "59000"),
]
SOURCES = ["Cosium", "telephone", "email", "visite", "web"]
DOC_TYPES = ["ordonnance", "devis_signe", "attestation_mutuelle", "consentement_rgpd"]
PRODUCTS = [
    ("Monture Ray-Ban Aviator", 180),
    ("Monture Oakley Sport", 150),
    ("Monture Gucci Luxe", 320),
    ("Verres progressifs", 120),
    ("Verres unifocaux", 60),
    ("Traitement anti-reflet", 35),
    ("Traitement anti-lumiere bleue", 45),
    ("Etui premium", 25),
]


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
    for customer in random.sample(customers, 20):
        for _ in range(random.randint(1, 3)):
            db.add(
                Interaction(
                    tenant_id=tenant_id,
                    client_id=customer.id,
                    type=random.choice(["appel", "email", "visite", "note"]),
                    direction=random.choice(["entrant", "sortant", "interne"]),
                    subject=random.choice(
                        [
                            "Demande de renseignement",
                            "Appel de suivi",
                            "Relance equipement",
                            "Visite renouvellement",
                            "Note interne",
                            "Email de confirmation",
                        ]
                    ),
                    content="Interaction de demo pour la presentation.",
                    created_by=1,
                    created_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=random.randint(0, 60)),
                )
            )

    # PEC Requests (from factures)
    for f in random.sample(factures_created, min(8, len(factures_created))):
        org = random.choice(orgs)
        pec_status = random.choice(["soumise", "en_attente", "acceptee", "refusee", "partielle"])
        montant_dem = round(float(f.montant_ttc) * random.uniform(0.3, 0.8), 2)
        montant_acc = (
            round(montant_dem * random.uniform(0.5, 1.0), 2) if pec_status in ("acceptee", "partielle") else None
        )
        pec = PecRequest(
            tenant_id=tenant_id,
            case_id=f.case_id,
            organization_id=org.id,
            facture_id=f.id,
            montant_demande=montant_dem,
            montant_accorde=montant_acc,
            status=pec_status,
            created_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=random.randint(0, 40)),
        )
        db.add(pec)
        stats["pec"] += 1

    # Bank Transactions (mix rapprochees et non rapprochees)
    for _ in range(25):
        days_ago = random.randint(0, 60)
        montant = round(random.uniform(50, 800), 2)
        reconciled = random.random() > 0.4
        db.add(
            BankTransaction(
                tenant_id=tenant_id,
                date=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days_ago),
                libelle=random.choice(
                    [
                        "VIR MUTUELLE MGEN",
                        "CB PAIEMENT CLIENT",
                        "VIR CPAM REMB",
                        "CHQ 1234567",
                        "PRLV FOURNISSEUR",
                        "VIR CLIENT DUPONT",
                        "CB REGLEMENT FACTURE",
                        "VIR HARMONIE MUTUELLE",
                    ]
                ),
                montant=montant,
                reference=f"REF-{random.randint(100000, 999999)}",
                source_file="releve_demo.csv",
                reconciled=reconciled,
            )
        )
        stats["bank_transactions"] += 1

    # Marketing Consents
    for customer in random.sample(customers, min(30, len(customers))):
        for channel in random.sample(["email", "sms"], random.randint(1, 2)):
            db.add(
                MarketingConsent(
                    tenant_id=tenant_id,
                    client_id=customer.id,
                    channel=channel,
                    consented=random.random() > 0.2,
                    consented_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=random.randint(0, 180)),
                    source="inscription",
                )
            )

    # Segment + Campaign
    seg = Segment(
        tenant_id=tenant_id,
        name="Clients fideles",
        description="Clients avec au moins 2 dossiers",
        rules_json='{"min_cases": 2}',
    )
    db.add(seg)
    db.flush()

    camp = Campaign(
        tenant_id=tenant_id,
        name="Renouvellement lunettes 2026",
        segment_id=seg.id,
        channel="email",
        subject="Vos lunettes ont plus de 2 ans ?",
        template="Bonjour {{client_name}}, il est peut-etre temps de renouveler vos lunettes. Prenez rendez-vous !",
        status="sent",
        sent_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=15),
        created_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=20),
    )
    db.add(camp)
    stats["campaigns"] += 1

    # Notifications
    user_id = 1
    for _ in range(10):
        db.add(
            Notification(
                tenant_id=tenant_id,
                user_id=user_id,
                type=random.choice(["info", "warning", "action", "success"]),
                title=random.choice(
                    [
                        "Nouveau dossier cree",
                        "Paiement recu",
                        "PEC en attente",
                        "Relance envoyee",
                        "Devis signe",
                        "Document ajoute",
                    ]
                ),
                message="Notification de demonstration pour la presentation.",
                is_read=random.random() > 0.5,
                created_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=random.randint(0, 14)),
            )
        )

    # Reminders (from factures with pending payments)
    for f in random.sample(factures_created, min(5, len(factures_created))):
        db.add(
            Reminder(
                tenant_id=tenant_id,
                target_type="client",
                target_id=f.case_id,
                facture_id=f.id,
                channel=random.choice(["email", "telephone"]),
                status=random.choice(["scheduled", "sent", "responded"]),
                content=f"Relance pour la facture {f.numero}",
                scheduled_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=random.randint(0, 20)),
                sent_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=random.randint(0, 15)),
                created_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=random.randint(0, 20)),
            )
        )

    stats["interactions"] = 20  # from the loop above

    db.commit()
    return stats
