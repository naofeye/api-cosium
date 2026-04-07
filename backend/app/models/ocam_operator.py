"""Model for OCAM operators (mutuelles/complementaires).

Stores operator-specific rules for PEC preparation: which fields
are required, which documents must be attached, and any specific
validation rules.
"""

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OcamOperator(Base):
    """An OCAM operator with specific PEC requirements."""

    __tablename__ = "ocam_operators"
    __table_args__ = (
        Index("ix_ocam_operator_tenant", "tenant_id"),
        Index("ix_ocam_operator_code", "tenant_id", "code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id"), nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    portal_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Required fields for this operator (JSON array of field names)
    required_fields: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Required documents (JSON array of document roles)
    required_documents: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Specific rules (JSON dict)
    specific_rules: Mapped[str | None] = mapped_column(Text, nullable=True)

    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, onupdate=lambda: datetime.now(UTC),
    )
