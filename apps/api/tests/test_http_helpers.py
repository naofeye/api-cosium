"""Tests pour les helpers HTTP (content_disposition RFC 5987)."""

from app.core.http import content_disposition


def test_ascii_filename_simple():
    header = content_disposition("facture_42.pdf")
    assert header == 'attachment; filename="facture_42.pdf"'


def test_inline_disposition():
    header = content_disposition("report.html", inline=True)
    assert header.startswith("inline;")


def test_unicode_filename_has_fallback_and_utf8():
    header = content_disposition("contrat été 2026.pdf")
    assert "filename=" in header
    assert "filename*=UTF-8''" in header
    assert "%C3%A9" in header  # é encode


def test_crlf_injection_sanitized():
    header = content_disposition("evil\r\nX-Injected: yes")
    assert "\r" not in header
    assert "\n" not in header
    assert "X-Injected" in header  # le texte reste, mais sans CR/LF actifs


def test_quote_in_filename_escaped():
    header = content_disposition('a"b.pdf')
    assert '"' not in header.split(";", 1)[1].split(";")[0].split("=", 1)[1].strip('"')


def test_backslash_sanitized():
    header = content_disposition("path\\to\\file.pdf")
    assert "\\" not in header
