"""Service de calcul du score de completude des fiches clients."""

from sqlalchemy import func as sa_func, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.domain.schemas.clients import ClientCompletenessScore
from app.models.client import Customer
from app.models.client_mutuelle import ClientMutuelle
from app.models.cosium_data import CosiumDocument, CosiumInvoice, CosiumPrescription

logger = get_logger("client_completeness_service")


def calculate_client_completeness(
    db: Session, customer: Customer, tenant_id: int
) -> ClientCompletenessScore:
    """Calculate data completeness percentage for a client.

    Evaluates profile fields and linked data presence.
    """
    fields: dict[str, bool] = {
        "email": bool(customer.email),
        "phone": bool(customer.phone),
        "birth_date": bool(customer.birth_date),
        "address": bool(customer.address or customer.street_name),
        "social_security_number": bool(customer.social_security_number),
        "cosium_id": bool(customer.cosium_id),
        "city": bool(customer.city),
        "postal_code": bool(customer.postal_code),
    }

    score = sum(fields.values()) / len(fields) * 100 if fields else 0
    return ClientCompletenessScore(score=round(score, 1), fields=fields)


def calculate_client_completeness_full(
    db: Session, customer: Customer, tenant_id: int
) -> ClientCompletenessScore:
    """Calculate full completeness including linked data (invoices, prescriptions, etc.).

    More expensive query - use for detail views, not lists.
    """
    customer_id = customer.id

    invoice_count = db.scalar(
        select(sa_func.count()).select_from(CosiumInvoice).where(
            CosiumInvoice.tenant_id == tenant_id,
            CosiumInvoice.customer_id == customer_id,
        )
    ) or 0

    prescription_count = db.scalar(
        select(sa_func.count()).select_from(CosiumPrescription).where(
            CosiumPrescription.tenant_id == tenant_id,
            CosiumPrescription.customer_id == customer_id,
        )
    ) or 0

    document_count = 0
    if customer.cosium_id:
        document_count = db.scalar(
            select(sa_func.count()).select_from(CosiumDocument).where(
                CosiumDocument.tenant_id == tenant_id,
                CosiumDocument.customer_cosium_id == int(customer.cosium_id),
            )
        ) or 0

    mutuelle_count = db.scalar(
        select(sa_func.count()).select_from(ClientMutuelle).where(
            ClientMutuelle.tenant_id == tenant_id,
            ClientMutuelle.customer_id == customer_id,
        )
    ) or 0

    fields: dict[str, bool] = {
        "email": bool(customer.email),
        "phone": bool(customer.phone),
        "birth_date": bool(customer.birth_date),
        "address": bool(customer.address or customer.street_name),
        "social_security_number": bool(customer.social_security_number),
        "cosium_id": bool(customer.cosium_id),
        "city": bool(customer.city),
        "postal_code": bool(customer.postal_code),
        "has_invoices": invoice_count > 0,
        "has_prescriptions": prescription_count > 0,
        "has_documents": document_count > 0,
        "has_mutuelle": mutuelle_count > 0,
        "has_optician": bool(customer.optician_name),
    }

    score = sum(fields.values()) / len(fields) * 100 if fields else 0
    return ClientCompletenessScore(score=round(score, 1), fields=fields)
