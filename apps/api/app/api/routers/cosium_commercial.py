"""Routes de lecture des operations commerciales Cosium — LECTURE SEULE.

Note : Cosium expose /vouchers et /carts uniquement en PUT/DELETE — INTERDIT
par notre charte. Seuls les /advantages (GET) sont disponibles.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.commercial import AdvantageResponse
from app.integrations.cosium.adapter import cosium_advantage_to_optiflow
from app.integrations.cosium.cosium_connector import CosiumConnector
from app.services.erp_auth_service import _authenticate_connector, _get_connector_for_tenant

router = APIRouter(prefix="/api/v1/cosium/commercial-operations", tags=["cosium-commercial"])


def _get_cosium_connector(db: Session, tenant_id: int) -> CosiumConnector:
    connector, tenant = _get_connector_for_tenant(db, tenant_id)
    if not isinstance(connector, CosiumConnector):
        from app.core.exceptions import BusinessError
        raise BusinessError("Le tenant n'utilise pas Cosium comme ERP")
    _authenticate_connector(connector, tenant)
    return connector


@router.get(
    "/{operation_id}/advantages",
    response_model=list[AdvantageResponse],
    summary="Avantages d'une operation commerciale",
)
def list_advantages(
    operation_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[AdvantageResponse]:
    connector = _get_cosium_connector(db, tenant_ctx.tenant_id)
    items = connector.list_commercial_operation_advantages(operation_id)
    return [AdvantageResponse(**cosium_advantage_to_optiflow(a)) for a in items]


@router.get(
    "/{operation_id}/advantages/{advantage_id}",
    response_model=AdvantageResponse,
    summary="Detail d'un avantage commercial",
)
def get_advantage(
    operation_id: int,
    advantage_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> AdvantageResponse:
    connector = _get_cosium_connector(db, tenant_ctx.tenant_id)
    raw = connector.get_commercial_operation_advantage(operation_id, advantage_id)
    return AdvantageResponse(**cosium_advantage_to_optiflow(raw))
