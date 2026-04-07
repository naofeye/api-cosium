"""Service vue client 360 — facade/orchestrateur.

Delegates to:
- client_360_documents: prescriptions, equipment, calendar, OCR, tags
- client_360_finance: invoices, payments, balance, aging
"""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.domain.schemas.client_360 import (
    Client360Response,
    CosiumDataBundle,
)
from app.domain.schemas.client_mutuelle import ClientMutuelleResponse
from app.domain.schemas.interactions import InteractionResponse
from app.models import (
    Case,
    Customer,
    Interaction,
    MarketingConsent,
)
from app.repositories import client_mutuelle_repo, client_repo
from app.services.client_360_documents import (
    build_calendar_events,
    build_correction_actuelle,
    build_cosium_payments,
    build_equipments,
    build_ocr_data,
    build_prescriptions,
    get_customer_tags,
    get_last_visit_date,
)
from app.services.client_360_finance import (
    aggregate_case_financials,
    build_financial_summary,
    build_prescription_warning,
    compute_total_ca_cosium,
    fetch_cosium_invoices,
)

logger = get_logger("client_360_service")


def _build_cosium_data(
    db: Session,
    tenant_id: int,
    client_id: int,
    customer: Customer,
    cosium_invoices_raw: list,
) -> CosiumDataBundle:
    """Build the Cosium data bundle for a client."""
    client_full_name = f"{customer.last_name} {customer.first_name}".strip()
    cosium_id = getattr(customer, "cosium_id", None)

    prescriptions, prescriptions_raw = build_prescriptions(
        db, tenant_id, client_id, cosium_id
    )
    correction_actuelle = build_correction_actuelle(prescriptions_raw)
    equipments = build_equipments(prescriptions_raw)

    invoice_cosium_ids = [ci.cosium_id for ci in cosium_invoices_raw]
    cosium_payments = build_cosium_payments(db, tenant_id, invoice_cosium_ids)

    calendar_events, calendar_raw = build_calendar_events(
        db, tenant_id, client_full_name, cosium_id
    )

    total_ca_cosium = compute_total_ca_cosium(cosium_invoices_raw)
    last_visit_date = get_last_visit_date(calendar_raw, cosium_invoices_raw)
    customer_tags = get_customer_tags(db, tenant_id, cosium_id)

    # Client mutuelles
    mutuelle_rows = client_mutuelle_repo.get_by_customer(db, client_id, tenant_id)
    mutuelles = [ClientMutuelleResponse.model_validate(m) for m in mutuelle_rows]

    ocr_data = build_ocr_data(db, tenant_id, client_id, cosium_id, prescriptions_raw)

    return CosiumDataBundle(
        prescriptions=prescriptions,
        cosium_payments=cosium_payments,
        calendar_events=calendar_events,
        equipments=equipments,
        correction_actuelle=correction_actuelle,
        total_ca_cosium=round(total_ca_cosium, 2),
        last_visit_date=last_visit_date,
        customer_tags=customer_tags,
        mutuelles=mutuelles,
        ocr_data=ocr_data,
    )


def get_client_360(db: Session, tenant_id: int, client_id: int) -> Client360Response:
    """Build the full 360 view for a client."""
    customer = client_repo.get_by_id(db, client_id, tenant_id)
    if not customer:
        raise NotFoundError("client", client_id)

    cases = db.scalars(
        select(Case)
        .where(Case.customer_id == client_id, Case.tenant_id == tenant_id)
        .options(
            selectinload(Case.documents),
            selectinload(Case.devis),
            selectinload(Case.factures),
            selectinload(Case.payments),
            selectinload(Case.pec_requests),
        )
    ).all()

    # Documents from cases
    documents = []
    for case in cases:
        for d in case.documents:
            documents.append(
                {"id": d.id, "type": d.type, "filename": d.filename, "uploaded_at": str(d.uploaded_at)}
            )

    # Dossiers summary
    dossiers = [
        {"id": c.id, "statut": c.status, "source": c.source, "created_at": str(c.created_at)}
        for c in cases
    ]

    # Financial aggregation
    fin = aggregate_case_financials(list(cases))

    # Consents
    consents = db.scalars(
        select(MarketingConsent).where(
            MarketingConsent.client_id == client_id,
            MarketingConsent.tenant_id == tenant_id,
        )
    ).all()
    consentements = [{"canal": c.channel, "consenti": c.consented} for c in consents]

    # Interactions
    interactions = db.scalars(
        select(Interaction)
        .where(Interaction.client_id == client_id, Interaction.tenant_id == tenant_id)
        .order_by(Interaction.created_at.desc())
        .limit(50)
    ).all()

    # Cosium invoices
    client_full_name = f"{customer.last_name} {customer.first_name}".strip()
    cosium_invoices_list, cosium_invoices_raw = fetch_cosium_invoices(
        db, tenant_id, client_id, client_full_name
    )

    # Cosium data bundle
    cosium_data = _build_cosium_data(
        db, tenant_id, client_id, customer, cosium_invoices_raw
    )

    # Financial summary
    resume_financier = build_financial_summary(fin["total_facture"], fin["total_paye"])
    reste_du = resume_financier.reste_du

    # Prescription warning
    prescription_warning = build_prescription_warning(cosium_data.prescriptions)

    customer_cosium_id = getattr(customer, "cosium_id", None)

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
        cosium_id=str(customer_cosium_id) if customer_cosium_id else None,
        created_at=customer.created_at,
        dossiers=dossiers,
        devis=fin["devis"],
        factures=fin["factures"],
        paiements=fin["paiements"],
        documents=documents,
        pec=fin["pec"],
        consentements=consentements,
        interactions=[InteractionResponse.model_validate(i) for i in interactions],
        cosium_invoices=cosium_invoices_list,
        cosium_data=cosium_data,
        resume_financier=resume_financier,
        prescription_warning=prescription_warning,
    )


def get_client_cosium_data(db: Session, tenant_id: int, client_id: int) -> CosiumDataBundle:
    """Return all Cosium data for a client in one call."""
    customer = client_repo.get_by_id(db, client_id, tenant_id)
    if not customer:
        raise NotFoundError("client", client_id)

    client_full_name = f"{customer.last_name} {customer.first_name}".strip()
    _, cosium_invoices_raw = fetch_cosium_invoices(
        db, tenant_id, client_id, client_full_name
    )

    return _build_cosium_data(db, tenant_id, client_id, customer, cosium_invoices_raw)
