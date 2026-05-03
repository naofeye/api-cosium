"""Modele ApiToken : token API publique scope par tenant.

Le token brut (raw) n'est jamais stocke. On stocke `hashed_token =
sha256(raw)` et `prefix` (4 premiers caracteres pour identification UI).

Authentification : header `Authorization: Bearer <raw_token>`. Le service
hash le raw, lookup par `hashed_token`, verifie expiration + revoked + scope.
"""
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ApiToken(Base):
    __tablename__ = "api_tokens"
    __table_args__ = (
        Index("ix_api_tokens_tenant_revoked", "tenant_id", "revoked"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    # 4 premiers caracteres du raw token, pour identification visuelle
    # (ex: "opf_xxxx") sans exposer le secret.
    prefix: Mapped[str] = mapped_column(String(12), nullable=False)
    hashed_token: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    # Liste blanche : ["read:clients", "read:devis", ...]
    scopes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False
    )
    created_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
