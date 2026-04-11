from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalars(select(User).where(User.email == email)).first()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.scalars(select(User).where(User.id == user_id)).first()


def create(db: Session, email: str, password_hash: str, role: str, is_active: bool = True) -> User:
    user = User(email=email, password_hash=password_hash, role=role, is_active=is_active)
    db.add(user)
    db.flush()
    return user
