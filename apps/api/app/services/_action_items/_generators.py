"""Generators d'action items extraits de action_item_service.

6 generators independants, chacun query une source (cases, calendar,
cosium invoices, payments) et cree des action_items pending pour
l'utilisateur. Pattern : check existing pending entity_ids, ne cree
que les nouveaux, supprime les resolved.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Case, Customer, Document, DocumentType, Payment
from app.models.cosium_data import CosiumInvoice
from app.models.cosium_reference import CosiumCalendarEvent
from app.repositories import action_item_repo


def generate_incomplete_cases(db: Session, tenant_id: int, user_id: int) -> None:
    required_count = (
        db.scalar(select(func.count()).select_from(DocumentType).where(DocumentType.is_required.is_(True))) or 0
    )
    if required_count == 0:
        return

    required_codes = [
        code for (code,) in db.execute(select(DocumentType.code).where(DocumentType.is_required.is_(True))).all()
    ]

    cases = db.execute(
        select(Case.id, Customer.first_name, Customer.last_name)
        .join(Customer, Customer.id == Case.customer_id)
        .where(Case.tenant_id == tenant_id)
    ).all()
    if not cases:
        return

    case_ids = [c.id for c in cases]
    present_by_case: dict[int, int] = {
        row.case_id: int(row.cnt)
        for row in db.execute(
            select(
                Document.case_id,
                func.count(func.distinct(Document.type)).label("cnt"),
            )
            .where(
                Document.case_id.in_(case_ids),
                Document.tenant_id == tenant_id,
                Document.type.in_(required_codes),
            )
            .group_by(Document.case_id)
        ).all()
    }
    existing_ids = action_item_repo.list_pending_entity_ids(
        db, user_id=user_id, tenant_id=tenant_id, type="dossier_incomplet", entity_type="case"
    )

    for case_row in cases:
        present = present_by_case.get(case_row.id, 0)
        missing = required_count - present
        if missing > 0:
            if case_row.id not in existing_ids:
                action_item_repo.create(
                    db,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    type="dossier_incomplet",
                    title=f"Dossier incomplet -{case_row.first_name} {case_row.last_name}",
                    description=f"{missing} piece(s) obligatoire(s) manquante(s)",
                    entity_type="case",
                    entity_id=case_row.id,
                    priority="high" if missing >= 3 else "medium",
                )
        elif case_row.id in existing_ids:
            action_item_repo.delete_resolved(
                db,
                user_id=user_id,
                tenant_id=tenant_id,
                type="dossier_incomplet",
                entity_type="case",
                entity_id=case_row.id,
            )


def generate_upcoming_appointments(db: Session, tenant_id: int, user_id: int) -> None:
    """Alerte pour les RDV de demain (rappel client)."""
    now = datetime.now(UTC).replace(tzinfo=None)
    tomorrow_start = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    day_after = tomorrow_start + timedelta(days=1)

    events = db.execute(
        select(CosiumCalendarEvent.id, CosiumCalendarEvent.subject, CosiumCalendarEvent.start_date)
        .where(
            CosiumCalendarEvent.tenant_id == tenant_id,
            CosiumCalendarEvent.start_date >= tomorrow_start,
            CosiumCalendarEvent.start_date < day_after,
            CosiumCalendarEvent.canceled.is_(False),
        )
    ).all()
    if not events:
        return
    existing_ids = action_item_repo.list_pending_entity_ids(
        db, user_id=user_id, tenant_id=tenant_id, type="rdv_demain", entity_type="calendar_event"
    )

    for ev in events:
        if ev.id not in existing_ids:
            heure = ev.start_date.strftime("%H:%M") if ev.start_date else ""
            action_item_repo.create(
                db, tenant_id=tenant_id, user_id=user_id,
                type="rdv_demain",
                title=f"RDV demain {heure} - {ev.subject[:80]}",
                description=f"Rappel client recommande pour le RDV du {ev.start_date.strftime('%d/%m/%Y') if ev.start_date else ''}",
                entity_type="calendar_event", entity_id=ev.id,
                priority="medium",
            )


def generate_overdue_cosium_invoices(db: Session, tenant_id: int, user_id: int) -> None:
    """Alerte pour les factures Cosium impayees depuis plus de 30 jours."""
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=30)

    invoices = db.execute(
        select(CosiumInvoice.id, CosiumInvoice.invoice_number, CosiumInvoice.outstanding_balance, CosiumInvoice.invoice_date)
        .where(
            CosiumInvoice.tenant_id == tenant_id,
            CosiumInvoice.type == "INVOICE",
            CosiumInvoice.outstanding_balance > 0,
            CosiumInvoice.invoice_date < cutoff,
        )
        .limit(200)
    ).all()
    if not invoices:
        return
    existing_ids = action_item_repo.list_pending_entity_ids(
        db, user_id=user_id, tenant_id=tenant_id, type="impaye_cosium", entity_type="cosium_invoice"
    )

    for inv in invoices:
        if inv.id not in existing_ids:
            days_overdue = (datetime.now(UTC).replace(tzinfo=None) - inv.invoice_date).days if inv.invoice_date else 0
            priority = "high" if days_overdue > 90 else "medium"
            action_item_repo.create(
                db, tenant_id=tenant_id, user_id=user_id,
                type="impaye_cosium",
                title=f"Impaye {inv.invoice_number or '#' + str(inv.id)} - {float(inv.outstanding_balance):.2f} EUR",
                description=f"Facture en retard de {days_overdue} jours",
                entity_type="cosium_invoice", entity_id=inv.id,
                priority=priority,
            )


def generate_stale_quotes(db: Session, tenant_id: int, user_id: int) -> None:
    """Alerte pour les devis Cosium non transformes depuis plus de 15 jours."""
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=15)

    quotes = db.execute(
        select(CosiumInvoice.id, CosiumInvoice.invoice_number, CosiumInvoice.total_ti, CosiumInvoice.invoice_date)
        .where(
            CosiumInvoice.tenant_id == tenant_id,
            CosiumInvoice.type == "QUOTE",
            CosiumInvoice.invoice_date < cutoff,
            CosiumInvoice.outstanding_balance == 0,
        )
        .limit(100)
    ).all()
    if not quotes:
        return
    existing_ids = action_item_repo.list_pending_entity_ids(
        db, user_id=user_id, tenant_id=tenant_id, type="devis_dormant", entity_type="cosium_invoice"
    )

    for q in quotes:
        if q.id not in existing_ids:
            days_old = (datetime.now(UTC).replace(tzinfo=None) - q.invoice_date).days if q.invoice_date else 0
            action_item_repo.create(
                db, tenant_id=tenant_id, user_id=user_id,
                type="devis_dormant",
                title=f"Devis dormant {q.invoice_number or '#' + str(q.id)} - {float(q.total_ti):.2f} EUR",
                description=f"Devis non transforme depuis {days_old} jours",
                entity_type="cosium_invoice", entity_id=q.id,
                priority="medium",
            )


def generate_renewal_opportunities(db: Session, tenant_id: int, user_id: int) -> None:
    """Alerte clients avec dernier achat optique > 24 mois (eligibles renouvellement)."""
    cutoff_old = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=730)  # 2 ans
    cutoff_recent = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=1825)  # 5 ans

    last_purchase = (
        select(
            CosiumInvoice.customer_id,
            func.max(CosiumInvoice.invoice_date).label("last_date"),
            func.sum(CosiumInvoice.total_ti).label("ca"),
        )
        .where(
            CosiumInvoice.tenant_id == tenant_id,
            CosiumInvoice.type == "INVOICE",
            CosiumInvoice.customer_id.isnot(None),
        )
        .group_by(CosiumInvoice.customer_id)
        .having(func.max(CosiumInvoice.invoice_date) < cutoff_old)
        .having(func.max(CosiumInvoice.invoice_date) >= cutoff_recent)
        .subquery()
    )

    rows = db.execute(
        select(
            last_purchase.c.customer_id,
            last_purchase.c.last_date,
            last_purchase.c.ca,
        )
        .order_by(last_purchase.c.ca.desc())
        .limit(100)
    ).all()
    if not rows:
        return
    existing_ids = action_item_repo.list_pending_entity_ids(
        db, user_id=user_id, tenant_id=tenant_id, type="renouvellement", entity_type="customer"
    )

    for r in rows:
        if not r.customer_id:
            continue
        if r.customer_id not in existing_ids:
            months_ago = (datetime.now(UTC).replace(tzinfo=None) - r.last_date).days // 30 if r.last_date else 0
            ca_total = float(r.ca or 0)
            priority = "high" if ca_total > 500 and months_ago > 30 else "medium"
            action_item_repo.create(
                db, tenant_id=tenant_id, user_id=user_id,
                type="renouvellement",
                title=f"Renouvellement #{r.customer_id} - {months_ago} mois sans achat",
                description=f"CA historique : {ca_total:.2f} EUR. A relancer pour bilan visuel.",
                entity_type="customer", entity_id=r.customer_id,
                priority=priority,
            )


def generate_overdue_payments(db: Session, tenant_id: int, user_id: int) -> None:
    overdue = db.execute(
        select(Payment.id, Payment.case_id, Payment.amount_due, Payment.amount_paid, Payment.payer_type)
        .where(Payment.tenant_id == tenant_id)
        .where(Payment.status.in_(["pending", "partial"]))
        .where(Payment.amount_paid < Payment.amount_due)
    ).all()
    if not overdue:
        return
    existing_ids = action_item_repo.list_pending_entity_ids(
        db, user_id=user_id, tenant_id=tenant_id, type="paiement_retard", entity_type="payment"
    )

    for p in overdue:
        remaining = float(p.amount_due) - float(p.amount_paid)
        if p.id not in existing_ids:
            action_item_repo.create(
                db,
                tenant_id=tenant_id,
                user_id=user_id,
                type="paiement_retard",
                title=f"Paiement en attente -{p.payer_type}",
                description=f"Reste a payer : {remaining:.2f} EUR",
                entity_type="payment",
                entity_id=p.id,
                priority="high",
            )
