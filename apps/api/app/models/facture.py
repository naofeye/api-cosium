from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Facture(Base):
    __tablename__ = "factures"
    __table_args__ = (
        Index("ix_factures_tenant_id", "tenant_id"),
        Index("ix_factures_tenant_numero", "tenant_id", "numero", unique=True),
        Index("ix_factures_tenant_status", "tenant_id", "status"),
    )
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), nullable=False, index=True)
    devis_id: Mapped[int] = mapped_column(ForeignKey("devis.id"), nullable=False, index=True)
    numero: Mapped[str] = mapped_column(String(50), nullable=False)
    date_emission: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    montant_ht: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    tva: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    montant_ttc: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="emise", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    case: Mapped["Case"] = relationship("Case", back_populates="factures", lazy="noload")  # type: ignore[name-defined]  # noqa: F821


class FactureLigne(Base):
    __tablename__ = "facture_lignes"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    facture_id: Mapped[int] = mapped_column(ForeignKey("factures.id", ondelete="CASCADE"), nullable=False, index=True)
    designation: Mapped[str] = mapped_column(String(255), nullable=False)
    quantite: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    prix_unitaire_ht: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    taux_tva: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=20.0)
    montant_ht: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    montant_ttc: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
