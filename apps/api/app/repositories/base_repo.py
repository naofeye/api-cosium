"""Base repository avec operations CRUD generiques.

Heriter de BaseRepository pour eviter la duplication de code dans les repos.
Usage:
    class MyRepo(BaseRepository[MyModel]):
        model = MyModel

    repo = MyRepo()
    item = repo.get_by_id(db, item_id, tenant_id)
"""

from typing import Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.base import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """Repository de base avec operations CRUD generiques filtrees par tenant."""

    model: type[T]

    def get_by_id(self, db: Session, entity_id: int, tenant_id: int) -> T | None:
        return db.scalars(
            select(self.model).where(
                self.model.id == entity_id,
                self.model.tenant_id == tenant_id,
            )
        ).first()

    def get_all(
        self, db: Session, tenant_id: int, page: int = 1, page_size: int = 25
    ) -> tuple[list[T], int]:
        stmt = select(self.model).where(self.model.tenant_id == tenant_id)
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        items = db.scalars(
            stmt.offset((page - 1) * page_size).limit(page_size)
        ).all()
        return list(items), total

    def create(self, db: Session, tenant_id: int, **kwargs: object) -> T:
        entity = self.model(tenant_id=tenant_id, **kwargs)
        db.add(entity)
        db.flush()
        db.refresh(entity)
        return entity

    def delete(self, db: Session, entity: T) -> None:
        db.delete(entity)
        db.flush()
