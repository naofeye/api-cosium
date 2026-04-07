"""Repository for batch operations and their items."""

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.batch_operation import BatchOperation, BatchOperationItem


def create_batch(
    db: Session,
    tenant_id: int,
    marketing_code: str,
    label: str | None,
    created_by: int,
    total_clients: int = 0,
) -> BatchOperation:
    batch = BatchOperation(
        tenant_id=tenant_id,
        marketing_code=marketing_code,
        label=label,
        created_by=created_by,
        total_clients=total_clients,
    )
    db.add(batch)
    db.flush()
    return batch


def create_item(
    db: Session,
    batch_id: int,
    customer_id: int,
) -> BatchOperationItem:
    item = BatchOperationItem(
        batch_id=batch_id,
        customer_id=customer_id,
    )
    db.add(item)
    db.flush()
    return item


def get_batch_by_id(
    db: Session, batch_id: int, tenant_id: int
) -> BatchOperation | None:
    return db.scalars(
        select(BatchOperation).where(
            BatchOperation.id == batch_id,
            BatchOperation.tenant_id == tenant_id,
        )
    ).first()


def list_batches(
    db: Session,
    tenant_id: int,
    limit: int = 25,
    offset: int = 0,
) -> list[BatchOperation]:
    return list(
        db.scalars(
            select(BatchOperation)
            .where(BatchOperation.tenant_id == tenant_id)
            .order_by(BatchOperation.started_at.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    )


def count_batches(db: Session, tenant_id: int) -> int:
    return db.scalar(
        select(func.count()).select_from(BatchOperation).where(
            BatchOperation.tenant_id == tenant_id
        )
    ) or 0


def get_items_by_batch(
    db: Session, batch_id: int
) -> list[BatchOperationItem]:
    return list(
        db.scalars(
            select(BatchOperationItem)
            .where(BatchOperationItem.batch_id == batch_id)
            .order_by(BatchOperationItem.id)
        ).all()
    )


def get_items_by_status(
    db: Session, batch_id: int, status: str
) -> list[BatchOperationItem]:
    return list(
        db.scalars(
            select(BatchOperationItem).where(
                BatchOperationItem.batch_id == batch_id,
                BatchOperationItem.status == status,
            )
        ).all()
    )


def update_item(
    db: Session,
    item_id: int,
    **kwargs: object,
) -> None:
    db.execute(
        update(BatchOperationItem)
        .where(BatchOperationItem.id == item_id)
        .values(**kwargs)
    )
    db.flush()


def update_batch(
    db: Session,
    batch_id: int,
    **kwargs: object,
) -> None:
    db.execute(
        update(BatchOperation)
        .where(BatchOperation.id == batch_id)
        .values(**kwargs)
    )
    db.flush()
