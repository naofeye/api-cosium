"""Tests for EncryptedString TypeDecorator (PII / transparent column encryption).

Does NOT duplicate tests already in test_encryption.py (encrypt/decrypt roundtrip,
empty string, unicode, random IV). Focus: TypeDecorator behaviour + SQLAlchemy
integration via the Customer model.
"""

from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.encryption import EncryptedString, decrypt, encrypt
from app.db.base import Base
from app.models.client import Customer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(name="isolated_db")
def isolated_db_fixture():
    """SQLite in-memory engine with full schema — isolated from the main db fixture."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    try:
        yield session, engine
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(name="dialect")
def dialect_fixture():
    """A minimal SQLAlchemy dialect stub — sufficient for process_*_param calls."""
    return MagicMock()


# ---------------------------------------------------------------------------
# 1. encrypt() / decrypt() roundtrip
# ---------------------------------------------------------------------------


def test_encrypt_decrypt_roundtrip_basic():
    plaintext = "numero-secu: 2 85 06 75 123 456 78"
    assert decrypt(encrypt(plaintext)) == plaintext


def test_encrypt_decrypt_roundtrip_address():
    address = "12 rue de la Paix, 75001 Paris"
    assert decrypt(encrypt(address)) == address


def test_encrypt_produces_string_not_bytes():
    result = encrypt("test")
    assert isinstance(result, str)


def test_decrypt_produces_string_not_bytes():
    result = decrypt(encrypt("test"))
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# 2. EncryptedString.process_bind_param — encrypts non-null, passes null through
# ---------------------------------------------------------------------------


def test_process_bind_param_null_passthrough(dialect):
    col = EncryptedString()
    assert col.process_bind_param(None, dialect) is None


def test_process_bind_param_encrypts_value(dialect):
    col = EncryptedString()
    plaintext = "75 avenue Victor Hugo"
    result = col.process_bind_param(plaintext, dialect)
    # Must not be the original plaintext
    assert result != plaintext
    # Must be decryptable back to the original
    assert decrypt(result) == plaintext


def test_process_bind_param_returns_string(dialect):
    col = EncryptedString()
    result = col.process_bind_param("some value", dialect)
    assert isinstance(result, str)


def test_process_bind_param_different_calls_give_different_ciphertext(dialect):
    """Fernet random IV: same plaintext → different ciphertext each time."""
    col = EncryptedString()
    a = col.process_bind_param("same", dialect)
    b = col.process_bind_param("same", dialect)
    assert a != b
    # Both must still decrypt to the same value
    assert decrypt(a) == decrypt(b) == "same"


# ---------------------------------------------------------------------------
# 3. EncryptedString.process_result_value — decrypts, passes null through
# ---------------------------------------------------------------------------


def test_process_result_value_null_passthrough(dialect):
    col = EncryptedString()
    assert col.process_result_value(None, dialect) is None


def test_process_result_value_decrypts_correctly(dialect):
    col = EncryptedString()
    plaintext = "1 85 06 75 123 456 78"
    ciphertext = encrypt(plaintext)
    assert col.process_result_value(ciphertext, dialect) == plaintext


def test_process_result_value_returns_string(dialect):
    col = EncryptedString()
    ciphertext = encrypt("hello")
    result = col.process_result_value(ciphertext, dialect)
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# 4. process_result_value — graceful fallback for unencrypted legacy data
# ---------------------------------------------------------------------------


def test_process_result_value_fallback_for_plaintext(dialect):
    """If the stored value is not valid Fernet ciphertext (legacy / migration),
    the original value must be returned unchanged instead of raising."""
    col = EncryptedString()
    legacy_value = "plain-old-unencrypted-address"
    result = col.process_result_value(legacy_value, dialect)
    assert result == legacy_value


def test_process_result_value_fallback_for_arbitrary_garbage(dialect):
    col = EncryptedString()
    garbage = "!@#$%^&*()_not_fernet_at_all"
    result = col.process_result_value(garbage, dialect)
    assert result == garbage


def test_process_result_value_fallback_does_not_raise(dialect):
    col = EncryptedString()
    # Must never raise regardless of what garbage is stored
    try:
        col.process_result_value("AAAAAAA", dialect)
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"process_result_value raised unexpectedly: {exc}")


def test_process_result_value_logs_warning_on_decrypt_failure(dialect, caplog):
    """When decryption fails (legacy plaintext), a warning must be logged with context."""
    import logging

    col = EncryptedString()
    legacy_value = "plain-old-unencrypted-address"
    with caplog.at_level(logging.WARNING, logger="encryption"):
        result = col.process_result_value(legacy_value, dialect)
    assert result == legacy_value
    assert any(
        "encrypted_string_decrypt_failed_fallback_plaintext" in rec.message
        for rec in caplog.records
    )


# ---------------------------------------------------------------------------
# 5. Integration: Customer model with EncryptedString columns
# ---------------------------------------------------------------------------


def _seed_tenant(session):
    """Insert the minimum required parent rows (organization + tenant)."""
    from app.models import Organization, Tenant

    org = Organization(name="Test Org Enc", slug="test-org-enc", plan="solo")
    session.add(org)
    session.flush()
    tenant = Tenant(
        organization_id=org.id,
        name="Magasin Enc",
        slug="magasin-enc",
        cosium_tenant="enc-tenant",
        cosium_login="enc-login",
        cosium_password_enc="enc-password",
    )
    session.add(tenant)
    session.flush()
    return tenant


def test_customer_encrypted_fields_stored_as_ciphertext(isolated_db):
    """Values written to EncryptedString columns must be stored encrypted in DB."""
    session, engine = isolated_db
    tenant = _seed_tenant(session)

    customer = Customer(
        tenant_id=tenant.id,
        first_name="Marie",
        last_name="Curie",
        social_security_number="2 85 06 75 123 456 78",
        address="12 rue du Dr Roux, 75015 Paris",
        street_name="rue du Dr Roux",
    )
    session.add(customer)
    session.commit()

    # Read raw ciphertext directly from DB (bypassing the TypeDecorator)
    raw = session.execute(
        text("SELECT social_security_number, address, street_name FROM customers WHERE id = :id"),
        {"id": customer.id},
    ).fetchone()

    assert raw is not None
    # The DB value must NOT equal the plaintext
    assert raw[0] != "2 85 06 75 123 456 78", "SSN should be stored encrypted"
    assert raw[1] != "12 rue du Dr Roux, 75015 Paris", "Address should be stored encrypted"
    assert raw[2] != "rue du Dr Roux", "Street name should be stored encrypted"

    # But they must be valid Fernet ciphertext (decryptable)
    assert decrypt(raw[0]) == "2 85 06 75 123 456 78"
    assert decrypt(raw[1]) == "12 rue du Dr Roux, 75015 Paris"
    assert decrypt(raw[2]) == "rue du Dr Roux"


def test_customer_encrypted_fields_read_back_as_plaintext(isolated_db):
    """ORM reads must transparently decrypt the stored ciphertext."""
    session, engine = isolated_db
    tenant = _seed_tenant(session)

    customer = Customer(
        tenant_id=tenant.id,
        first_name="Pierre",
        last_name="Curie",
        social_security_number="1 59 04 75 000 111 22",
        address="1 place Jussieu, 75005 Paris",
    )
    session.add(customer)
    session.commit()

    # Expire cache to force a fresh load from DB
    session.expire(customer)
    reloaded = session.get(Customer, customer.id)

    assert reloaded.social_security_number == "1 59 04 75 000 111 22"
    assert reloaded.address == "1 place Jussieu, 75005 Paris"


def test_customer_null_encrypted_fields_stay_null(isolated_db):
    """NULL PII columns must stay NULL — no encryption attempted."""
    session, engine = isolated_db
    tenant = _seed_tenant(session)

    customer = Customer(
        tenant_id=tenant.id,
        first_name="Anonymous",
        last_name="User",
        social_security_number=None,
        address=None,
    )
    session.add(customer)
    session.commit()
    session.expire(customer)

    reloaded = session.get(Customer, customer.id)
    assert reloaded.social_security_number is None
    assert reloaded.address is None


def test_customer_update_encrypted_field(isolated_db):
    """Updating an EncryptedString column must re-encrypt the new value."""
    session, engine = isolated_db
    tenant = _seed_tenant(session)

    customer = Customer(
        tenant_id=tenant.id,
        first_name="Jean",
        last_name="Valjean",
        address="Rue Plumet, Paris",
    )
    session.add(customer)
    session.commit()

    # Update the address
    customer.address = "Boulevard du Temple, Paris"
    session.commit()
    session.expire(customer)

    reloaded = session.get(Customer, customer.id)
    assert reloaded.address == "Boulevard du Temple, Paris"

    # Confirm new ciphertext is in DB
    raw = session.execute(
        text("SELECT address FROM customers WHERE id = :id"),
        {"id": customer.id},
    ).fetchone()
    assert raw[0] != "Boulevard du Temple, Paris"
    assert decrypt(raw[0]) == "Boulevard du Temple, Paris"
