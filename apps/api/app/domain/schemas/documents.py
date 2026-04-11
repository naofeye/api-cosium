from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    id: int
    type: str
    filename: str
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)
