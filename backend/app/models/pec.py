from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PayerOrganization(Base):
    __tablename__ = "payer_organizations"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)


class PayerContract(Base):
    __tablename__ = "payer_contracts"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("payer_organizations.id"), nullable=False, index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False, index=True)
    numero_adherent: Mapped[str] = mapped_column(String(100), nullable=False)


class PecRequest(Base):
    __tablename__ = "pec_requests"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), nullable=False, index=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("payer_organizations.id"), nullable=False, index=True)
    facture_id: Mapped[int | None] = mapped_column(ForeignKey("factures.id"), nullable=True, index=True)
    montant_demande: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    montant_accorde: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="soumise", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    case: Mapped["Case"] = relationship("Case", back_populates="pec_requests", lazy="noload")  # type: ignore[name-defined]


class PecStatusHistory(Base):
    __tablename__ = "pec_status_history"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    pec_request_id: Mapped[int] = mapped_column(ForeignKey("pec_requests.id"), nullable=False, index=True)
    old_status: Mapped[str] = mapped_column(String(30), nullable=False)
    new_status: Mapped[str] = mapped_column(String(30), nullable=False)
    comment: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


class Relance(Base):
    __tablename__ = "relances"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    pec_request_id: Mapped[int] = mapped_column(ForeignKey("pec_requests.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    date_envoi: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    contenu: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
