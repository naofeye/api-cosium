"""Service generique pour les requetes paginee/filtrees sur les donnees de reference Cosium.

Centralise les patterns de query repetes dans le router cosium_reference.
"""

from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel
from sqlalchemy import BinaryExpression, ColumnElement, UnaryExpression, func, or_, select
from sqlalchemy.orm import Session


class PaginatedResult(BaseModel):
    """Resultat pagine generique."""

    items: list[Any]
    total: int
    page: int
    page_size: int


def paginated_query(
    db: Session,
    model: type,
    tenant_id: int,
    page: int,
    page_size: int,
    *,
    order_by: list[UnaryExpression | Any] | None = None,
    filters: list[ColumnElement[bool] | BinaryExpression[bool]] | None = None,
    response_schema: type[BaseModel] | None = None,
) -> dict[str, Any]:
    """Execute une requete paginee avec filtres optionnels.

    Args:
        db: Session SQLAlchemy.
        model: Modele SQLAlchemy (doit avoir tenant_id et id).
        tenant_id: ID du tenant pour le filtrage RLS.
        page: Numero de page (1-based).
        page_size: Nombre d'elements par page.
        order_by: Liste de clauses ORDER BY.
        filters: Liste de filtres WHERE supplementaires.
        response_schema: Schema Pydantic pour valider chaque item (optionnel).

    Returns:
        Dict avec items, total, page, page_size.
    """
    base_where = model.tenant_id == tenant_id

    query = select(model).where(base_where)
    count_query = select(func.count(model.id)).where(base_where)

    if filters:
        for f in filters:
            query = query.where(f)
            count_query = count_query.where(f)

    if order_by:
        query = query.order_by(*order_by)

    total = db.scalar(count_query) or 0
    offset = (page - 1) * page_size
    items = db.scalars(query.offset(offset).limit(page_size)).all()

    if response_schema:
        items = [response_schema.model_validate(i) for i in items]

    return {"items": items, "total": total, "page": page, "page_size": page_size}


def list_all(
    db: Session,
    model: type,
    tenant_id: int,
    *,
    order_by: list[UnaryExpression | Any] | None = None,
    response_schema: type[BaseModel] | None = None,
) -> Sequence[Any]:
    """Liste tous les elements d'un modele pour un tenant (sans pagination).

    Args:
        db: Session SQLAlchemy.
        model: Modele SQLAlchemy.
        tenant_id: ID du tenant.
        order_by: Clauses ORDER BY.
        response_schema: Schema Pydantic pour valider chaque item (optionnel).

    Returns:
        Liste d'items (valides par le schema si fourni, sinon ORM bruts).
    """
    query = select(model).where(model.tenant_id == tenant_id)
    if order_by:
        query = query.order_by(*order_by)
    items = db.scalars(query).all()
    if response_schema:
        return [response_schema.model_validate(i) for i in items]
    return items


def ilike_filter(column: Any, search: str) -> ColumnElement[bool]:
    """Cree un filtre ILIKE sur une colonne."""
    return column.ilike(f"%{search}%")


def multi_ilike_filter(columns: list[Any], search: str) -> ColumnElement[bool]:
    """Cree un filtre OR de ILIKE sur plusieurs colonnes."""
    pattern = f"%{search}%"
    return or_(*[col.ilike(pattern) for col in columns])
