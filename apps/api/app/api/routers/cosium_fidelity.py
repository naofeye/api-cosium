"""Routes de lecture cartes de fidelite + parrainages + recherche fuzzy Cosium — LECTURE SEULE."""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
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


class CosiumCustomerLoose(BaseModel):
    """Resultat de recherche fuzzy client Cosium (live)."""
    cosium_id: int | None = None
    customer_number: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    birth_date: str | None = None


def _get_cosium_connector(db: Session, tenant_id: int) -> CosiumConnector:
    connector, tenant = _get_connector_for_tenant(db, tenant_id)
    if not isinstance(connector, CosiumConnector):
        from app.core.exceptions import BusinessError
        raise BusinessError("Le tenant n'utilise pas Cosium comme ERP")
    _authenticate_connector(connector, tenant)
    return connector


@router.get(
    "/search",
    response_model=list[CosiumCustomerLoose],
    summary="Recherche fuzzy clients Cosium",
    description="Recherche par nom, prenom ou numero client (matching approximatif). Au moins un parametre requis.",
)
def search_customers_loose(
    last_name: str | None = Query(None, min_length=1),
    first_name: str | None = Query(None, min_length=1),
    customer_number: str | None = Query(None, min_length=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[CosiumCustomerLoose]:
    if not (last_name or first_name or customer_number):
        from app.core.exceptions import ValidationError
        raise ValidationError("Au moins un parametre est requis : last_name, first_name ou customer_number")
    connector = _get_cosium_connector(db, tenant_ctx.tenant_id)
    try:
        raw = connector.search_customers_loose(
            last_name=last_name, first_name=first_name,
            customer_number=customer_number, page_size=page_size,
        )
    except Exception as e:
        from app.core.exceptions import ExternalServiceError
        raise ExternalServiceError(f"Recherche Cosium indisponible : {str(e)[:100]}")
    result: list[CosiumCustomerLoose] = []
    for c in raw:
        cid_raw = c.get("id") or c.get("cosiumId")
        cid = None
        if cid_raw:
            try: cid = int(cid_raw)
            except (ValueError, TypeError): pass
        result.append(CosiumCustomerLoose(
            cosium_id=cid,
            customer_number=str(c.get("customerNumber", "") or "") or None,
            first_name=c.get("firstName"),
            last_name=c.get("lastName"),
            email=c.get("email"),
            phone=c.get("mobilePhoneNumber") or c.get("phoneNumber"),
            birth_date=c.get("birthDate"),
        ))
    return result


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
