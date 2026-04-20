"""Data constants and seed helpers for demo data.

Extracted from seed_demo.py to keep each file under 300 lines.
"""

import random
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

FIRST_NAMES = [
    "Marie", "Jean", "Sophie", "Pierre", "Camille", "Thomas", "Julie",
    "Nicolas", "Isabelle", "Laurent", "Claire", "Francois", "Nathalie",
    "Olivier", "Catherine", "Philippe", "Sandrine", "Patrick", "Valerie",
    "Christophe",
]
LAST_NAMES = [
    "Dupont", "Martin", "Bernard", "Petit", "Robert", "Richard", "Durand",
    "Moreau", "Simon", "Laurent", "Michel", "Leroy", "Roux", "David",
    "Bertrand", "Morel", "Fournier", "Girard", "Andre", "Mercier",
]
CITIES = [
    ("Paris", "75001"), ("Lyon", "69001"), ("Marseille", "13001"),
    ("Bordeaux", "33000"), ("Toulouse", "31000"), ("Nantes", "44000"),
    ("Strasbourg", "67000"), ("Lille", "59000"),
]
SOURCES = ["Cosium", "telephone", "email", "visite", "web"]
DOC_TYPES = ["ordonnance", "devis_signe", "attestation_mutuelle", "consentement_rgpd"]
PRODUCTS = [
    ("Monture Ray-Ban Aviator", 180), ("Monture Oakley Sport", 150),
    ("Monture Gucci Luxe", 320), ("Verres progressifs", 120),
    ("Verres unifocaux", 60), ("Traitement anti-reflet", 35),
    ("Traitement anti-lumiere bleue", 45), ("Etui premium", 25),
]


def seed_interactions(db: Session, tenant_id: int, customers: list) -> None:
    """Seed interaction records for a sample of customers."""
    from app.models import Interaction

    for customer in random.sample(customers, min(20, len(customers))):
        for _ in range(random.randint(1, 3)):
            db.add(
                Interaction(
                    tenant_id=tenant_id,
                    client_id=customer.id,
                    type=random.choice(["appel", "email", "visite", "note"]),
                    direction=random.choice(["entrant", "sortant", "interne"]),
                    subject=random.choice([
                        "Demande de renseignement", "Appel de suivi",
                        "Relance equipement", "Visite renouvellement",
                        "Note interne", "Email de confirmation",
                    ]),
                    content="Interaction de demo pour la presentation.",
                    created_by=1,
                    created_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=random.randint(0, 60)),
                )
            )


def seed_pec_requests(db: Session, tenant_id: int, factures: list, orgs: list, stats: dict) -> None:
    """Seed PEC (prise en charge) requests from factures."""
    from app.models import PecRequest

    for f in random.sample(factures, min(8, len(factures))):
        org = random.choice(orgs)
        pec_status = random.choice(["soumise", "en_attente", "acceptee", "refusee", "partielle"])
        montant_dem = round(float(f.montant_ttc) * random.uniform(0.3, 0.8), 2)
        montant_acc = (
            round(montant_dem * random.uniform(0.5, 1.0), 2) if pec_status in ("acceptee", "partielle") else None
        )
        db.add(PecRequest(
            tenant_id=tenant_id, case_id=f.case_id, organization_id=org.id,
            facture_id=f.id, montant_demande=montant_dem, montant_accorde=montant_acc,
            status=pec_status,
            created_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=random.randint(0, 40)),
        ))
        stats["pec"] += 1


def seed_bank_transactions(db: Session, tenant_id: int, stats: dict) -> None:
    """Seed bank transactions (mix reconciled and not)."""
    from app.models import BankTransaction

    labels = [
        "VIR MUTUELLE MGEN", "CB PAIEMENT CLIENT", "VIR CPAM REMB",
        "CHQ 1234567", "PRLV FOURNISSEUR", "VIR CLIENT DUPONT",
        "CB REGLEMENT FACTURE", "VIR HARMONIE MUTUELLE",
    ]
    for _ in range(25):
        db.add(BankTransaction(
            tenant_id=tenant_id,
            date=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=random.randint(0, 60)),
            libelle=random.choice(labels),
            montant=round(random.uniform(50, 800), 2),
            reference=f"REF-{random.randint(100000, 999999)}",
            source_file="releve_demo.csv",
            reconciled=random.random() > 0.4,
        ))
        stats["bank_transactions"] += 1


def seed_marketing_and_notifications(
    db: Session, tenant_id: int, customers: list, factures: list, stats: dict,
) -> None:
    """Seed marketing consents, segments, campaigns, notifications, and reminders."""
    from app.models import Campaign, MarketingConsent, Notification, Reminder, Segment

    for customer in random.sample(customers, min(30, len(customers))):
        for channel in random.sample(["email", "sms"], random.randint(1, 2)):
            db.add(MarketingConsent(
                tenant_id=tenant_id, client_id=customer.id, channel=channel,
                consented=random.random() > 0.2,
                consented_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=random.randint(0, 180)),
                source="inscription",
            ))

    seg = Segment(
        tenant_id=tenant_id, name="Clients fideles",
        description="Clients avec au moins 2 dossiers", rules_json='{"min_cases": 2}',
    )
    db.add(seg)
    db.flush()

    db.add(Campaign(
        tenant_id=tenant_id, name="Renouvellement lunettes 2026", segment_id=seg.id,
        channel="email", subject="Vos lunettes ont plus de 2 ans ?",
        template="Bonjour {{client_name}}, il est peut-etre temps de renouveler vos lunettes. Prenez rendez-vous !",
        status="sent",
        sent_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=15),
        created_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=20),
    ))
    stats["campaigns"] += 1

    for _ in range(10):
        db.add(Notification(
            tenant_id=tenant_id, user_id=1,
            type=random.choice(["info", "warning", "action", "success"]),
            title=random.choice([
                "Nouveau dossier cree", "Paiement recu", "PEC en attente",
                "Relance envoyee", "Devis signe", "Document ajoute",
            ]),
            message="Notification de demonstration pour la presentation.",
            is_read=random.random() > 0.5,
            created_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=random.randint(0, 14)),
        ))

    for f in random.sample(factures, min(5, len(factures))):
        db.add(Reminder(
            tenant_id=tenant_id, target_type="client", target_id=f.case_id,
            facture_id=f.id, channel=random.choice(["email", "telephone"]),
            status=random.choice(["scheduled", "sent", "responded"]),
            content=f"Relance pour la facture {f.numero}",
            scheduled_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=random.randint(0, 20)),
            sent_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=random.randint(0, 15)),
            created_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=random.randint(0, 20)),
        ))
