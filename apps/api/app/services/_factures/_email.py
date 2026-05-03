"""Envoi facture par email (PDF en piece jointe) extrait de facture_service."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError, NotFoundError
from app.core.logging import get_logger
from app.domain.schemas.factures import FactureSendEmailResponse
from app.integrations.email_sender import EmailAttachment, email_sender
from app.integrations.email_templates import render_email
from app.repositories import facture_repo
from app.services import audit_service, event_service, pdf_service

logger = get_logger("facture_service.email")


def send_facture_email(
    db: Session,
    tenant_id: int,
    facture_id: int,
    user_id: int,
    to: str | None = None,
    subject: str | None = None,
    message: str | None = None,
) -> FactureSendEmailResponse:
    """Envoie la facture par email avec PDF en piece jointe."""
    facture = facture_repo.get_by_id(db, facture_id=facture_id, tenant_id=tenant_id)
    if not facture:
        raise NotFoundError("facture", facture_id)

    contact = facture_repo.get_customer_contact(
        db, facture_id=facture_id, tenant_id=tenant_id
    )
    if not contact:
        raise NotFoundError("facture", facture_id)

    recipient = (to or contact["customer_email"] or "").strip()
    if not recipient:
        raise BusinessError(
            "Aucun destinataire : le client n'a pas d'email enregistre, fournissez un destinataire explicite.",
            code="EMAIL_RECIPIENT_MISSING",
        )

    pdf_bytes = pdf_service.generate_facture_pdf(
        db, facture_id=facture_id, tenant_id=tenant_id
    )

    facture_date = (
        contact["facture_date"].strftime("%d/%m/%Y")
        if contact["facture_date"]
        else None
    )
    body_html = render_email(
        "facture.html",
        client_name=contact["customer_name"] or "Madame, Monsieur",
        facture_numero=contact["facture_numero"],
        facture_date=facture_date,
        montant_ht=f"{contact['montant_ht']:.2f}",
        tva=f"{contact['tva']:.2f}",
        montant_ttc=f"{contact['montant_ttc']:.2f}",
        custom_message=(message or "").strip() or None,
    )

    email_subject = (subject or f"Votre facture {contact['facture_numero']}").strip()
    attachment = EmailAttachment(
        filename=f"facture_{contact['facture_numero']}.pdf",
        content=pdf_bytes,
        mime_type="application/pdf",
    )

    sent = email_sender.send_email(
        to=recipient,
        subject=email_subject,
        body_html=body_html,
        attachments=[attachment],
    )

    if not sent:
        raise BusinessError(
            "L'envoi de l'email a echoue. Reessayez plus tard.",
            code="EMAIL_SEND_FAILED",
        )

    if user_id:
        audit_service.log_action(
            db,
            tenant_id,
            user_id,
            "send_email",
            "facture",
            facture_id,
            new_value={"to": recipient, "subject": email_subject},
        )
        event_service.emit_event(
            db, tenant_id, "FactureEnvoyee", "facture", facture_id, user_id
        )
        db.commit()

    logger.info(
        "facture_email_sent",
        tenant_id=tenant_id,
        facture_id=facture_id,
        to=recipient,
    )
    return FactureSendEmailResponse(sent=True, to=recipient, facture_id=facture_id)
