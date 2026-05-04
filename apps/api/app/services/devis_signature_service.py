"""Service signature electronique devis (eIDAS Simple).

Flux :
1. Admin appelle `generate_public_signature_link(devis_id)` -> retourne URL
   `/devis/sign/<public_token>` envoyable par email au client.
2. Le client ouvre le lien (page publique sans login), valide la signature
   en cliquant + acceptant le texte de consentement.
3. Le frontend POST `/api/public/v1/devis/{public_token}/sign` avec le
   texte de consentement + capture l'IP/UA.
4. Le service valide (token actif, devis non signe), persiste la signature,
   change status -> "signe", emit event devis.signed (-> webhook).

Securite :
- Le public_token est un UUID v4, single-use (pas de re-signature)
- IP + User-Agent stockes pour audit
- Texte de consentement copie tel quel (preuve juridique)
- Signature sur devis en status != "signe" uniquement (idempotence)
"""
from __future__ import annotations

import secrets
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError, NotFoundError
from app.core.logging import get_logger
from app.domain.schemas.devis import DevisResponse
from app.models.devis import Devis
from app.repositories import devis_repo
from app.services import audit_service, event_service, webhook_emit_helpers

logger = get_logger("devis_signature_service")

DEFAULT_CONSENT_TEXT = (
    "En cliquant sur ACCEPTER, je confirme avoir pris connaissance du "
    "devis et l'accepte sans reserve. Cette acceptation a la meme valeur "
    "qu'une signature manuscrite (signature electronique simple, "
    "reglement eIDAS UE 910/2014)."
)


def generate_public_token() -> str:
    """UUID v4 hex (32 chars). Suffisant pour URL publique non-devinable."""
    return secrets.token_hex(16)


def ensure_public_link(
    db: Session, tenant_id: int, devis_id: int, user_id: int
) -> str:
    """Genere ou retourne le public_token existant pour un devis.

    Le devis doit etre en status `envoye` ou `brouillon` (pas deja signe
    ou refuse). Idempotent : si token existe deja, retourne celui-la.
    """
    devis = devis_repo.get_by_id(db, devis_id=devis_id, tenant_id=tenant_id)
    if devis is None:
        raise NotFoundError("devis", devis_id)
    if devis.status in {"signe", "refuse", "facture", "annule"}:
        raise BusinessError(
            f"Devis en status '{devis.status}' : signature electronique impossible.",
            code="DEVIS_NOT_SIGNABLE",
        )

    if not devis.public_token:
        devis.public_token = generate_public_token()
        db.commit()
        if user_id:
            audit_service.log_action(
                db,
                tenant_id,
                user_id,
                "generate_signature_link",
                "devis",
                devis_id,
            )

    logger.info(
        "devis_public_link_generated",
        tenant_id=tenant_id,
        devis_id=devis_id,
        user_id=user_id,
    )
    return devis.public_token


def get_devis_by_public_token(db: Session, public_token: str) -> Devis | None:
    """Lookup public sans context tenant (pour la page de signature)."""
    if not public_token:
        return None
    return db.query(Devis).filter(Devis.public_token == public_token).first()


def sign_devis_public(
    db: Session,
    *,
    public_token: str,
    consent_text: str,
    client_ip: str | None,
    user_agent: str | None,
) -> DevisResponse:
    """Signature electronique via lien public.

    - Lookup par public_token
    - Verifie statut signable
    - Persiste signed_at + signature_*
    - Status -> "signe"
    - Emit webhook devis.signed
    """
    devis = get_devis_by_public_token(db, public_token)
    if devis is None:
        raise NotFoundError("devis", public_token)

    if devis.status in {"signe", "facture"}:
        raise BusinessError(
            "Ce devis a deja ete signe.",
            code="DEVIS_ALREADY_SIGNED",
        )
    if devis.status in {"refuse", "annule", "expire"}:
        raise BusinessError(
            f"Devis en status '{devis.status}' : signature impossible.",
            code="DEVIS_NOT_SIGNABLE",
        )
    # Defense en profondeur : meme si la task Celery d'expiration n'a pas
    # encore tourne (elle s'execute toutes les 3h15), refuser les devis
    # dont valid_until est passe. Couvre la fenetre entre J+validity et le
    # prochain cron, durant laquelle le devis n'a pas encore le status
    # 'expire' mais est materiellement perime.
    valid_until = devis.valid_until
    if valid_until is not None:
        now = datetime.now(UTC).replace(tzinfo=None)
        # valid_until est typed datetime, mais defensif : si SQLite retourne
        # un date pur, on combine avec min.time() pour comparer.
        if not isinstance(valid_until, datetime):
            from datetime import datetime as _dt

            valid_until = _dt.combine(valid_until, _dt.min.time())
        if valid_until < now:
            raise BusinessError(
                "Ce devis a expire et ne peut plus etre signe.",
                code="DEVIS_EXPIRED",
            )

    devis.signed_at = datetime.now(UTC).replace(tzinfo=None)
    devis.signature_method = "clickwrap"
    devis.signature_ip = (client_ip or "")[:64]
    devis.signature_user_agent = (user_agent or "")[:500]
    devis.signature_consent_text = consent_text or DEFAULT_CONSENT_TEXT
    devis.status = "signe"
    db.commit()
    db.refresh(devis)

    response = DevisResponse.model_validate(devis)
    # Audit + event interne (pas de user_id : signature publique)
    try:
        audit_service.log_action(
            db,
            devis.tenant_id,
            user_id=0,
            action="sign_public",
            entity_type="devis",
            entity_id=devis.id,
            new_value={
                "signature_method": "clickwrap",
                "signature_ip": devis.signature_ip,
                "signed_at": devis.signed_at.isoformat() if devis.signed_at else None,
            },
        )
        event_service.emit_event(
            db, devis.tenant_id, "DevisSigne", "devis", devis.id, user_id=0
        )
        webhook_emit_helpers.emit_devis_status_changed(
            db, devis.tenant_id, response, "signe"
        )
    except Exception as exc:
        # Best-effort : la signature est persistee, le reste ne doit pas
        # echouer la transaction.
        logger.warning(
            "devis_sign_post_actions_failed",
            devis_id=devis.id,
            error=str(exc),
        )

    logger.info(
        "devis_signed_public",
        tenant_id=devis.tenant_id,
        devis_id=devis.id,
        ip=devis.signature_ip,
    )
    return response
