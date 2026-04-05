"""Service vue client 360 — agregation complete."""

from sqlalchemy import func as sa_func
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.domain.schemas.client_360 import Client360Response, CosiumInvoiceSummary, FinancialSummary
from app.domain.schemas.interactions import InteractionResponse
from app.models import (
    Case,
    Customer,
    Devis,
    Document,
    Facture,
    Interaction,
    MarketingConsent,
    Payment,
    PecRequest,
)
from app.models.cosium_data import CosiumInvoice

logger = get_logger("client_360_service")


def get_client_360(db: Session, tenant_id: int, client_id: int) -> Client360Response:
    customer = db.get(Customer, client_id)
    if not customer or customer.tenant_id != tenant_id:
        raise NotFoundError("client", client_id)

    cases = db.scalars(select(Case).where(Case.customer_id == client_id, Case.tenant_id == tenant_id)).all()
    case_ids = [c.id for c in cases]

    dossiers = [{"id": c.id, "statut": c.status, "source": c.source, "created_at": str(c.created_at)} for c in cases]
    documents = []
    devis_list = []
    factures = []
    paiements = []
    pec_list = []
    total_facture = 0.0
    total_paye = 0.0

    if case_ids:
        docs = db.scalars(select(Document).where(Document.case_id.in_(case_ids))).all()
        documents = [
            {"id": d.id, "type": d.type, "filename": d.filename, "uploaded_at": str(d.uploaded_at)} for d in docs
        ]

        devis = db.scalars(select(Devis).where(Devis.case_id.in_(case_ids))).all()
        devis_list = [
            {
                "id": d.id,
                "numero": d.numero,
                "statut": d.status,
                "montant_ttc": float(d.montant_ttc),
                "reste_a_charge": float(d.reste_a_charge),
            }
            for d in devis
        ]

        facts = db.scalars(select(Facture).where(Facture.case_id.in_(case_ids))).all()
        factures = [
            {
                "id": f.id,
                "numero": f.numero,
                "statut": f.status,
                "montant_ttc": float(f.montant_ttc),
                "date_emission": str(f.date_emission),
            }
            for f in facts
        ]
        total_facture = sum(float(f.montant_ttc) for f in facts)

        pays = db.scalars(select(Payment).where(Payment.case_id.in_(case_ids))).all()
        paiements = [
            {
                "id": p.id,
                "payeur": p.payer_type,
                "mode": p.mode_paiement,
                "montant_du": float(p.amount_due),
                "montant_paye": float(p.amount_paid),
                "statut": p.status,
            }
            for p in pays
        ]
        total_paye = sum(float(p.amount_paid) for p in pays)

        pecs = db.scalars(select(PecRequest).where(PecRequest.case_id.in_(case_ids))).all()
        pec_list = [
            {
                "id": p.id,
                "statut": p.status,
                "montant_demande": float(p.montant_demande),
                "montant_accorde": float(p.montant_accorde) if p.montant_accorde else None,
            }
            for p in pecs
        ]

    consents = db.scalars(
        select(MarketingConsent).where(MarketingConsent.client_id == client_id, MarketingConsent.tenant_id == tenant_id)
    ).all()
    consentements = [{"canal": c.channel, "consenti": c.consented} for c in consents]

    interactions = db.scalars(
        select(Interaction)
        .where(Interaction.client_id == client_id, Interaction.tenant_id == tenant_id)
        .order_by(Interaction.created_at.desc())
        .limit(50)
    ).all()

    # Cosium invoices: match by customer_id or by customer_name (ILIKE)
    client_full_name = f"{customer.last_name} {customer.first_name}".strip()
    cosium_inv_query = select(CosiumInvoice).where(
        CosiumInvoice.tenant_id == tenant_id,
    )
    # Match by FK or by name pattern
    cosium_invoices_raw = db.scalars(
        cosium_inv_query.where(
            (CosiumInvoice.customer_id == client_id)
            | (sa_func.upper(CosiumInvoice.customer_name).contains(client_full_name.upper()))
        )
        .order_by(CosiumInvoice.invoice_date.desc())
        .limit(100)
    ).all()

    cosium_invoices_list = [
        CosiumInvoiceSummary(
            cosium_id=ci.cosium_id,
            invoice_number=ci.invoice_number,
            invoice_date=str(ci.invoice_date) if ci.invoice_date else None,
            type=ci.type,
            total_ti=ci.total_ti,
            outstanding_balance=ci.outstanding_balance,
            share_social_security=ci.share_social_security,
            share_private_insurance=ci.share_private_insurance,
            settled=ci.settled,
        )
        for ci in cosium_invoices_raw
    ]

    reste_du = round(max(total_facture - total_paye, 0), 2)
    taux = round(total_paye / total_facture * 100, 1) if total_facture > 0 else 0

    return Client360Response(
        id=customer.id,
        first_name=customer.first_name,
        last_name=customer.last_name,
        email=customer.email,
        phone=customer.phone,
        birth_date=str(customer.birth_date) if customer.birth_date else None,
        address=customer.address,
        city=customer.city,
        postal_code=customer.postal_code,
        social_security_number=customer.social_security_number,
        avatar_url=f"/api/v1/clients/{customer.id}/avatar" if customer.avatar_url else None,
        created_at=customer.created_at,
        dossiers=dossiers,
        devis=devis_list,
        factures=factures,
        paiements=paiements,
        documents=documents,
        pec=pec_list,
        consentements=consentements,
        interactions=[InteractionResponse.model_validate(i) for i in interactions],
        cosium_invoices=cosium_invoices_list,
        resume_financier=FinancialSummary(
            total_facture=round(total_facture, 2),
            total_paye=round(total_paye, 2),
            reste_du=reste_du,
            taux_recouvrement=taux,
        ),
    )
