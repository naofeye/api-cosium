"""Schemas for global search endpoint."""

from pydantic import BaseModel


class SearchResultItem(BaseModel):
    id: int
    type: str
    label: str
    detail: str = ""


class SearchResponse(BaseModel):
    clients: list[SearchResultItem] = []
    dossiers: list[SearchResultItem] = []
    devis: list[SearchResultItem] = []
    factures: list[SearchResultItem] = []
    cosium_factures: list[SearchResultItem] = []
    ordonnances: list[SearchResultItem] = []
