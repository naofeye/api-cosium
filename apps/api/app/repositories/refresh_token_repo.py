import hashlib
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import RefreshToken


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create(
    db: Session,
    token: str,
    user_id: int,
    expires_at: datetime,
    tenant_id: int | None = None,
) -> RefreshToken:
    rt = RefreshToken(
        token=_hash_token(token),
        user_id=user_id,
        tenant_id=tenant_id,
        expires_at=expires_at,
    )
    db.add(rt)
    db.flush()
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
        db.flush()


def revoke_all_for_user(db: Session, user_id: int) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False))
        .values(revoked=True)
    )


def is_valid(rt: RefreshToken) -> bool:
    now = datetime.now(UTC)  # naive datetime for DB compatibility
    return not rt.revoked and rt.expires_at > now.replace(tzinfo=None)


def list_active_for_user(db: Session, user_id: int) -> list[RefreshToken]:
    """Sessions actives (non revokes, non expires) triees du plus recent au plus ancien."""
    now = datetime.now(UTC).replace(tzinfo=None)
    return list(
        db.scalars(
            select(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked.is_(False),
                RefreshToken.expires_at > now,
            )
            .order_by(RefreshToken.created_at.desc())
        )
    )


def revoke_by_id(db: Session, user_id: int, session_id: int) -> bool:
    """Revoque une session precise. Renvoie False si non trouvee ou n'appartient pas a l'user."""
    rt = db.scalars(
        select(RefreshToken).where(RefreshToken.id == session_id, RefreshToken.user_id == user_id)
    ).first()
    if not rt:
        return False
    rt.revoked = True
    db.flush()
    return True


def purge_orphans(db: Session, keep_days: int = 30) -> int:
    """Supprime les tokens revokes ou expires depuis plus de keep_days jours.

    Retourne le nombre de lignes supprimees.
    """
    from datetime import timedelta

    from sqlalchemy import delete, or_

    cutoff = (datetime.now(UTC) - timedelta(days=keep_days)).replace(tzinfo=None)
    result = db.execute(
        delete(RefreshToken).where(
            or_(RefreshToken.revoked.is_(True), RefreshToken.expires_at < cutoff),
            RefreshToken.created_at < cutoff,
        )
    )
    return result.rowcount or 0
