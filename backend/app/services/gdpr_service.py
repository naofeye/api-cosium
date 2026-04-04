"""Service RGPD — droit d'acces, portabilite, droit a l'oubli."""

import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.models import (
    Case,
    Customer,
    Devis,
    Document,
    Facture,
    Interaction,
    MarketingConsent,
    Payment,
)
from app.services import audit_service

logger = get_logger("gdpr_service")


def get_client_data(db: Session, tenant_id: int, client_id: int, user_id: int) -> dict:
    """Droit d'acces — retourne toutes les donnees du client."""
    customer = db.get(Customer, client_id)
    if not customer or customer.tenant_id != tenant_id:
        raise NotFoundError("client", client_id)
    if user_id:
        audit_service.log_action(db, tenant_id, user_id, "create", "gdpr_access", client_id)

    cases = db.scalars(select(Case).where(Case.customer_id == client_id, Case.tenant_id == tenant_id)).all()
    case_ids = [c.id for c in cases]

    data = {
        "informations_personnelles": {
            "id": customer.id,
            "prenom": customer.first_name,
            "nom": customer.last_name,
            "email": customer.email,
            "telephone": customer.phone,
            "date_naissance": str(customer.birth_date) if customer.birth_date else None,
            "adresse": customer.address,
            "ville": customer.city,
            "code_postal": customer.postal_code,
            "numero_secu": customer.social_security_number,
        },
        "dossiers": [{"id": c.id, "statut": c.status, "source": c.source} for c in cases],
    }

    if case_ids:
        documents = db.scalars(select(Document).where(Document.case_id.in_(case_ids))).all()
        data["documents"] = [{"id": d.id, "type": d.type, "filename": d.filename} for d in documents]

        devis_list = db.scalars(select(Devis).where(Devis.case_id.in_(case_ids))).all()
        data["devis"] = [{"id": d.id, "numero": d.numero, "montant_ttc": float(d.montant_ttc)} for d in devis_list]

        factures = db.scalars(select(Facture).where(Facture.case_id.in_(case_ids))).all()
        data["factures"] = [{"id": f.id, "numero": f.numero, "montant_ttc": float(f.montant_ttc)} for f in factures]

        payments = db.scalars(select(Payment).where(Payment.case_id.in_(case_ids))).all()
        data["paiements"] = [{"id": p.id, "montant_paye": float(p.amount_paid), "statut": p.status} for p in payments]

    consents = db.scalars(
        select(MarketingConsent).where(MarketingConsent.client_id == client_id, MarketingConsent.tenant_id == tenant_id)
    ).all()
    data["consentements_marketing"] = [
        {"canal": c.channel, "consenti": c.consented, "date": str(c.consented_at) if c.consented_at else None}
        for c in consents
    ]

    interactions = db.scalars(
        select(Interaction).where(Interaction.client_id == client_id, Interaction.tenant_id == tenant_id)
    ).all()
    data["interactions"] = [{"id": i.id, "type": i.type, "sujet": i.subject} for i in interactions]

    return data


def export_client_data(db: Session, tenant_id: int, client_id: int, user_id: int) -> bytes:
    """Portabilite — export JSON de toutes les donnees."""
    data = get_client_data(db, tenant_id, client_id, user_id)

    if user_id:
        audit_service.log_action(db, tenant_id, user_id, "create", "gdpr_export", client_id)

    logger.info("gdpr_export", tenant_id=tenant_id, client_id=client_id)
    return json.dumps(data, ensure_ascii=False, indent=2, default=str).encode("utf-8")


def anonymize_client(db: Session, tenant_id: int, client_id: int, user_id: int) -> dict:
    """Droit a l'oubli — anonymise les donnees personnelles."""
    customer = db.get(Customer, client_id)
    if not customer or customer.tenant_id != tenant_id:
        raise NotFoundError("client", client_id)

    old_name = f"{customer.first_name} {customer.last_name}"
    customer.first_name = "ANONYMISE"
    customer.last_name = f"CLIENT-{client_id}"
    customer.email = None
    customer.phone = None
    customer.birth_date = None
    customer.address = None
    customer.city = None
    customer.postal_code = None
    customer.social_security_number = None
    customer.notes = None
    customer.updated_at = datetime.now(UTC).replace(tzinfo=None)

    # Anonymiser les consentements
    consents = db.scalars(
        select(MarketingConsent).where(MarketingConsent.client_id == client_id, MarketingConsent.tenant_id == tenant_id)
    ).all()
    for c in consents:
        c.consented = False
        c.revoked_at = datetime.now(UTC).replace(tzinfo=None)

    db.commit()

    if user_id:
        audit_service.log_action(
            db, tenant_id, user_id, "delete", "gdpr_anonymize", client_id, old_value={"name": old_name}
        )

    logger.info("gdpr_anonymized", tenant_id=tenant_id, client_id=client_id)
    return {"client_id": client_id, "status": "anonymized"}
