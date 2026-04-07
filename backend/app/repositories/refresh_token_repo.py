import hashlib
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import RefreshToken


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create(db: Session, token: str, user_id: int, expires_at: datetime) -> RefreshToken:
    rt = RefreshToken(token=_hash_token(token), user_id=user_id, expires_at=expires_at)
    db.add(rt)
    db.commit()
    db.refresh(rt)
    return rt


def get_by_token(db: Session, token: str) -> RefreshToken | None:
    return db.scalars(
        select(RefreshToken).where(
            RefreshToken.token == _hash_token(token),
            RefreshToken.revoked.is_(False),
        )
    ).first()


def revoke(db: Session, token: str) -> None:
    rt = db.scalars(
        select(RefreshToken).where(RefreshToken.token == _hash_token(token))
    ).first()
    if rt:
        rt.revoked = True
        db.commit()


def revoke_all_for_user(db: Session, user_id: int) -> None:
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False)
    ).update({"revoked": True})


def is_valid(rt: RefreshToken) -> bool:
    now = datetime.now(UTC)  # naive datetime for DB compatibility
    return not rt.revoked and rt.expires_at > now.replace(tzinfo=None)
