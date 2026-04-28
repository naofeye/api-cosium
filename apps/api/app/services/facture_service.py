from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError, NotFoundError
from app.core.logging import get_logger
from app.domain.schemas.factures import (
    FactureDetail,
    FactureLigneResponse,
    FactureResponse,
    FactureSendEmailResponse,
)
from app.integrations.email_sender import EmailAttachment, email_sender
from app.integrations.email_templates import render_email
from app.repositories import devis_repo, facture_repo
from app.services import audit_service, event_service, pdf_service

logger = get_logger("facture_service")


def create_from_devis(db: Session, tenant_id: int, devis_id: int, user_id: int) -> FactureResponse:
    devis = devis_repo.get_by_id(db, devis_id=devis_id, tenant_id=tenant_id)
    if not devis:
        raise NotFoundError("devis", devis_id)

    if devis.status == "facture":
        # Idempotent: if already converted, return existing facture
        existing = facture_repo.get_by_devis_id(db, devis_id=devis_id, tenant_id=tenant_id)
        if existing:
            logger.info("facture_already_exists", tenant_id=tenant_id, devis_id=devis_id, facture_id=existing.id)
            return FactureResponse.model_validate(existing)
        # Partial failure recovery: devis marked as "facture" but no facture exists — allow creation
    elif devis.status != "signe":
        raise BusinessError(
            "DEVIS_NOT_SIGNED",
            "Le devis doit etre signe avant de pouvoir generer une facture",
        )

    numero = facture_repo.generate_numero(db, tenant_id)
    facture = facture_repo.create(
        db,
        tenant_id=tenant_id,
        case_id=devis.case_id,
        devis_id=devis.id,
        numero=numero,
        montant_ht=float(devis.montant_ht),
        tva=float(devis.tva),
        montant_ttc=float(devis.montant_ttc),
    )

    lignes = devis_repo.get_lignes(db, devis_id=devis_id, tenant_id=tenant_id)
    for l in lignes:
        facture_repo.add_ligne(
            db,
            tenant_id,
            facture.id,
            designation=l.designation,
            quantite=l.quantite,
            prix_unitaire_ht=float(l.prix_unitaire_ht),
            taux_tva=float(l.taux_tva),
            montant_ht=float(l.montant_ht),
            montant_ttc=float(l.montant_ttc),
        )

    if devis.status == "signe":
        devis_repo.update_status(db, devis, "facture")

    db.commit()
    db.refresh(facture)

    if user_id:
        audit_service.log_action(
            db,
            tenant_id,
            user_id,
            "create",
            "facture",
            facture.id,
            new_value={"numero": numero, "devis_id": devis_id},
        )
        event_service.emit_event(db, tenant_id, "FactureEmise", "facture", facture.id, user_id)

    logger.info("facture_created", tenant_id=tenant_id, facture_id=facture.id, numero=numero, devis_id=devis_id)
    return FactureResponse.model_validate(facture)


def list_factures(db: Session, tenant_id: int, limit: int = 25, offset: int = 0) -> list[FactureResponse]:
    rows = facture_repo.list_all(db, tenant_id, limit=limit, offset=offset)
    return [FactureResponse(**r) for r in rows]


def get_facture_detail(db: Session, tenant_id: int, facture_id: int) -> FactureDetail:
    data = facture_repo.get_detail(db, facture_id=facture_id, tenant_id=tenant_id)
    if not data:
        raise NotFoundError("facture", facture_id)
    lignes = facture_repo.get_lignes(db, facture_id=facture_id, tenant_id=tenant_id)
    return FactureDetail(
        **data,
        lignes=[FactureLigneResponse.model_validate(l) for l in lignes],
    )


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
