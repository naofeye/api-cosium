"""Modeles webhooks HTTP sortants.

Pattern : un tenant configure des `WebhookSubscription` (URL + event_types[]
+ secret HMAC). Sur chaque evenement metier interesse, on cree une
`WebhookDelivery` (status=pending) et on enqueue un job Celery qui POST
le payload signe (X-Webhook-Signature-256).

Les retries suivent un backoff exponentiel borne ([30s, 2m, 15m, 1h, 6h])
puis la delivery passe en `failed` et reste consultable via API admin.
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
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class WebhookSubscription(Base):
    """Souscription d'un tenant a un set d'event_types pour une URL cible."""

    __tablename__ = "webhook_subscriptions"
    __table_args__ = (
        Index("ix_webhook_subs_tenant_active", "tenant_id", "is_active"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    # Liste blanche d'evenements abonnes : ["facture.created", "client.created"]
    event_types: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    # Secret HMAC partage avec le client. Genere cote serveur, jamais expose
    # apres creation (UI affiche les 4 premiers caracteres puis ****).
    secret: Mapped[str] = mapped_column(String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    created_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    deliveries: Mapped[list["WebhookDelivery"]] = relationship(
        back_populates="subscription", cascade="all, delete-orphan"
    )


class WebhookDelivery(Base):
    """Une tentative de livraison d'un evenement vers une subscription.

    status :
    - pending : enqueue, pas encore tente
    - success : 2xx recu
    - retrying : echec recuperable, prochain retry programme
    - failed : retries epuises, abandon
    """

    __tablename__ = "webhook_deliveries"
    __table_args__ = (
        Index("ix_webhook_deliv_tenant_created", "tenant_id", "created_at"),
        Index("ix_webhook_deliv_status_next_retry", "status", "next_retry_at"),
        Index("ix_webhook_deliv_event_id", "event_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("webhook_subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    # event_id : cle d'idempotence cote consommateur. UUID4 par defaut. Si le
    # consommateur recoit deux fois le meme event_id, il doit dedupliquer.
    event_id: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False, index=True
    )

    subscription: Mapped[WebhookSubscription] = relationship(
        back_populates="deliveries"
    )
