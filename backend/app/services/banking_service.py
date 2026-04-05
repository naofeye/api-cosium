import csv
import io
from datetime import datetime

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError, NotFoundError
from app.core.logging import get_logger
from app.domain.schemas.banking import (
    BankTransactionListResponse,
    BankTransactionResponse,
    PaymentCreate,
    PaymentResponse,
    ReconcileResult,
)
from app.repositories import banking_repo
from app.services import audit_service, event_service

logger = get_logger("banking_service")


def create_payment(
    db: Session,
    tenant_id: int,
    payload: PaymentCreate,
    user_id: int,
    idempotency_key: str | None = None,
) -> PaymentResponse:
    if idempotency_key:
        existing = banking_repo.get_by_idempotency_key(db, key=idempotency_key, tenant_id=tenant_id)
        if existing:
            return PaymentResponse.model_validate(existing)

    payment = banking_repo.create_payment(
        db,
        tenant_id=tenant_id,
        case_id=payload.case_id,
        facture_id=payload.facture_id,
        payer_type=payload.payer_type,
        mode_paiement=payload.mode_paiement,
        reference_externe=payload.reference_externe,
        date_paiement=payload.date_paiement,
        amount_due=payload.amount_due,
        amount_paid=payload.amount_paid,
        idempotency_key=idempotency_key,
    )

    if user_id:
        audit_service.log_action(
            db,
            tenant_id,
            user_id,
            "create",
            "payment",
            payment.id,
            new_value={"amount": payload.amount_paid, "payer": payload.payer_type},
        )
        event_service.emit_event(db, tenant_id, "PaiementRecu", "payment", payment.id, user_id)

    logger.info("payment_created", tenant_id=tenant_id, payment_id=payment.id, amount=payload.amount_paid)
    return PaymentResponse.model_validate(payment)


def import_statement(db: Session, tenant_id: int, file: UploadFile, user_id: int) -> int:
    raw = file.file.read()
    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            content = raw.decode("latin-1")
        except UnicodeDecodeError:
            raise BusinessError("FILE_DECODE_ERROR", "Impossible de lire le fichier. Format d'encodage non supporte.") from None
    reader = csv.DictReader(io.StringIO(content), delimiter=";")

    count = 0
    source_file = file.filename or "import.csv"

    for row in reader:
        try:
            date_str = row.get("date", row.get("Date", "")).strip()
            libelle = row.get("libelle", row.get("Libelle", row.get("label", ""))).strip()
            montant_str = row.get("montant", row.get("Montant", row.get("amount", "0"))).strip()
            reference = row.get("reference", row.get("Reference", row.get("ref", ""))).strip() or None

            montant_str = montant_str.replace(",", ".").replace(" ", "")
            montant = float(montant_str)

            for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
                try:
                    date = datetime.strptime(date_str, fmt)
                    break
                except ValueError:
                    continue
            else:
                continue

            banking_repo.create_transaction(db, tenant_id, date, libelle, montant, reference, source_file)
            count += 1
        except (ValueError, KeyError):
            continue

    db.commit()

    if user_id:
        audit_service.log_action(
            db,
            tenant_id,
            user_id,
            "create",
            "bank_import",
            0,
            new_value={"file": source_file, "count": count},
        )

    logger.info("bank_statement_imported", tenant_id=tenant_id, file=source_file, count=count)
    return count


def auto_reconcile(db: Session, tenant_id: int, user_id: int) -> ReconcileResult:
    matched, unmatched = banking_repo.auto_reconcile(db, tenant_id)

    if user_id and matched > 0:
        event_service.emit_event(db, tenant_id, "PaiementRapproche", "bank_reconcile", 0, user_id)

    logger.info("auto_reconcile_done", tenant_id=tenant_id, matched=matched, unmatched=unmatched)
    return ReconcileResult(matched=matched, unmatched=unmatched)


def manual_match(
    db: Session, tenant_id: int, transaction_id: int, payment_id: int, user_id: int
) -> BankTransactionResponse:
    tx = banking_repo.get_transaction(db, tx_id=transaction_id, tenant_id=tenant_id)
    if not tx:
        raise NotFoundError("bank_transaction", transaction_id)
    if tx.reconciled:
        raise BusinessError("ALREADY_RECONCILED", "Cette transaction est deja rapprochee")

    banking_repo.reconcile(db, tx=tx, payment_id=payment_id)

    if user_id:
        audit_service.log_action(
            db,
            tenant_id,
            user_id,
            "update",
            "bank_transaction",
            transaction_id,
            new_value={"payment_id": payment_id},
        )

    logger.info("manual_match_done", tenant_id=tenant_id, tx_id=transaction_id, payment_id=payment_id)
    return BankTransactionResponse.model_validate(tx)


def get_unmatched(db: Session, tenant_id: int) -> list[BankTransactionResponse]:
    txs = banking_repo.get_unmatched(db, tenant_id)
    return [BankTransactionResponse.model_validate(t) for t in txs]


def get_unreconciled_payments(db: Session, tenant_id: int) -> list[PaymentResponse]:
    payments = banking_repo.list_unreconciled_payments(db, tenant_id)
    return [PaymentResponse.model_validate(p) for p in payments]


def list_transactions(
    db: Session,
    tenant_id: int,
    reconciled: bool | None = None,
    limit: int = 100,
    offset: int = 0,
) -> BankTransactionListResponse:
    items, total = banking_repo.list_transactions(db, tenant_id, reconciled, limit, offset)
    return BankTransactionListResponse(
        items=[BankTransactionResponse.model_validate(t) for t in items],
        total=total,
    )
