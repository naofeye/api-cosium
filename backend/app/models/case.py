from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Case(Base):
    __tablename__ = "cases"
    __table_args__ = (Index("ix_cases_tenant_id", "tenant_id"),)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False, index=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)

    # Relationships for eager loading (selectinload)
    documents: Mapped[list["Document"]] = relationship("Document", back_populates="case", lazy="noload")  # type: ignore[name-defined]
    devis: Mapped[list["Devis"]] = relationship("Devis", back_populates="case", lazy="noload")  # type: ignore[name-defined]
    factures: Mapped[list["Facture"]] = relationship("Facture", back_populates="case", lazy="noload")  # type: ignore[name-defined]
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="case", lazy="noload")  # type: ignore[name-defined]
    pec_requests: Mapped[list["PecRequest"]] = relationship("PecRequest", back_populates="case", lazy="noload")  # type: ignore[name-defined]
