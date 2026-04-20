from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.encryption import EncryptedString
from app.db.base import Base


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (Index("ix_customers_tenant_id", "tenant_id"),)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    cosium_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    last_name: Mapped[str] = mapped_column(String(120), nullable=False)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    customer_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(EncryptedString(500), nullable=True)
    street_number: Mapped[str | None] = mapped_column(EncryptedString(200), nullable=True)
    street_name: Mapped[str | None] = mapped_column(EncryptedString(500), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    social_security_number: Mapped[str | None] = mapped_column(EncryptedString(200), nullable=True)
    optician_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ophthalmologist_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    mobile_phone_country: Mapped[str | None] = mapped_column(String(10), nullable=True)
    site_id: Mapped[int | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, onupdate=lambda: datetime.now(UTC))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None, index=True)
