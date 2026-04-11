from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models import TenantUser, User
from app.services import notification_service

logger = get_logger("event_service")

EVENT_CONFIG: dict[str, dict] = {
    "DossierCree": {
        "notif_type": "info",
        "title": "Nouveau dossier cree",
        "message_tpl": "Le dossier #{entity_id} a ete cree.",
    },
    "DocumentAjoute": {
        "notif_type": "success",
        "title": "Document ajoute",
        "message_tpl": "Un document a ete ajoute au dossier #{entity_id}.",
    },
    "PaiementRecu": {
        "notif_type": "success",
        "title": "Paiement recu",
        "message_tpl": "Un paiement a ete enregistre pour le dossier #{entity_id}.",
    },
    "DevisCree": {
        "notif_type": "info",
        "title": "Devis cree",
        "message_tpl": "Le devis #{entity_id} a ete cree.",
    },
    "DevisEnvoye": {
        "notif_type": "info",
        "title": "Devis envoye",
        "message_tpl": "Le devis #{entity_id} a ete envoye au client.",
    },
    "DevisSigne": {
        "notif_type": "success",
        "title": "Devis signe",
        "message_tpl": "Le devis #{entity_id} a ete signe par le client.",
    },
    "DevisAnnule": {
        "notif_type": "warning",
        "title": "Devis annule",
        "message_tpl": "Le devis #{entity_id} a ete annule.",
    },
    "FactureEmise": {
        "notif_type": "success",
        "title": "Facture emise",
        "message_tpl": "La facture #{entity_id} a ete emise.",
    },
    "FacturePayee": {
        "notif_type": "success",
        "title": "Facture payee",
        "message_tpl": "La facture #{entity_id} a ete payee.",
    },
    "PECSoumise": {
        "notif_type": "info",
        "title": "PEC soumise",
        "message_tpl": "La demande de PEC #{entity_id} a ete soumise.",
    },
    "PECAcceptee": {
        "notif_type": "success",
        "title": "PEC acceptee",
        "message_tpl": "La demande de PEC #{entity_id} a ete acceptee.",
    },
    "PECRefusee": {
        "notif_type": "warning",
        "title": "PEC refusee",
        "message_tpl": "La demande de PEC #{entity_id} a ete refusee.",
    },
    "PaiementRapproche": {
        "notif_type": "success",
        "title": "Rapprochement bancaire",
        "message_tpl": "Des paiements ont ete rapproches automatiquement.",
    },
    "EcartDetecte": {
        "notif_type": "warning",
        "title": "Ecart detecte",
        "message_tpl": "Un ecart a ete detecte lors du rapprochement #{entity_id}.",
    },
    "RelanceEnvoyee": {
        "notif_type": "info",
        "title": "Relance envoyee",
        "message_tpl": "Une relance a ete envoyee (#{entity_id}).",
    },
    "RelanceEchouee": {
        "notif_type": "warning",
        "title": "Relance echouee",
        "message_tpl": "L'envoi de la relance #{entity_id} a echoue.",
    },
    "PaiementApresRelance": {
        "notif_type": "success",
        "title": "Paiement apres relance",
        "message_tpl": "Un paiement a ete recu suite a la relance #{entity_id}.",
    },
    "CampagneLancee": {
        "notif_type": "success",
        "title": "Campagne lancee",
        "message_tpl": "La campagne marketing #{entity_id} a ete envoyee.",
    },
    "CampagneTerminee": {
        "notif_type": "info",
        "title": "Campagne terminee",
        "message_tpl": "La campagne #{entity_id} est terminee.",
    },
}


def emit_event(
    db: Session,
    tenant_id: int,
    event_type: str,
    entity_type: str,
    entity_id: int,
    user_id: int,
    data: dict | None = None,
) -> None:
    logger.info(
        "event_emitted",
        tenant_id=tenant_id,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
    )

    config = EVENT_CONFIG.get(event_type)
    if not config:
        return

    # TENANT ISOLATION: Always filter admins by tenant_id via the tenant_users
    # join table. Without this, notifications would leak to admins of other tenants.
    # tenant_id is required; if somehow missing, return early to avoid global broadcast.
    if not tenant_id:
        logger.warning("emit_event_no_tenant", event_type=event_type, entity_id=entity_id)
        return
    query = (
        select(User)
        .join(TenantUser, TenantUser.user_id == User.id)
        .where(
            User.role.in_(["admin", "owner"]),
            User.is_active.is_(True),
            TenantUser.tenant_id == tenant_id,
        )
    )
    admin_users = db.scalars(query).all()

    message = config["message_tpl"].format(entity_id=entity_id)

    for admin in admin_users:
        notification_service.notify(
            db,
            tenant_id=tenant_id,
            user_id=admin.id,
            type=config["notif_type"],
            title=config["title"],
            message=message,
            entity_type=entity_type,
            entity_id=entity_id,
        )
