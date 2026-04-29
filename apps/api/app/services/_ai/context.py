"""Constructeurs de contexte pour le copilote IA (dossier, Cosium)."""

from sqlalchemy.orm import Session

from app.integrations.ai.rag import search_docs
from app.repositories import ai_context_repo

from app.services._ai.prompts import SYSTEM_PROMPTS


def get_client_cosium_context(db: Session, customer_id: int, tenant_id: int) -> str:
    """Build a concise Cosium data context string for a given customer.

    Queries CosiumInvoice, CosiumPrescription, and CosiumPayment tables
    for data linked to this customer, and formats it as a readable summary.
    """
    parts: list[str] = []

    invoices = ai_context_repo.get_cosium_invoices(db, customer_id, tenant_id)

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

    prescriptions = ai_context_repo.get_cosium_prescriptions(db, customer_id, tenant_id)

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

    if invoices:
        customer_invoice_ids = ai_context_repo.get_cosium_invoice_ids(db, customer_id, tenant_id)

        if customer_invoice_ids:
            cosium_payments = ai_context_repo.get_cosium_payments_by_invoice_ids(
                db, customer_invoice_ids, tenant_id
            )

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
    case = ai_context_repo.get_case_with_customer(db, case_id, tenant_id)
    if not case:
        return f"Dossier #{case_id} introuvable."

    parts = [
        f"DOSSIER #{case.id}",
        f"Client: {case.first_name} {case.last_name}",
        f"Statut: {case.status} | Source: {case.source}",
        f"Tel: {case.phone or 'N/A'} | Email: {case.email or 'N/A'}",
        f"Cree le: {case.created_at}",
    ]

    docs = ai_context_repo.get_case_documents(db, case_id)
    if docs:
        parts.append(f"\nDOCUMENTS ({len(docs)}):")
        for d in docs:
            parts.append(f"  - {d.type}: {d.filename} ({d.uploaded_at})")

    devis_list = ai_context_repo.get_case_devis(db, case_id)
    if devis_list:
        parts.append(f"\nDEVIS ({len(devis_list)}):")
        for d in devis_list:
            parts.append(f"  - {d.numero}: {d.status} | TTC: {d.montant_ttc} EUR | RAC: {d.reste_a_charge} EUR")

    factures = ai_context_repo.get_case_factures(db, case_id)
    if factures:
        parts.append(f"\nFACTURES ({len(factures)}):")
        for f in factures:
            parts.append(f"  - {f.numero}: {f.status} | {f.montant_ttc} EUR")

    payments = ai_context_repo.get_case_payments(db, case_id)
    if payments:
        parts.append(f"\nPAIEMENTS ({len(payments)}):")
        total_due = sum(float(p.amount_due) for p in payments)
        total_paid = sum(float(p.amount_paid) for p in payments)
        for p in payments:
            parts.append(f"  - {p.payer_type}: du={p.amount_due} EUR, paye={p.amount_paid} EUR ({p.status})")
        parts.append(f"  TOTAL: du={total_due} EUR, paye={total_paid} EUR, reste={total_due - total_paid} EUR")

    pecs = ai_context_repo.get_case_pecs(db, case_id)
    if pecs:
        parts.append(f"\nPEC ({len(pecs)}):")
        for p in pecs:
            parts.append(
                f"  - {p.name}: {p.status} | demande={p.montant_demande} EUR | accorde={p.montant_accorde or 'N/A'} EUR"
            )

    customer_id = ai_context_repo.get_case_customer_id(db, case_id, tenant_id)
    if customer_id:
        cosium_ctx = get_client_cosium_context(db, customer_id, tenant_id)
        if cosium_ctx:
            parts.append(f"\n--- DONNEES COSIUM (ERP) ---\n{cosium_ctx}")

    return "\n".join(parts)


def resolve_copilot_context(
    db: Session, tenant_id: int, mode: str, question: str, case_id: int | None
) -> tuple[str, str]:
    """Retourne (system_prompt, context_string) pour un appel copilote."""
    system = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["dossier"])
    context = ""

    if mode == "documentaire":
        rag_results = search_docs(question)
        context = (
            f"DOCUMENTATION COSIUM (extraits pertinents):\n\n{rag_results}"
            if rag_results
            else "Aucun extrait de documentation pertinent trouve."
        )
    elif case_id:
        context = _build_case_context(db, tenant_id, case_id)
    elif mode == "marketing":
        total_clients = ai_context_repo.count_customers(db, tenant_id)
        total_cases = ai_context_repo.count_cases(db, tenant_id)
        context = (
            f"CONTEXTE MARKETING:\nNombre total de clients: {total_clients}\n"
            f"Nombre total de dossiers: {total_cases}\n"
        )

    return system, context
