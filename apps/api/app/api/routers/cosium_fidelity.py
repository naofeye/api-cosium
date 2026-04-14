"""Routes de lecture cartes de fidelite + parrainages Cosium — LECTURE SEULE."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.fidelity import FidelityCardResponse, SponsorshipResponse
from app.integrations.cosium.adapter import (
    cosium_fidelity_card_to_optiflow,
    cosium_sponsorship_to_optiflow,
)
from app.integrations.cosium.cosium_connector import CosiumConnector
from app.services.erp_auth_service import _authenticate_connector, _get_connector_for_tenant

router = APIRouter(prefix="/api/v1/cosium/customers", tags=["cosium-fidelity"])


def _get_cosium_connector(db: Session, tenant_id: int) -> CosiumConnector:
    connector, tenant = _get_connector_for_tenant(db, tenant_id)
    if not isinstance(connector, CosiumConnector):
        from app.core.exceptions import BusinessError
        raise BusinessError("Le tenant n'utilise pas Cosium comme ERP")
    _authenticate_connector(connector, tenant)
    return connector


@router.get(
    "/{customer_cosium_id}/fidelity-cards",
    response_model=list[FidelityCardResponse],
    summary="Cartes de fidelite d'un client",
)
def list_fidelity_cards(
    customer_cosium_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[FidelityCardResponse]:
    connector = _get_cosium_connector(db, tenant_ctx.tenant_id)
    items = connector.list_customer_fidelity_cards(customer_cosium_id)
    return [FidelityCardResponse(**cosium_fidelity_card_to_optiflow(c)) for c in items]


@router.get(
    "/{customer_cosium_id}/sponsorships",
    response_model=list[SponsorshipResponse],
    summary="Parrainages d'un client",
)
def list_sponsorships(
    customer_cosium_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[SponsorshipResponse]:
    connector = _get_cosium_connector(db, tenant_ctx.tenant_id)
    items = connector.list_customer_sponsorships(customer_cosium_id)
    return [SponsorshipResponse(**cosium_sponsorship_to_optiflow(s)) for s in items]
