"""Routes de lecture des notes CRM Cosium — LECTURE SEULE.

Permet d'integrer l'historique CRM dans la fiche client OptiFlow.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.notes import CosiumNoteResponse
from app.integrations.cosium.adapter import cosium_note_to_optiflow
from app.integrations.cosium.cosium_connector import CosiumConnector
from app.services.erp_auth_service import _authenticate_connector, _get_connector_for_tenant

router = APIRouter(prefix="/api/v1/cosium/notes", tags=["cosium-notes"])


def _get_cosium_connector(db: Session, tenant_id: int) -> CosiumConnector:
    connector, tenant = _get_connector_for_tenant(db, tenant_id)
    if not isinstance(connector, CosiumConnector):
        from app.core.exceptions import BusinessError
        raise BusinessError("Le tenant n'utilise pas Cosium comme ERP")
    _authenticate_connector(connector, tenant)
    return connector


@router.get(
    "/customer/{customer_cosium_id}",
    response_model=list[CosiumNoteResponse],
    summary="Notes CRM d'un client",
    description="Liste les notes CRM Cosium d'un client (historique).",
)
def list_for_customer(
    customer_cosium_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[CosiumNoteResponse]:
    connector = _get_cosium_connector(db, tenant_ctx.tenant_id)
    items = connector.list_notes_for_customer(customer_cosium_id)
    return [CosiumNoteResponse(**cosium_note_to_optiflow(n)) for n in items]


@router.get(
    "/statuses",
    summary="Statuts de notes",
    description="Reference des statuts possibles pour une note.",
)
def list_statuses(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[dict]:
    connector = _get_cosium_connector(db, tenant_ctx.tenant_id)
    return connector.list_note_statuses()


@router.get(
    "/{note_id}",
    response_model=CosiumNoteResponse,
    summary="Detail d'une note",
)
def get_note(
    note_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> CosiumNoteResponse:
    connector = _get_cosium_connector(db, tenant_ctx.tenant_id)
    raw = connector.get_note(note_id)
    return CosiumNoteResponse(**cosium_note_to_optiflow(raw))
