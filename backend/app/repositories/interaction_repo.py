from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Interaction


def create(
    db: Session,
    tenant_id: int,
    client_id: int,
    case_id: int | None,
    type: str,
    direction: str,
    subject: str,
    content: str | None,
    created_by: int | None,
) -> Interaction:
    item = Interaction(
        tenant_id=tenant_id,
        client_id=client_id,
        case_id=case_id,
        type=type,
        direction=direction,
        subject=subject,
        content=content,
        created_by=created_by,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def list_by_client(
    db: Session, client_id: int, tenant_id: int, type: str | None = None, limit: int = 50, offset: int = 0
) -> tuple[list[Interaction], int]:
    q = select(Interaction).where(
        Interaction.client_id == client_id,
        Interaction.tenant_id == tenant_id,
    )
    if type:
        q = q.where(Interaction.type == type)
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.scalars(q.order_by(Interaction.created_at.desc()).limit(limit).offset(offset)).all()
    return list(rows), total


def list_by_case(db: Session, case_id: int, tenant_id: int) -> list[Interaction]:
    return list(
        db.scalars(
            select(Interaction)
            .where(
                Interaction.case_id == case_id,
                Interaction.tenant_id == tenant_id,
            )
            .order_by(Interaction.created_at.desc())
        ).all()
    )


def get_by_id(db: Session, interaction_id: int, tenant_id: int) -> Interaction | None:
    return db.scalars(
        select(Interaction).where(
            Interaction.id == interaction_id,
            Interaction.tenant_id == tenant_id,
        )
    ).first()


def delete(db: Session, interaction: Interaction) -> None:
    db.delete(interaction)
    db.commit()
