from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# Duree de validite par defaut d'un devis non signe (en jours).
# Norme metier opticien : 90 jours apres creation/envoi.
DEVIS_DEFAULT_VALIDITY_DAYS = 90


class Devis(Base):
    __tablename__ = "devis"
    __table_args__ = (
        Index("ix_devis_tenant_numero", "tenant_id", "numero", unique=True),
    )
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    numero: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="brouillon", index=True)
    montant_ht: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    tva: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    montant_ttc: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    part_secu: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    part_mutuelle: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    reste_a_charge: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    # Date a laquelle le devis cesse d'etre valide. Null = duree indeterminee
    # (ancien devis pre-feature). Nouveau : created_at + 90 jours par defaut.
    valid_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, onupdate=lambda: datetime.now(UTC))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)

    # Signature electronique (eIDAS Simple) — V1 clickwrap. Voir
    # services/devis_signature_service.py et migration e8f9a1b2c3d4.
    public_token: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True, index=True)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    signature_method: Mapped[str | None] = mapped_column(String(30), nullable=True)
    signature_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    signature_user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    signature_consent_text: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    case: Mapped["Case"] = relationship("Case", back_populates="devis", lazy="noload")  # type: ignore[name-defined]  # noqa: F821


class DevisLigne(Base):
    __tablename__ = "devis_lignes"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    devis_id: Mapped[int] = mapped_column(ForeignKey("devis.id", ondelete="CASCADE"), nullable=False, index=True)
    designation: Mapped[str] = mapped_column(String(255), nullable=False)
    quantite: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    prix_unitaire_ht: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    taux_tva: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=20.0)
    montant_ht: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    montant_ttc: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
