from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DocumentType(Base):
    __tablename__ = "document_types"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False, default="general")
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    applies_to_case_type: Mapped[str | None] = mapped_column(String(80), nullable=True)


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_tenant_uploaded_at", "tenant_id", "uploaded_at"),
    )
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(80), nullable=False)
    document_type_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("document_types.id", ondelete="SET NULL"), nullable=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    case: Mapped["Case"] = relationship("Case", back_populates="documents", lazy="noload")  # type: ignore[name-defined]  # noqa: F821
