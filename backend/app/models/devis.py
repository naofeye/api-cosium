from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Devis(Base):
    __tablename__ = "devis"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), nullable=False, index=True)
    numero: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="brouillon", index=True)
    montant_ht: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    tva: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    montant_ttc: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    part_secu: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    part_mutuelle: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    reste_a_charge: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, onupdate=lambda: datetime.now(UTC))

    case: Mapped["Case"] = relationship("Case", back_populates="devis", lazy="noload")  # type: ignore[name-defined]  # noqa: F821


class DevisLigne(Base):
    __tablename__ = "devis_lignes"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    devis_id: Mapped[int] = mapped_column(ForeignKey("devis.id", ondelete="CASCADE"), nullable=False, index=True)
    designation: Mapped[str] = mapped_column(String(255), nullable=False)
    quantite: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    prix_unitaire_ht: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    taux_tva: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=20.0)
    montant_ht: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    montant_ttc: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
