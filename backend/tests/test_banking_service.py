"""Unit tests for banking_service — direct service function calls."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError
from app.domain.schemas.banking import PaymentCreate
from app.models import BankTransaction, Case, Customer, Payment, Tenant
from app.services import banking_service


def _tenant_id(db: Session) -> int:
    return db.query(Tenant).filter(Tenant.slug == "test-magasin").first().id


def _seed_case(db: Session, tenant_id: int) -> int:
    c = Customer(tenant_id=tenant_id, first_name="Test", last_name="Banking")
    db.add(c)
    db.flush()
    case = Case(tenant_id=tenant_id, customer_id=c.id, status="draft")
    db.add(case)
    db.flush()
    return case.id


class TestCreatePayment:
    def test_creates_with_valid_data(self, db, seed_user):
        tid = _tenant_id(db)
        case_id = _seed_case(db, tid)

        payload = PaymentCreate(
            case_id=case_id,
            payer_type="client",
            mode_paiement="cb",
            amount_due=200.0,
            amount_paid=200.0,
        )
        result = banking_service.create_payment(db, tid, payload, seed_user.id)

        assert result.id is not None
        assert result.amount_paid == 200.0
        assert result.payer_type == "client"
        assert result.status == "paid"

    def test_idempotency_key_prevents_duplicate(self, db, seed_user):
        tid = _tenant_id(db)
        case_id = _seed_case(db, tid)

        payload = PaymentCreate(
            case_id=case_id,
            payer_type="client",
            amount_due=100.0,
            amount_paid=100.0,
        )
        first = banking_service.create_payment(db, tid, payload, seed_user.id, idempotency_key="key-123")
        second = banking_service.create_payment(db, tid, payload, seed_user.id, idempotency_key="key-123")

        # Same record returned, not a new one
        assert first.id == second.id
        # Only one payment in DB with this key
        count = db.query(Payment).filter(Payment.idempotency_key == "key-123").count()
        assert count == 1


class TestImportStatement:
    def test_csv_import_creates_transactions(self, db, seed_user):
        tid = _tenant_id(db)

        csv_content = (
            "date;libelle;montant;reference\n"
            "15/03/2026;Paiement client Martin;150,00;REF001\n"
            "16/03/2026;Virement mutuelle;300,50;REF002\n"
        )
        mock_file = MagicMock()
        mock_file.file.read.return_value = csv_content.encode("utf-8")
        mock_file.filename = "releve_mars.csv"

        imported, skipped = banking_service.import_statement(db, tid, mock_file, seed_user.id)
        assert imported == 2

        txs = db.query(BankTransaction).filter(BankTransaction.tenant_id == tid).all()
        assert len(txs) == 2
        assert any(t.reference == "REF001" for t in txs)


class TestAutoReconcile:
    def test_matches_by_amount_and_date(self, db, seed_user):
        tid = _tenant_id(db)
        case_id = _seed_case(db, tid)

        now = datetime.now(UTC).replace(tzinfo=None)

        # Create a payment
        payment = Payment(
            tenant_id=tid, case_id=case_id, payer_type="client",
            amount_due=150.0, amount_paid=150.0, status="paid",
            date_paiement=now - timedelta(days=1),
        )
        db.add(payment)
        db.flush()

        # Create a matching bank transaction (same amount, close date)
        tx = BankTransaction(
            tenant_id=tid, date=now, libelle="Paiement client",
            montant=150.0, reference=None,
        )
        db.add(tx)
        db.commit()

        result = banking_service.auto_reconcile(db, tid, seed_user.id)
        assert result.matched == 1
        assert result.unmatched == 0

        db.refresh(tx)
        assert tx.reconciled is True
        assert tx.reconciled_payment_id == payment.id


class TestManualMatch:
    def test_links_transaction_to_payment(self, db, seed_user):
        tid = _tenant_id(db)
        case_id = _seed_case(db, tid)

        now = datetime.now(UTC).replace(tzinfo=None)

        payment = Payment(
            tenant_id=tid, case_id=case_id, payer_type="client",
            amount_due=75.0, amount_paid=75.0, status="paid",
            date_paiement=now,
        )
        db.add(payment)
        db.flush()

        tx = BankTransaction(
            tenant_id=tid, date=now, libelle="Virement inconnu", montant=75.0,
        )
        db.add(tx)
        db.commit()

        result = banking_service.manual_match(db, tid, tx.id, payment.id, seed_user.id)
        assert result.reconciled is True
        assert result.reconciled_payment_id == payment.id

    def test_manual_match_already_reconciled_raises(self, db, seed_user):
        tid = _tenant_id(db)
        case_id = _seed_case(db, tid)

        now = datetime.now(UTC).replace(tzinfo=None)

        payment = Payment(
            tenant_id=tid, case_id=case_id, payer_type="client",
            amount_due=50.0, amount_paid=50.0, status="paid",
        )
        db.add(payment)
        db.flush()

        tx = BankTransaction(
            tenant_id=tid, date=now, libelle="Already matched",
            montant=50.0, reconciled=True, reconciled_payment_id=payment.id,
        )
        db.add(tx)
        db.commit()

        with pytest.raises(BusinessError):
            banking_service.manual_match(db, tid, tx.id, payment.id, seed_user.id)
