import hashlib
from datetime import UTC, datetime

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
    return (
        db.query(RefreshToken)
        .filter(
            RefreshToken.token == _hash_token(token),
            RefreshToken.revoked.is_(False),
        )
        .first()
    )


def revoke(db: Session, token: str) -> None:
    rt = db.query(RefreshToken).filter(RefreshToken.token == _hash_token(token)).first()
    if rt:
        rt.revoked = True
        db.commit()


def is_valid(rt: RefreshToken) -> bool:
    now = datetime.now(UTC).replace(tzinfo=None)
    return not rt.revoked and rt.expires_at > now
