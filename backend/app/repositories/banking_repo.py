from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models import BankTransaction, Payment

# --- Payments ---


def create_payment(
    db: Session,
    tenant_id: int,
    case_id: int,
    facture_id: int | None,
    payer_type: str,
    mode_paiement: str | None,
    reference_externe: str | None,
    date_paiement: datetime | None,
    amount_due: float,
    amount_paid: float,
    idempotency_key: str | None,
) -> Payment:
    status = "paid" if amount_paid >= amount_due and amount_due > 0 else ("partial" if amount_paid > 0 else "pending")
    p = Payment(
        tenant_id=tenant_id,
        case_id=case_id,
        facture_id=facture_id,
        payer_type=payer_type,
        mode_paiement=mode_paiement,
        reference_externe=reference_externe,
        date_paiement=date_paiement or datetime.now(UTC).replace(tzinfo=None),
        amount_due=amount_due,
        amount_paid=amount_paid,
        status=status,
        idempotency_key=idempotency_key,
    )
    db.add(p)
    db.flush()
    db.refresh(p)
    return p


def get_by_idempotency_key(db: Session, key: str, tenant_id: int) -> Payment | None:
    return db.scalars(select(Payment).where(Payment.idempotency_key == key, Payment.tenant_id == tenant_id)).first()


def list_unreconciled_payments(db: Session, tenant_id: int, limit: int = 500) -> list[Payment]:
    return list(
        db.scalars(
            select(Payment)
            .where(Payment.amount_paid > 0, Payment.tenant_id == tenant_id)
            .order_by(Payment.created_at.desc())
            .limit(limit)
        ).all()
    )


# --- Bank Transactions ---


def get_transaction_signatures(db: Session, tenant_id: int) -> set[tuple[str, float, str]]:
    """Return a set of (date_iso, amount_rounded, libelle_prefix) for dedup."""
    rows = db.execute(
        select(BankTransaction.date, BankTransaction.montant, BankTransaction.libelle)
        .where(BankTransaction.tenant_id == tenant_id)
    ).all()
    return {
        (r.date.date().isoformat() if r.date else "", round(float(r.montant), 2), (r.libelle or "")[:100])
        for r in rows
    }


def create_transaction(
    db: Session,
    tenant_id: int,
    date: datetime,
    libelle: str,
    montant: float,
    reference: str | None,
    source_file: str | None,
) -> BankTransaction:
    t = BankTransaction(
        tenant_id=tenant_id,
        date=date,
        libelle=libelle,
        montant=montant,
        reference=reference,
        source_file=source_file,
    )
    db.add(t)
    return t


def list_transactions(
    db: Session,
    tenant_id: int,
    reconciled: bool | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[BankTransaction], int]:
    q = select(BankTransaction).where(BankTransaction.tenant_id == tenant_id)
    if reconciled is not None:
        q = q.where(BankTransaction.reconciled == reconciled)
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.scalars(q.order_by(BankTransaction.date.desc()).limit(limit).offset(offset)).all()
    return list(rows), total


def get_unmatched(db: Session, tenant_id: int, limit: int = 1000) -> list[BankTransaction]:
    return list(
        db.scalars(
            select(BankTransaction)
            .where(BankTransaction.reconciled.is_(False), BankTransaction.tenant_id == tenant_id)
            .order_by(BankTransaction.date.desc())
            .limit(limit)
        ).all()
    )


def get_transaction(db: Session, tx_id: int, tenant_id: int) -> BankTransaction | None:
    return db.scalars(
        select(BankTransaction).where(BankTransaction.id == tx_id, BankTransaction.tenant_id == tenant_id)
    ).first()


def reconcile(db: Session, tx: BankTransaction, payment_id: int) -> None:
    tx.reconciled = True
    tx.reconciled_payment_id = payment_id
    db.flush()


def auto_reconcile(db: Session, tenant_id: int) -> tuple[int, int]:
    unmatched = get_unmatched(db, tenant_id)
    matched_count = 0

    # Pre-compute the set of already-reconciled payment IDs once (avoid N+1)
    already_matched: set[int] = {
        r[0]
        for r in db.execute(
            select(BankTransaction.reconciled_payment_id).where(
                BankTransaction.reconciled.is_(True),
                BankTransaction.tenant_id == tenant_id,
            )
        ).all()
        if r[0]
    }

    for tx in unmatched:
        # Match by exact amount + date within 3 days + reference substring
        candidates = db.scalars(
            select(Payment).where(
                and_(
                    Payment.tenant_id == tenant_id,
                    Payment.amount_paid == abs(tx.montant),
                    Payment.date_paiement.isnot(None),
                    Payment.date_paiement >= tx.date - timedelta(days=3),
                    Payment.date_paiement <= tx.date + timedelta(days=3),
                )
            )
        ).all()

        matched_payment_id: int | None = None

        # Try reference matching first
        if tx.reference:
            for p in candidates:
                if p.reference_externe and tx.reference in p.reference_externe:
                    matched_payment_id = p.id
                    break

        # If no reference match, take first unmatched amount+date candidate
        if matched_payment_id is None and candidates:
            for p in candidates:
                if p.id not in already_matched:
                    matched_payment_id = p.id
                    break

        if matched_payment_id is not None:
            reconcile(db, tx, matched_payment_id)
            already_matched.add(matched_payment_id)
            matched_count += 1

    return matched_count, len(unmatched) - matched_count
