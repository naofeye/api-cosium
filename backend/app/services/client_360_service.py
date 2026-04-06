"""Service vue client 360 — agregation complete."""

import json

from sqlalchemy import func as sa_func
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.domain.schemas.client_360 import (
    Client360Response,
    CorrectionActuelle,
    CosiumCalendarSummary,
    CosiumDataBundle,
    CosiumInvoiceSummary,
    CosiumPaymentSummary,
    CosiumPrescriptionSummary,
    EquipmentItem,
    FinancialSummary,
    PrescriptionWarning,
)
from app.domain.schemas.client_mutuelle import ClientMutuelleResponse
from app.domain.schemas.interactions import InteractionResponse
from app.models import (
    Case,
    Customer,
    Interaction,
    MarketingConsent,
)
from app.models.client_mutuelle import ClientMutuelle
from app.models.cosium_data import CosiumInvoice, CosiumPayment, CosiumPrescription
from app.models.cosium_reference import CosiumCalendarEvent, CosiumCustomerTag

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

    # --- Prescriptions ---
    rx_query = select(CosiumPrescription).where(
        CosiumPrescription.tenant_id == tenant_id,
    )
    if cosium_id:
        rx_query = rx_query.where(
            (CosiumPrescription.customer_id == client_id)
            | (CosiumPrescription.customer_cosium_id == int(cosium_id))
        )
    else:
        rx_query = rx_query.where(CosiumPrescription.customer_id == client_id)

    prescriptions_raw = db.scalars(
        rx_query.order_by(CosiumPrescription.file_date.desc().nullslast()).limit(20)
    ).all()

    prescriptions = [
        CosiumPrescriptionSummary(
            id=rx.id,
            cosium_id=rx.cosium_id,
            prescription_date=rx.prescription_date,
            prescriber_name=rx.prescriber_name,
            sphere_right=rx.sphere_right,
            cylinder_right=rx.cylinder_right,
            axis_right=rx.axis_right,
            addition_right=rx.addition_right,
            sphere_left=rx.sphere_left,
            cylinder_left=rx.cylinder_left,
            axis_left=rx.axis_left,
            addition_left=rx.addition_left,
            spectacles_json=rx.spectacles_json,
        )
        for rx in prescriptions_raw
    ]

    # --- Correction actuelle (latest prescription) ---
    correction_actuelle = None
    if prescriptions_raw:
        latest = prescriptions_raw[0]
        correction_actuelle = CorrectionActuelle(
            prescription_date=latest.prescription_date,
            prescriber_name=latest.prescriber_name,
            sphere_right=latest.sphere_right,
            cylinder_right=latest.cylinder_right,
            axis_right=latest.axis_right,
            addition_right=latest.addition_right,
            sphere_left=latest.sphere_left,
            cylinder_left=latest.cylinder_left,
            axis_left=latest.axis_left,
            addition_left=latest.addition_left,
        )

    # --- Equipment from spectacles_json ---
    equipments: list[EquipmentItem] = []
    for rx in prescriptions_raw:
        if not rx.spectacles_json:
            continue
        try:
            specs = json.loads(rx.spectacles_json)
            if isinstance(specs, list):
                for spec in specs:
                    equipments.append(
                        EquipmentItem(
                            prescription_id=rx.id,
                            prescription_date=rx.prescription_date,
                            label=spec.get("label", spec.get("name", "")),
                            brand=spec.get("brand", spec.get("marque", "")),
                            type=spec.get("type", spec.get("famille", "")),
                        )
                    )
            elif isinstance(specs, dict):
                equipments.append(
                    EquipmentItem(
                        prescription_id=rx.id,
                        prescription_date=rx.prescription_date,
                        label=specs.get("label", specs.get("name", "")),
                        brand=specs.get("brand", specs.get("marque", "")),
                        type=specs.get("type", specs.get("famille", "")),
                    )
                )
        except (json.JSONDecodeError, TypeError) as exc:
            logger.warning(
                "malformed_spectacles_json",
                prescription_id=rx.id,
                error=str(exc),
            )

    # --- Cosium Payments (join via invoice cosium_id) ---
    invoice_cosium_ids = [ci.cosium_id for ci in cosium_invoices_raw]
    cosium_payments: list[CosiumPaymentSummary] = []
    if invoice_cosium_ids:
        pay_query = (
            select(CosiumPayment)
            .where(
                CosiumPayment.tenant_id == tenant_id,
                CosiumPayment.invoice_cosium_id.in_(invoice_cosium_ids),
            )
            .order_by(CosiumPayment.due_date.desc().nullslast())
            .limit(100)
        )
        payments_raw = db.scalars(pay_query).all()
        cosium_payments = [
            CosiumPaymentSummary(
                id=p.id,
                cosium_id=p.cosium_id,
                amount=p.amount,
                type=p.type,
                due_date=str(p.due_date) if p.due_date else None,
                issuer_name=p.issuer_name,
                bank=p.bank,
                site_name=p.site_name,
                payment_number=p.payment_number,
                invoice_cosium_id=p.invoice_cosium_id,
            )
            for p in payments_raw
        ]

    # --- Calendar Events (fuzzy match on customer_fullname or customer_number) ---
    cal_query = select(CosiumCalendarEvent).where(
        CosiumCalendarEvent.tenant_id == tenant_id,
    )
    name_upper = client_full_name.upper()
    if cosium_id:
        cal_query = cal_query.where(
            (sa_func.upper(CosiumCalendarEvent.customer_fullname).contains(name_upper))
            | (CosiumCalendarEvent.customer_number == str(cosium_id))
        )
    else:
        cal_query = cal_query.where(
            sa_func.upper(CosiumCalendarEvent.customer_fullname).contains(name_upper)
        )
    cal_query = cal_query.order_by(
        CosiumCalendarEvent.start_date.desc().nullslast()
    ).limit(30)
    calendar_raw = db.scalars(cal_query).all()

    calendar_events = [
        CosiumCalendarSummary(
            id=ev.id,
            cosium_id=ev.cosium_id,
            start_date=str(ev.start_date) if ev.start_date else None,
            end_date=str(ev.end_date) if ev.end_date else None,
            subject=ev.subject,
            category_name=ev.category_name,
            category_color=ev.category_color,
            status=ev.status,
            canceled=ev.canceled,
            missed=ev.missed,
            observation=ev.observation,
            site_name=ev.site_name,
        )
        for ev in calendar_raw
    ]

    # --- Total CA Cosium ---
    total_ca_cosium = sum(
        ci.total_ti for ci in cosium_invoices_raw
        if ci.type in ("INVOICE", "CREDIT_NOTE")
    )

    # --- Last visit date ---
    last_visit_date: str | None = None
    for ev in calendar_raw:
        if not ev.canceled and ev.start_date:
            last_visit_date = str(ev.start_date)
            break
    if not last_visit_date and cosium_invoices_raw:
        for ci in cosium_invoices_raw:
            if ci.invoice_date:
                last_visit_date = str(ci.invoice_date)
                break

    # --- Customer tags ---
    customer_tags: list[str] = []
    if cosium_id:
        tag_rows = db.scalars(
            select(CosiumCustomerTag.tag_code).where(
                CosiumCustomerTag.tenant_id == tenant_id,
                CosiumCustomerTag.customer_cosium_id == str(cosium_id),
            )
        ).all()
        customer_tags = list(tag_rows)

    # --- Client mutuelles ---
    mutuelle_rows = db.scalars(
        select(ClientMutuelle).where(
            ClientMutuelle.tenant_id == tenant_id,
            ClientMutuelle.customer_id == client_id,
        ).order_by(ClientMutuelle.active.desc(), ClientMutuelle.created_at.desc())
    ).all()
    mutuelles = [ClientMutuelleResponse.model_validate(m) for m in mutuelle_rows]

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
    )


def get_client_360(db: Session, tenant_id: int, client_id: int) -> Client360Response:
    """Build the full 360 view for a client."""
    customer = db.get(Customer, client_id)
    if not customer or customer.tenant_id != tenant_id:
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

    dossiers = [
        {"id": c.id, "statut": c.status, "source": c.source, "created_at": str(c.created_at)}
        for c in cases
    ]
    documents = []
    devis_list = []
    factures = []
    paiements = []
    pec_list = []
    total_facture = 0.0
    total_paye = 0.0

    for case in cases:
        for d in case.documents:
            documents.append(
                {"id": d.id, "type": d.type, "filename": d.filename, "uploaded_at": str(d.uploaded_at)}
            )

        for d in case.devis:
            devis_list.append(
                {
                    "id": d.id,
                    "numero": d.numero,
                    "statut": d.status,
                    "montant_ttc": float(d.montant_ttc),
                    "reste_a_charge": float(d.reste_a_charge),
                }
            )

        for f in case.factures:
            factures.append(
                {
                    "id": f.id,
                    "numero": f.numero,
                    "statut": f.status,
                    "montant_ttc": float(f.montant_ttc),
                    "date_emission": str(f.date_emission),
                }
            )
            total_facture += float(f.montant_ttc)

        for p in case.payments:
            paiements.append(
                {
                    "id": p.id,
                    "payeur": p.payer_type,
                    "mode": p.mode_paiement,
                    "montant_du": float(p.amount_due),
                    "montant_paye": float(p.amount_paid),
                    "statut": p.status,
                }
            )
            total_paye += float(p.amount_paid)

        for p in case.pec_requests:
            pec_list.append(
                {
                    "id": p.id,
                    "statut": p.status,
                    "montant_demande": float(p.montant_demande),
                    "montant_accorde": float(p.montant_accorde) if p.montant_accorde else None,
                }
            )

    consents = db.scalars(
        select(MarketingConsent).where(
            MarketingConsent.client_id == client_id,
            MarketingConsent.tenant_id == tenant_id,
        )
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
    cosium_invoices_raw = db.scalars(
        cosium_inv_query.where(
            (CosiumInvoice.customer_id == client_id)
            | (sa_func.upper(CosiumInvoice.customer_name).contains(client_full_name.upper()))
        )
        .order_by(CosiumInvoice.invoice_date.desc())
        .limit(50)
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

    # Build Cosium data bundle
    cosium_data = _build_cosium_data(
        db, tenant_id, client_id, customer, cosium_invoices_raw
    )

    reste_du = round(max(total_facture - total_paye, 0), 2)
    taux = round(total_paye / total_facture * 100, 1) if total_facture > 0 else 0

    customer_cosium_id = getattr(customer, "cosium_id", None)

    # --- Prescription warning (> 2 years) ---
    prescription_warning = None
    if cosium_data.prescriptions:
        latest_rx_date_str = cosium_data.prescriptions[0].prescription_date
        if latest_rx_date_str:
            try:
                from datetime import UTC, datetime

                latest_rx_date = datetime.strptime(latest_rx_date_str[:10], "%Y-%m-%d")
                days_since = (datetime.now(UTC).replace(tzinfo=None) - latest_rx_date).days
                if days_since > 730:
                    prescription_warning = PrescriptionWarning(
                        expired=True,
                        latest_date=latest_rx_date_str[:10],
                        days_since=days_since,
                        message=(
                            f"Ordonnance de plus de 2 ans "
                            f"(derniere : {latest_rx_date.strftime('%d/%m/%Y')}, "
                            f"il y a {days_since} jours). "
                            f"Pensez a contacter le client pour un renouvellement."
                        ),
                    )
            except (ValueError, TypeError):
                pass

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
        devis=devis_list,
        factures=factures,
        paiements=paiements,
        documents=documents,
        pec=pec_list,
        consentements=consentements,
        interactions=[InteractionResponse.model_validate(i) for i in interactions],
        cosium_invoices=cosium_invoices_list,
        cosium_data=cosium_data,
        resume_financier=FinancialSummary(
            total_facture=round(total_facture, 2),
            total_paye=round(total_paye, 2),
            reste_du=reste_du,
            taux_recouvrement=taux,
        ),
        prescription_warning=prescription_warning,
    )


def get_client_cosium_data(db: Session, tenant_id: int, client_id: int) -> CosiumDataBundle:
    """Return all Cosium data for a client in one call."""
    customer = db.get(Customer, client_id)
    if not customer or customer.tenant_id != tenant_id:
        raise NotFoundError("client", client_id)

    client_full_name = f"{customer.last_name} {customer.first_name}".strip()
    cosium_inv_query = select(CosiumInvoice).where(
        CosiumInvoice.tenant_id == tenant_id,
    )
    cosium_invoices_raw = db.scalars(
        cosium_inv_query.where(
            (CosiumInvoice.customer_id == client_id)
            | (sa_func.upper(CosiumInvoice.customer_name).contains(client_full_name.upper()))
        )
        .order_by(CosiumInvoice.invoice_date.desc())
        .limit(50)
    ).all()

    return _build_cosium_data(db, tenant_id, client_id, customer, cosium_invoices_raw)
