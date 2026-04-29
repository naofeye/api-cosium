"""Schemas Pydantic pour l'historique conversationnel du copilote IA."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AiMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    tokens_in: int | None = None
    tokens_out: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AiConversationListItem(BaseModel):
    id: int
    title: str
    mode: str
    case_id: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AiConversationDetail(AiConversationListItem):
    messages: list[AiMessageResponse] = []


class AiAppendRequest(BaseModel):
    """Append a message to a conversation. Si conversation_id=None, en cree une nouvelle."""

    question: str = Field(..., min_length=1, max_length=4000)
    conversation_id: int | None = None
    mode: str = Field("dossier", min_length=1, max_length=50)
    case_id: int | None = None


class AiAppendResponse(BaseModel):
    conversation_id: int
    answer: str
