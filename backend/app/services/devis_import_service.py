"""Service to import Cosium QUOTE invoices as OptiFlow Devis records.

Converts CosiumInvoice records of type QUOTE into Devis + DevisLigne,
linking them to existing cases or creating new ones as needed.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.case import Case
from app.models.cosium_data import CosiumInvoice
from app.models.devis import Devis, DevisLigne

logger = get_logger("devis_import_service")

# TVA rate for optical equipment in France
TVA_TAUX = 20.0


def _find_or_create_case(
    db: Session,
    tenant_id: int,
    customer_id: int,
) -> Case:
    """Find the most recent active case for a customer, or create one."""
    case = db.scalars(
        select(Case)
        .where(
            Case.customer_id == customer_id,
            Case.tenant_id == tenant_id,
            Case.deleted_at.is_(None),
        )
        .order_by(Case.created_at.desc())
        .limit(1)
    ).first()

    if case:
        return case

    case = Case(
        tenant_id=tenant_id,
        customer_id=customer_id,
        status="complet",
        source="cosium",
    )
    db.add(case)
    db.flush()
    logger.info(
        "case_created_for_import",
        tenant_id=tenant_id,
        customer_id=customer_id,
        case_id=case.id,
    )
    return case


def _devis_exists_for_quote(
    db: Session,
    tenant_id: int,
    invoice_number: str,
) -> bool:
    """Check if a devis with this numero already exists."""
    return db.scalar(
        select(Devis.id)
        .where(
            Devis.tenant_id == tenant_id,
            Devis.numero == invoice_number,
        )
        .limit(1)
    ) is not None


def _create_devis_from_quote(
    db: Session,
    tenant_id: int,
    quote: CosiumInvoice,
    case_id: int,
) -> Devis:
    """Create a Devis and a single DevisLigne from a Cosium QUOTE."""
    montant_ttc = round(float(quote.total_ti or 0), 2)
    part_secu = round(float(quote.share_social_security or 0), 2)
    part_mutuelle = round(float(quote.share_private_insurance or 0), 2)
    reste_a_charge = round(max(montant_ttc - part_secu - part_mutuelle, 0), 2)
    montant_ht = round(montant_ttc / (1 + TVA_TAUX / 100), 2)
    tva = round(montant_ttc - montant_ht, 2)

    devis = Devis(
        tenant_id=tenant_id,
        case_id=case_id,
        numero=quote.invoice_number,
        status="signe",
        montant_ht=montant_ht,
        tva=tva,
        montant_ttc=montant_ttc,
        part_secu=part_secu,
        part_mutuelle=part_mutuelle,
        reste_a_charge=reste_a_charge,
    )
    db.add(devis)
    db.flush()

    ligne = DevisLigne(
        tenant_id=tenant_id,
        devis_id=devis.id,
        designation="Equipement optique (importe Cosium)",
        quantite=1,
        prix_unitaire_ht=montant_ht,
        taux_tva=TVA_TAUX,
        montant_ht=montant_ht,
        montant_ttc=montant_ttc,
    )
    db.add(ligne)

    return devis


def import_cosium_quotes_as_devis(
    db: Session,
    tenant_id: int,
    user_id: int,
    customer_id: int | None = None,
    batch_size: int = 500,
) -> dict:
    """Convert Cosium QUOTE invoices into OptiFlow Devis records.

    Args:
        db: Database session.
        tenant_id: Tenant ID for data isolation.
        user_id: User performing the import (for audit).
        customer_id: If set, only import quotes for this customer.
        batch_size: Commit every N records to avoid memory issues.

    Returns:
        dict with keys: imported, skipped, no_customer, errors, cases_created.
    """
    stmt = (
        select(CosiumInvoice)
        .where(
            CosiumInvoice.tenant_id == tenant_id,
            CosiumInvoice.type == "QUOTE",
        )
        .order_by(CosiumInvoice.invoice_date.desc())
    )
    if customer_id is not None:
        stmt = stmt.where(CosiumInvoice.customer_id == customer_id)

    quotes = db.scalars(stmt).all()

    stats = {
        "imported": 0,
        "skipped": 0,
        "no_customer": 0,
        "errors": 0,
        "cases_created": 0,
        "total_quotes": len(quotes),
    }

    cases_created_before = set()

    for i, quote in enumerate(quotes):
        try:
            # Skip quotes without linked customer
            if quote.customer_id is None:
                stats["no_customer"] += 1
                continue

            # Skip if devis already exists for this quote number
            if _devis_exists_for_quote(db, tenant_id, quote.invoice_number):
                stats["skipped"] += 1
                continue

            # Find or create case
            case = _find_or_create_case(db, tenant_id, quote.customer_id)
            if case.id not in cases_created_before and case.source == "cosium":
                # Check if this case was just created (new)
                if case.created_at and (datetime.now(UTC) - case.created_at).total_seconds() < 5:
                    stats["cases_created"] += 1
                    cases_created_before.add(case.id)

            # Create the devis
            _create_devis_from_quote(db, tenant_id, quote, case.id)
            stats["imported"] += 1

            # Batch commit to avoid memory issues
            if (i + 1) % batch_size == 0:
                db.commit()
                logger.info(
                    "devis_import_batch_committed",
                    tenant_id=tenant_id,
                    processed=i + 1,
                    imported=stats["imported"],
                )

        except (SQLAlchemyError, ValueError, TypeError) as exc:
            logger.error(
                "devis_import_error",
                tenant_id=tenant_id,
                invoice_number=quote.invoice_number,
                error=str(exc),
            )
            stats["errors"] += 1
            db.rollback()

    # Final commit
    try:
        db.commit()
    except SQLAlchemyError as exc:
        logger.error("devis_import_final_commit_error", error=str(exc))
        db.rollback()
        stats["errors"] += 1

    logger.info(
        "devis_import_completed",
        tenant_id=tenant_id,
        user_id=user_id,
        stats=stats,
    )

    return stats
