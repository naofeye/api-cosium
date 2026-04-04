"""Tests for encryption module."""

import pytest

from app.core.encryption import encrypt, decrypt


def test_encrypt_returns_different_value():
    result = encrypt("hello")
    assert result != "hello"
    assert len(result) > 0


def test_decrypt_reverses_encrypt():
    original = "my_secret_password_123"
    encrypted = encrypt(original)
    decrypted = decrypt(encrypted)
    assert decrypted == original


def test_encrypt_different_inputs_give_different_outputs():
    a = encrypt("password1")
    b = encrypt("password2")
    assert a != b


def test_decrypt_invalid_raises():
    with pytest.raises(Exception):
        decrypt("not-a-valid-encrypted-string")


def test_encrypt_empty_string():
    encrypted = encrypt("")
    decrypted = decrypt(encrypted)
    assert decrypted == ""


def test_encrypt_unicode():
    original = "mot de passe avec accents: eaeieoe"
    encrypted = encrypt(original)
    decrypted = decrypt(encrypted)
    assert decrypted == original


def test_encrypt_produces_different_ciphertexts():
    """Fernet uses random IV, so same plaintext gives different ciphertexts."""
    a = encrypt("same_value")
    b = encrypt("same_value")
    # Both decrypt to same value
    assert decrypt(a) == decrypt(b) == "same_value"
    # But ciphertexts are different (due to random IV)
    assert a != b
