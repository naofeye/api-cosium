from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.domain.schemas.marketing import ConsentResponse, ConsentUpdate
from app.repositories import marketing_repo
from app.services import audit_service

logger = get_logger("consent_service")


def get_consents(db: Session, tenant_id: int, client_id: int) -> list[ConsentResponse]:
    consents = marketing_repo.get_consents(db, client_id=client_id, tenant_id=tenant_id)
    return [ConsentResponse.model_validate(c) for c in consents]


def update_consent(
    db: Session,
    tenant_id: int,
    client_id: int,
    channel: str,
    payload: ConsentUpdate,
    user_id: int,
) -> ConsentResponse:
    consent = marketing_repo.upsert_consent(
        db,
        tenant_id,
        client_id,
        channel,
        payload.consented,
        payload.source,
    )
    if user_id:
        audit_service.log_action(
            db,
            tenant_id,
            user_id,
            "update",
            "marketing_consent",
            consent.id,
            new_value={"channel": channel, "consented": payload.consented},
        )
    logger.info(
        "consent_updated", tenant_id=tenant_id, client_id=client_id, channel=channel, consented=payload.consented
    )
    return ConsentResponse.model_validate(consent)


def check_consent(db: Session, tenant_id: int, client_id: int, channel: str) -> bool:
    return marketing_repo.check_consent(db, client_id=client_id, channel=channel, tenant_id=tenant_id)
