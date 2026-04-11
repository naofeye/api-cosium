from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PayerOrgCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., pattern="^(mutuelle|secu)$")
    code: str = Field(..., min_length=1, max_length=50)
    contact_email: str | None = None


class PayerOrgResponse(BaseModel):
    id: int
    name: str
    type: str
    code: str
    contact_email: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PecCreate(BaseModel):
    case_id: int
    organization_id: int
    facture_id: int | None = None
    montant_demande: float = Field(..., ge=0)


class PecStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(soumise|en_attente|acceptee|refusee|partielle|cloturee)$")
    montant_accorde: float | None = Field(None, ge=0)
    comment: str | None = Field(None, max_length=500)


class PecStatusHistoryResponse(BaseModel):
    id: int
    old_status: str
    new_status: str
    comment: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PecResponse(BaseModel):
    id: int
    case_id: int
    organization_id: int
    facture_id: int | None = None
    montant_demande: float
    montant_accorde: float | None = None
    status: str
    created_at: datetime
    organization_name: str | None = None
    customer_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PecDetail(PecResponse):
    history: list[PecStatusHistoryResponse] = []


class RelanceCreate(BaseModel):
    type: str = Field(..., pattern="^(email|courrier|telephone)$")
    contenu: str | None = None


class RelanceResponse(BaseModel):
    id: int
    pec_request_id: int
    type: str
    date_envoi: datetime
    contenu: str | None = None
    created_by: int

    model_config = ConfigDict(from_attributes=True)
