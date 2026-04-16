"""Model for client-mutuelle associations detected from Cosium data."""

from datetime import UTC, date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ClientMutuelle(Base):
    """Association client <-> mutuelle detectee ou saisie manuellement."""

    __tablename__ = "client_mutuelles"
    __table_args__ = (
        Index("ix_client_mutuelles_tenant_customer", "tenant_id", "customer_id"),
        Index("ix_client_mutuelles_tenant_mutuelle", "tenant_id", "mutuelle_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    mutuelle_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mutuelle_name: Mapped[str] = mapped_column(String(255), nullable=False)
    numero_adherent: Mapped[str | None] = mapped_column(String(100), nullable=True)
    type_beneficiaire: Mapped[str] = mapped_column(String(50), nullable=False, default="assure")
    date_debut: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_fin: Mapped[date | None] = mapped_column(Date, nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="cosium_tpp")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
