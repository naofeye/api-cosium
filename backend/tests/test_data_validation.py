"""Tests for ERP data validation and phone normalization."""

from datetime import date, timedelta

from app.integrations.erp_models import ERPCustomer
from app.services.erp_sync_service import _normalize_phone, _validate_erp_customer_data


# ---------- Test 1: valid data returns no warnings ----------

def test_validate_erp_customer_valid_data() -> None:
    """Valid ERP customer data should produce no warnings."""
    customer = ERPCustomer(
        erp_id="100",
        first_name="Jean",
        last_name="Dupont",
        email="jean.dupont@example.com",
        birth_date=date(1985, 6, 15),
        social_security_number="1850675001234",
    )
    warnings = _validate_erp_customer_data(customer)
    assert warnings == []


# ---------- Test 2: invalid email ----------

def test_validate_erp_customer_invalid_email() -> None:
    """Email without @ should generate a warning."""
    customer = ERPCustomer(
        erp_id="101",
        first_name="Marie",
        last_name="Martin",
        email="invalid-email-no-at",
    )
    warnings = _validate_erp_customer_data(customer)
    assert len(warnings) == 1
    assert "invalide" in warnings[0].lower() or "email" in warnings[0].lower()


# ---------- Test 3: future birth date ----------

def test_validate_erp_customer_future_birth_date() -> None:
    """Birth date in the future should generate a warning."""
    future_date = date.today() + timedelta(days=30)
    customer = ERPCustomer(
        erp_id="102",
        first_name="Futur",
        last_name="Bebe",
        birth_date=future_date,
    )
    warnings = _validate_erp_customer_data(customer)
    assert len(warnings) >= 1
    assert any("futur" in w.lower() for w in warnings)


# ---------- Test 4: invalid SSN (too short) ----------

def test_validate_erp_customer_invalid_ssn() -> None:
    """SSN with wrong number of digits should generate a warning."""
    customer = ERPCustomer(
        erp_id="103",
        first_name="Pierre",
        last_name="Duval",
        social_security_number="12345",  # Too short (5 digits)
    )
    warnings = _validate_erp_customer_data(customer)
    assert len(warnings) >= 1
    assert any("securite sociale" in w.lower() or "longueur" in w.lower() for w in warnings)


# ---------- Test 5: normalize_phone strips formatting ----------

def test_normalize_phone_strips_formatting() -> None:
    """Phone normalization should remove spaces, dots, and dashes."""
    assert _normalize_phone("06 12 34 56 78") == "0612345678"
    assert _normalize_phone("06.12.34.56.78") == "0612345678"
    assert _normalize_phone("06-12-34-56-78") == "0612345678"
    assert _normalize_phone(None) is None
    assert _normalize_phone("") == ""


# ---------- Test 6: normalize_phone handles international format ----------

def test_normalize_phone_international_format() -> None:
    """International phone numbers starting with + should be preserved."""
    assert _normalize_phone("+33 6 12 34 56 78") == "+33612345678"
    # A number not starting with + or 0 should get a 0 prefix
    assert _normalize_phone("612345678") == "0612345678"
    # Already starting with 0
    assert _normalize_phone("0612345678") == "0612345678"
