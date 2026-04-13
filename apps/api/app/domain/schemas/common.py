"""Schemas reutilisables : reponses paginees, wrappers, enveloppes."""
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Enveloppe standard pour toute reponse paginee.

    Exemple :
        @router.get("/items", response_model=PaginatedResponse[ItemResponse])
        def list_items(...) -> PaginatedResponse[ItemResponse]:
            items, total = repo.list_with_count(...)
            return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)
    """

    items: list[T]
    total: int = Field(..., ge=0, description="Nombre total d'items (toutes pages)")
    page: int = Field(..., ge=1, description="Page courante (1-indexed)")
    page_size: int = Field(..., ge=1, le=500, description="Nombre d'items par page")

    model_config = ConfigDict(from_attributes=True)

    @property
    def total_pages(self) -> int:
        if self.page_size <= 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size


class MessageResponse(BaseModel):
    """Reponse simple pour endpoints qui ne retournent qu'un message (delete, toggle, etc.)."""

    message: str
    detail: str | None = None
