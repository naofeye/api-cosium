"""Service IA — copilote metier OptiFlow avec 4 modes."""

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.integrations.ai.claude_provider import claude_provider
from app.integrations.ai.rag import search_docs
from app.models import (
    Case,
    Customer,
    Devis,
    Document,
    Facture,
    PayerOrganization,
    Payment,
    PecRequest,
)
from app.models.cosium_data import CosiumInvoice, CosiumPayment, CosiumPrescription

logger = get_logger("ai_service")

SYSTEM_PROMPTS = {
    "dossier": (
        "Tu es le Copilote Dossier d'OptiFlow, une plateforme pour opticiens. "
        "Analyse le dossier client fourni et reponds en francais. "
        "Identifie : resume du dossier, anomalies, prochaines actions, pieces manquantes. "
        "Sois concis et actionnable."
    ),
    "financier": (
        "Tu es le Copilote Financier d'OptiFlow. "
        "Analyse la situation financiere du dossier : suivi paiements, risque de retard, "
        "recommandation de relance. Donne des chiffres precis."
    ),
    "documentaire": (
        "Tu es le Copilote Documentaire d'OptiFlow, specialise dans le logiciel Cosium. "
        "Utilise les extraits de documentation fournis pour repondre aux questions "
        "sur les fonctionnalites, la configuration et l'utilisation de Cosium. "
        "Si l'info n'est pas dans le contexte, dis-le clairement."
    ),
    "marketing": (
        "Tu es le Copilote Marketing d'OptiFlow. "
        "Suggere des segments clients, des campagnes, et des strategies marketing "
        "adaptees aux opticiens. Sois creatif mais realiste."
    ),
}


def get_client_cosium_context(db: Session, customer_id: int, tenant_id: int) -> str:
    """Build a concise Cosium data context string for a given customer.

    Queries CosiumInvoice, CosiumPrescription, and CosiumPayment tables
    for data linked to this customer, and formats it as a readable summary.
    """
    parts: list[str] = []

    # Cosium invoices
    invoices = db.execute(
        select(
            CosiumInvoice.invoice_number,
            CosiumInvoice.invoice_date,
            CosiumInvoice.total_ti,
            CosiumInvoice.outstanding_balance,
            CosiumInvoice.type,
            CosiumInvoice.settled,
        )
        .where(
            CosiumInvoice.customer_id == customer_id,
            CosiumInvoice.tenant_id == tenant_id,
        )
        .order_by(CosiumInvoice.invoice_date.desc())
        .limit(20)
    ).all()

    if invoices:
        total_amount = sum(float(inv.total_ti) for inv in invoices)
        total_outstanding = sum(float(inv.outstanding_balance) for inv in invoices)
        settled_count = sum(1 for inv in invoices if inv.settled)
        last_date = invoices[0].invoice_date if invoices[0].invoice_date else None
        parts.append(
            f"FACTURES COSIUM ({len(invoices)}): "
            f"total {total_amount:.2f} EUR, "
            f"solde restant {total_outstanding:.2f} EUR, "
            f"{settled_count} soldees"
        )
        if last_date:
            parts.append(f"  Derniere facture: {last_date.strftime('%d/%m/%Y') if hasattr(last_date, 'strftime') else last_date}")
        for inv in invoices[:5]:
            date_str = inv.invoice_date.strftime('%d/%m/%Y') if inv.invoice_date and hasattr(inv.invoice_date, 'strftime') else 'N/A'
            parts.append(
                f"  - {inv.invoice_number} ({inv.type}) {date_str}: "
                f"{inv.total_ti:.2f} EUR {'(solde)' if inv.settled else f'reste {inv.outstanding_balance:.2f} EUR'}"
            )

    # Cosium prescriptions
    prescriptions = db.execute(
        select(
            CosiumPrescription.prescription_date,
            CosiumPrescription.sphere_right,
            CosiumPrescription.cylinder_right,
            CosiumPrescription.axis_right,
            CosiumPrescription.addition_right,
            CosiumPrescription.sphere_left,
            CosiumPrescription.cylinder_left,
            CosiumPrescription.axis_left,
            CosiumPrescription.addition_left,
            CosiumPrescription.prescriber_name,
        )
        .where(
            CosiumPrescription.customer_id == customer_id,
            CosiumPrescription.tenant_id == tenant_id,
        )
        .order_by(CosiumPrescription.file_date.desc())
        .limit(5)
    ).all()

    if prescriptions:
        parts.append(f"\nORDONNANCES COSIUM ({len(prescriptions)}):")
        for rx in prescriptions:
            od_parts = []
            if rx.sphere_right is not None:
                od_parts.append(f"sph {rx.sphere_right:+.2f}")
            if rx.cylinder_right is not None:
                od_parts.append(f"cyl {rx.cylinder_right:+.2f}")
            if rx.axis_right is not None:
                od_parts.append(f"axe {int(rx.axis_right)}")
            if rx.addition_right is not None:
                od_parts.append(f"add {rx.addition_right:+.2f}")

            og_parts = []
            if rx.sphere_left is not None:
                og_parts.append(f"sph {rx.sphere_left:+.2f}")
            if rx.cylinder_left is not None:
                og_parts.append(f"cyl {rx.cylinder_left:+.2f}")
            if rx.axis_left is not None:
                og_parts.append(f"axe {int(rx.axis_left)}")
            if rx.addition_left is not None:
                og_parts.append(f"add {rx.addition_left:+.2f}")

            od_str = " ".join(od_parts) if od_parts else "N/A"
            og_str = " ".join(og_parts) if og_parts else "N/A"
            date_str = rx.prescription_date or "N/A"
            prescriber = rx.prescriber_name or "N/A"
            parts.append(f"  - {date_str} (Dr {prescriber}): OD [{od_str}] OG [{og_str}]")

    # Cosium payments — linked to customer via invoice_cosium_id
    # CosiumPayment doesn't have a direct customer_id, so we go through invoices.
    if invoices:
        customer_invoice_ids = db.scalars(
            select(CosiumInvoice.cosium_id).where(
                CosiumInvoice.customer_id == customer_id,
                CosiumInvoice.tenant_id == tenant_id,
            )
        ).all()

        if customer_invoice_ids:
            cosium_payments = db.execute(
                select(
                    CosiumPayment.amount,
                    CosiumPayment.type,
                    CosiumPayment.due_date,
                    CosiumPayment.payment_number,
                )
                .where(
                    CosiumPayment.tenant_id == tenant_id,
                    CosiumPayment.invoice_cosium_id.in_(customer_invoice_ids),
                )
                .order_by(CosiumPayment.due_date.desc())
                .limit(10)
            ).all()

            if cosium_payments:
                total_paid = sum(float(p.amount) for p in cosium_payments)
                parts.append(
                    f"\nPAIEMENTS COSIUM ({len(cosium_payments)}): "
                    f"total encaisse {total_paid:.2f} EUR"
                )
                for p in cosium_payments[:5]:
                    date_str = p.due_date.strftime('%d/%m/%Y') if p.due_date and hasattr(p.due_date, 'strftime') else 'N/A'
                    parts.append(f"  - {p.payment_number} ({p.type}) {date_str}: {p.amount:.2f} EUR")

    if not parts:
        return ""

    return "\n".join(parts)


def _build_case_context(db: Session, tenant_id: int, case_id: int) -> str:
    """Construit le contexte complet d'un dossier pour le copilote."""
    case = db.execute(
        select(
            Case.id,
            Case.status,
            Case.source,
            Case.created_at,
            Customer.first_name,
            Customer.last_name,
            Customer.phone,
            Customer.email,
        )
        .join(Customer, Customer.id == Case.customer_id)
        .where(Case.id == case_id, Case.tenant_id == tenant_id)
    ).first()
    if not case:
        return f"Dossier #{case_id} introuvable."

    parts = [
        f"DOSSIER #{case.id}",
        f"Client: {case.first_name} {case.last_name}",
        f"Statut: {case.status} | Source: {case.source}",
        f"Tel: {case.phone or 'N/A'} | Email: {case.email or 'N/A'}",
        f"Cree le: {case.created_at}",
    ]

    # Documents
    docs = db.execute(
        select(Document.type, Document.filename, Document.uploaded_at).where(Document.case_id == case_id)
    ).all()
    if docs:
        parts.append(f"\nDOCUMENTS ({len(docs)}):")
        for d in docs:
            parts.append(f"  - {d.type}: {d.filename} ({d.uploaded_at})")

    # Devis
    devis_list = db.execute(
        select(Devis.numero, Devis.status, Devis.montant_ttc, Devis.reste_a_charge).where(Devis.case_id == case_id)
    ).all()
    if devis_list:
        parts.append(f"\nDEVIS ({len(devis_list)}):")
        for d in devis_list:
            parts.append(f"  - {d.numero}: {d.status} | TTC: {d.montant_ttc} EUR | RAC: {d.reste_a_charge} EUR")

    # Factures
    factures = db.execute(
        select(Facture.numero, Facture.status, Facture.montant_ttc).where(Facture.case_id == case_id)
    ).all()
    if factures:
        parts.append(f"\nFACTURES ({len(factures)}):")
        for f in factures:
            parts.append(f"  - {f.numero}: {f.status} | {f.montant_ttc} EUR")

    # Paiements
    payments = db.execute(
        select(Payment.payer_type, Payment.amount_due, Payment.amount_paid, Payment.status).where(
            Payment.case_id == case_id
        )
    ).all()
    if payments:
        parts.append(f"\nPAIEMENTS ({len(payments)}):")
        total_due = sum(float(p.amount_due) for p in payments)
        total_paid = sum(float(p.amount_paid) for p in payments)
        for p in payments:
            parts.append(f"  - {p.payer_type}: du={p.amount_due} EUR, paye={p.amount_paid} EUR ({p.status})")
        parts.append(f"  TOTAL: du={total_due} EUR, paye={total_paid} EUR, reste={total_due - total_paid} EUR")

    # PEC
    pecs = db.execute(
        select(
            PecRequest.id,
            PecRequest.status,
            PecRequest.montant_demande,
            PecRequest.montant_accorde,
            PayerOrganization.name,
        )
        .join(PayerOrganization, PayerOrganization.id == PecRequest.organization_id)
        .where(PecRequest.case_id == case_id)
    ).all()
    if pecs:
        parts.append(f"\nPEC ({len(pecs)}):")
        for p in pecs:
            parts.append(
                f"  - {p.name}: {p.status} | demande={p.montant_demande} EUR | accorde={p.montant_accorde or 'N/A'} EUR"
            )

    # Enrich with Cosium data if customer is linked
    customer_row = db.execute(
        select(Case.customer_id).where(Case.id == case_id, Case.tenant_id == tenant_id)
    ).first()
    if customer_row and customer_row.customer_id:
        cosium_ctx = get_client_cosium_context(db, customer_row.customer_id, tenant_id)
        if cosium_ctx:
            parts.append(f"\n--- DONNEES COSIUM (ERP) ---\n{cosium_ctx}")

    return "\n".join(parts)


def copilot_query(
    db: Session,
    tenant_id: int,
    question: str,
    user_id: int,
    case_id: int | None = None,
    mode: str = "dossier",
) -> str:
    """Point d'entree principal du copilote IA."""
    system = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["dossier"])
    context = ""

    if mode == "documentaire":
        # RAG: recherche dans les docs Cosium
        rag_results = search_docs(question)
        if rag_results:
            context = f"DOCUMENTATION COSIUM (extraits pertinents):\n\n{rag_results}"
        else:
            context = "Aucun extrait de documentation pertinent trouve."

    elif case_id:
        context = _build_case_context(db, tenant_id, case_id)

    elif mode == "marketing":
        # Contexte marketing global
        total_clients = (
            db.scalar(select(func.count()).select_from(Customer).where(Customer.tenant_id == tenant_id)) or 0
        )
        total_cases = db.scalar(select(func.count()).select_from(Case).where(Case.tenant_id == tenant_id)) or 0
        context = (
            f"CONTEXTE MARKETING:\nNombre total de clients: {total_clients}\nNombre total de dossiers: {total_cases}\n"
        )

    logger.info("copilot_query", tenant_id=tenant_id, mode=mode, case_id=case_id, question_len=len(question))
    result = claude_provider.query_with_usage(question, context=context, system=system)

    # Log AI usage
    from app.models import AiUsageLog

    try:
        usage = AiUsageLog(
            tenant_id=tenant_id,
            user_id=user_id,
            copilot_type=mode,
            model_used=result.get("model", "unknown"),
            tokens_in=result.get("tokens_in", 0),
            tokens_out=result.get("tokens_out", 0),
            cost_usd=_estimate_cost(result.get("tokens_in", 0), result.get("tokens_out", 0)),
        )
        db.add(usage)
        db.commit()
    except (SQLAlchemyError, ValueError, TypeError) as e:
        logger.warning("ai_usage_log_failed", error=str(e))

    return result["text"]


def _estimate_cost(tokens_in: int, tokens_out: int) -> float:
    """Estimation du cout basee sur les tarifs Haiku."""
    return round((tokens_in * 0.00000025) + (tokens_out * 0.00000125), 6)
