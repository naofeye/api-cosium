from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError, NotFoundError
from app.core.logging import get_logger
from app.domain.schemas.devis import (
    DevisCreate,
    DevisDetail,
    DevisLineCreate,
    DevisLineResponse,
    DevisResponse,
    DevisSendEmailResponse,
    DevisUpdate,
)
from app.integrations.email_sender import EmailAttachment, email_sender
from app.integrations.email_templates import render_email
from app.repositories import devis_repo
from app.services import audit_service, event_service, pdf_service, webhook_emit_helpers

logger = get_logger("devis_service")

VALID_TRANSITIONS: dict[str, list[str]] = {
    "brouillon": ["envoye", "annule"],
    "envoye": ["signe", "annule"],
    "signe": ["facture", "annule"],
    "facture": [],
    "annule": [],
}

EVENT_MAP: dict[str, str] = {
    "brouillon": "DevisCree",
    "envoye": "DevisEnvoye",
    "signe": "DevisSigne",
    "annule": "DevisAnnule",
}


def _compute_ligne(ligne: DevisLineCreate) -> tuple[float, float]:
    montant_ht = round(ligne.quantite * ligne.prix_unitaire_ht, 2)
    montant_ttc = round(montant_ht * (1 + ligne.taux_tva / 100), 2)
    return montant_ht, montant_ttc


def _add_lignes(db: Session, tenant_id: int, devis_id: int, lignes: list[DevisLineCreate]) -> None:
    for ligne in lignes:
        montant_ht, montant_ttc = _compute_ligne(ligne)
        devis_repo.add_ligne(
            db,
            tenant_id,
            devis_id,
            designation=ligne.designation,
            quantite=ligne.quantite,
            prix_unitaire_ht=ligne.prix_unitaire_ht,
            taux_tva=ligne.taux_tva,
            montant_ht=montant_ht,
            montant_ttc=montant_ttc,
        )
    db.flush()


def _recalculate_totals(
    db: Session, tenant_id: int, devis_id: int, part_secu: float, part_mutuelle: float
) -> tuple[float, float, float, float]:
    lignes = devis_repo.get_lignes(db, devis_id=devis_id, tenant_id=tenant_id)
    total_ht = round(sum(float(l.montant_ht) for l in lignes), 2)
    total_ttc = round(sum(float(l.montant_ttc) for l in lignes), 2)
    total_tva = round(total_ttc - total_ht, 2)
    reste = round(max(total_ttc - part_secu - part_mutuelle, 0), 2)
    return total_ht, total_tva, total_ttc, reste


def create_devis(db: Session, tenant_id: int, payload: DevisCreate, user_id: int) -> DevisResponse:
    numero = devis_repo.generate_numero(db, tenant_id)
    devis = devis_repo.create(db, tenant_id, payload.case_id, numero)

    _add_lignes(db, tenant_id, devis.id, payload.lignes)

    total_ht, total_tva, total_ttc, reste = _recalculate_totals(
        db, tenant_id, devis.id, payload.part_secu, payload.part_mutuelle
    )
    devis_repo.update_totals(
        db,
        devis,
        total_ht,
        total_tva,
        total_ttc,
        payload.part_secu,
        payload.part_mutuelle,
        reste,
    )
    db.commit()
    db.refresh(devis)

    if user_id:
        audit_service.log_action(
            db,
            tenant_id,
            user_id,
            "create",
            "devis",
            devis.id,
            new_value={"numero": numero, "montant_ttc": total_ttc},
        )
        event_service.emit_event(db, tenant_id, "DevisCree", "devis", devis.id, user_id)
        devis_response = DevisResponse.model_validate(devis)
        webhook_emit_helpers.emit_devis_created(db, tenant_id, devis_response)

    logger.info("devis_created", tenant_id=tenant_id, devis_id=devis.id, numero=numero)
    return DevisResponse.model_validate(devis)


def list_devis(db: Session, tenant_id: int, limit: int = 25, offset: int = 0) -> list[DevisResponse]:
    rows = devis_repo.list_all(db, tenant_id, limit=limit, offset=offset)
    return [DevisResponse(**r) for r in rows]


def get_devis_detail(db: Session, tenant_id: int, devis_id: int) -> DevisDetail:
    data = devis_repo.get_detail(db, devis_id=devis_id, tenant_id=tenant_id)
    if not data:
        raise NotFoundError("devis", devis_id)
    lignes = devis_repo.get_lignes(db, devis_id=devis_id, tenant_id=tenant_id)
    return DevisDetail(
        **data,
        lignes=[DevisLineResponse.model_validate(l) for l in lignes],
    )


def update_devis(db: Session, tenant_id: int, devis_id: int, payload: DevisUpdate, user_id: int) -> DevisResponse:
    devis = devis_repo.get_by_id(db, devis_id=devis_id, tenant_id=tenant_id)
    if not devis:
        raise NotFoundError("devis", devis_id)
    if devis.status != "brouillon":
        raise BusinessError("Seul un devis en brouillon peut etre modifie", code="DEVIS_NOT_EDITABLE")

    part_secu = payload.part_secu if payload.part_secu is not None else float(devis.part_secu)
    part_mutuelle = payload.part_mutuelle if payload.part_mutuelle is not None else float(devis.part_mutuelle)

    if payload.lignes is not None:
        # Calculate new totals BEFORE modifying anything to ensure atomicity
        new_total_ht = 0.0
        new_total_ttc = 0.0
        for ligne in payload.lignes:
            montant_ht, montant_ttc = _compute_ligne(ligne)
            new_total_ht += montant_ht
            new_total_ttc += montant_ttc

        # All-or-nothing: delete old + insert new in same flush
        devis_repo.clear_lignes(db, devis_id=devis_id, tenant_id=tenant_id)
        _add_lignes(db, tenant_id, devis_id, payload.lignes)

    total_ht, total_tva, total_ttc, reste = _recalculate_totals(db, tenant_id, devis_id, part_secu, part_mutuelle)
    devis_repo.update_totals(
        db,
        devis,
        total_ht,
        total_tva,
        total_ttc,
        part_secu,
        part_mutuelle,
        reste,
    )

    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    db.refresh(devis)

    if user_id:
        audit_service.log_action(
            db, tenant_id, user_id, "update", "devis", devis.id, new_value={"montant_ttc": total_ttc}
        )

    logger.info("devis_updated", tenant_id=tenant_id, devis_id=devis.id)
    return DevisResponse.model_validate(devis)


def change_status(db: Session, tenant_id: int, devis_id: int, new_status: str, user_id: int) -> DevisResponse:
    devis = devis_repo.get_by_id(db, devis_id=devis_id, tenant_id=tenant_id)
    if not devis:
        raise NotFoundError("devis", devis_id)

    allowed = VALID_TRANSITIONS.get(devis.status, [])
    if new_status not in allowed:
        raise BusinessError(
            "INVALID_TRANSITION",
            f"Transition '{devis.status}' -> '{new_status}' non autorisee. "
            f"Transitions possibles : {', '.join(allowed) or 'aucune'}",
        )

    old_status = devis.status
    devis_repo.update_status(db, devis, new_status)

    if user_id:
        audit_service.log_action(
            db,
            tenant_id,
            user_id,
            "update",
            "devis",
            devis.id,
            old_value={"status": old_status},
            new_value={"status": new_status},
        )
        event_name = EVENT_MAP.get(new_status)
        if event_name:
            event_service.emit_event(db, tenant_id, event_name, "devis", devis.id, user_id)
            webhook_emit_helpers.emit_devis_status_changed(
                db, tenant_id, DevisResponse.model_validate(devis), new_status
            )

    logger.info("devis_status_changed", tenant_id=tenant_id, devis_id=devis.id, old=old_status, new=new_status)
    return DevisResponse.model_validate(devis)


def send_devis_email(
    db: Session,
    tenant_id: int,
    devis_id: int,
    user_id: int,
    to: str | None = None,
    subject: str | None = None,
    message: str | None = None,
) -> DevisSendEmailResponse:
    """Envoie le devis par email avec PDF en piece jointe.

    Si `to` est None, utilise l'email du client par defaut. Si le client n'a
    pas d'email et qu'aucun destinataire n'est fourni, leve une BusinessError.
    """
    devis = devis_repo.get_by_id(db, devis_id=devis_id, tenant_id=tenant_id)
    if not devis:
        raise NotFoundError("devis", devis_id)

    contact = devis_repo.get_customer_contact(db, devis_id=devis_id, tenant_id=tenant_id)
    if not contact:
        raise NotFoundError("devis", devis_id)

    recipient = (to or contact["customer_email"] or "").strip()
    if not recipient:
        raise BusinessError(
            "Aucun destinataire : le client n'a pas d'email enregistre, fournissez un destinataire explicite.",
            code="EMAIL_RECIPIENT_MISSING",
        )

    pdf_bytes = pdf_service.generate_devis_pdf(db, devis_id=devis_id, tenant_id=tenant_id)

    devis_date = (
        contact["devis_created_at"].strftime("%d/%m/%Y")
        if contact["devis_created_at"]
        else None
    )
    body_html = render_email(
        "devis.html",
        client_name=contact["customer_name"] or "Madame, Monsieur",
        devis_numero=contact["devis_numero"],
        devis_date=devis_date,
        custom_message=(message or "").strip() or None,
    )

    email_subject = (subject or f"Votre devis {contact['devis_numero']}").strip()
    attachment = EmailAttachment(
        filename=f"devis_{contact['devis_numero']}.pdf",
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
            "devis",
            devis_id,
            new_value={"to": recipient, "subject": email_subject},
        )
        event_service.emit_event(
            db, tenant_id, "DevisEnvoye", "devis", devis_id, user_id
        )
        db.commit()

    logger.info(
        "devis_email_sent",
        tenant_id=tenant_id,
        devis_id=devis_id,
        to=recipient,
    )
    return DevisSendEmailResponse(sent=True, to=recipient, devis_id=devis_id)
