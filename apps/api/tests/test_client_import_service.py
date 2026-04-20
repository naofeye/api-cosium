"""Tests for client_import_service — CSV/Excel import, validation, duplicate detection."""
import io
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.models.client import Customer
from app.services.client_import_service import (
    _detect_delimiter,
    _normalize_column,
    _parse_date,
    generate_import_template,
    import_from_file,
)


# ---------------------------------------------------------------------------
# Helper to build a minimal CSV file in bytes
# ---------------------------------------------------------------------------

def _make_csv(rows: list[list[str]], delimiter: str = ";") -> bytes:
    lines = []
    for row in rows:
        lines.append(delimiter.join(row))
    return "\n".join(lines).encode("utf-8-sig")


# ---------------------------------------------------------------------------
# Unit tests for internal helpers
# ---------------------------------------------------------------------------

class TestDetectDelimiter:
    def test_semicolon(self):
        assert _detect_delimiter("Nom;Prenom;Email") == ";"

    def test_comma(self):
        assert _detect_delimiter("Nom,Prenom,Email") == ","

    def test_tab(self):
        assert _detect_delimiter("Nom\tPrenom\tEmail") == "\t"


class TestNormalizeColumn:
    def test_strips_spaces(self):
        assert _normalize_column("  Nom  ") == "nom"

    def test_lowercases(self):
        assert _normalize_column("Prénom") == "prénom"

    def test_replaces_underscore_with_space(self):
        assert _normalize_column("last_name") == "last name"

    def test_replaces_hyphen_with_space(self):
        assert _normalize_column("e-mail") == "e mail"


class TestParseDate:
    def test_dd_mm_yyyy(self):
        assert _parse_date("15/03/1985") == "1985-03-15"

    def test_dd_mm_yy(self):
        assert _parse_date("15/03/85") == "1985-03-15"

    def test_iso_format(self):
        assert _parse_date("1985-03-15") == "1985-03-15"

    def test_dot_separated(self):
        assert _parse_date("15.03.1985") == "1985-03-15"

    def test_empty_returns_none(self):
        assert _parse_date("") is None

    def test_invalid_returns_none(self):
        assert _parse_date("not-a-date") is None

    def test_strips_whitespace(self):
        assert _parse_date("  15/03/1985  ") == "1985-03-15"


# ---------------------------------------------------------------------------
# Tests for import_from_file — CSV
# ---------------------------------------------------------------------------

class TestImportFromFileCsv:
    def test_valid_single_row_creates_customer(self, db: Session, default_tenant):
        csv_content = _make_csv([
            ["Nom", "Prenom", "Email", "Telephone"],
            ["Dupont", "Jean", "jean.dupont@test.fr", "0612345678"],
        ])
        with patch("app.services.client_import_service.audit_service") as mock_audit:
            mock_audit.log_action = MagicMock()
            result = import_from_file(
                db, default_tenant.id, csv_content, "import.csv", user_id=1
            )

        assert result.imported == 1
        assert result.updated == 0
        assert result.skipped == 0
        assert result.errors == []

        customer = db.query(Customer).filter(
            Customer.tenant_id == default_tenant.id,
            Customer.email == "jean.dupont@test.fr",
        ).first()
        assert customer is not None
        assert customer.last_name == "Dupont"
        assert customer.first_name == "Jean"

    def test_valid_multiple_rows(self, db: Session, default_tenant):
        csv_content = _make_csv([
            ["Nom", "Prenom", "Email"],
            ["Martin", "Alice", "alice@test.fr"],
            ["Bernard", "Bob", "bob@test.fr"],
            ["Durand", "Charlie", "charlie@test.fr"],
        ])
        with patch("app.services.client_import_service.audit_service") as mock_audit:
            mock_audit.log_action = MagicMock()
            result = import_from_file(
                db, default_tenant.id, csv_content, "import.csv", user_id=1
            )

        assert result.imported == 3
        assert result.skipped == 0

    def test_row_missing_last_name_is_skipped(self, db: Session, default_tenant):
        csv_content = _make_csv([
            ["Nom", "Prenom", "Email"],
            ["", "Jean", "jean@test.fr"],
        ])
        with patch("app.services.client_import_service.audit_service") as mock_audit:
            mock_audit.log_action = MagicMock()
            result = import_from_file(
                db, default_tenant.id, csv_content, "import.csv", user_id=1
            )

        assert result.imported == 0
        assert result.skipped == 1
        assert len(result.errors) == 1
        assert "Nom de famille manquant" in result.errors[0].reason

    def test_invalid_email_is_cleared_but_row_imported(self, db: Session, default_tenant):
        csv_content = _make_csv([
            ["Nom", "Prenom", "Email"],
            ["Dupont", "Jean", "not-an-email"],
        ])
        with patch("app.services.client_import_service.audit_service") as mock_audit:
            mock_audit.log_action = MagicMock()
            result = import_from_file(
                db, default_tenant.id, csv_content, "import.csv", user_id=1
            )

        # Row is imported (without email), but error is recorded
        assert result.imported == 1
        assert len(result.errors) == 1
        assert "invalide" in result.errors[0].reason.lower()

        customer = db.query(Customer).filter(
            Customer.tenant_id == default_tenant.id,
            Customer.last_name == "Dupont",
        ).first()
        assert customer is not None
        assert customer.email is None

    def test_invalid_phone_is_cleared_but_row_imported(self, db: Session, default_tenant):
        csv_content = _make_csv([
            ["Nom", "Prenom", "Telephone"],
            ["Dupont", "Jean", "INVALID_PHONE_XYZ"],
        ])
        with patch("app.services.client_import_service.audit_service") as mock_audit:
            mock_audit.log_action = MagicMock()
            result = import_from_file(
                db, default_tenant.id, csv_content, "import.csv", user_id=1
            )

        assert result.imported == 1
        assert any("Telephone invalide" in e.reason for e in result.errors)

        customer = db.query(Customer).filter(
            Customer.tenant_id == default_tenant.id,
            Customer.last_name == "Dupont",
        ).first()
        assert customer.phone is None

    def test_birth_date_parsed_correctly(self, db: Session, default_tenant):
        csv_content = _make_csv([
            ["Nom", "Prenom", "Date de naissance"],
            ["Dupont", "Jean", "15/03/1985"],
        ])
        with patch("app.services.client_import_service.audit_service") as mock_audit:
            mock_audit.log_action = MagicMock()
            import_from_file(
                db, default_tenant.id, csv_content, "import.csv", user_id=1
            )

        customer = db.query(Customer).filter(
            Customer.tenant_id == default_tenant.id,
            Customer.last_name == "Dupont",
        ).first()
        assert customer is not None
        assert customer.birth_date == date(1985, 3, 15)

    def test_empty_file_returns_zero_counts(self, db: Session, default_tenant):
        # CSV with only a header row
        csv_content = _make_csv([["Nom", "Prenom", "Email"]])
        with patch("app.services.client_import_service.audit_service") as mock_audit:
            mock_audit.log_action = MagicMock()
            result = import_from_file(
                db, default_tenant.id, csv_content, "import.csv", user_id=1
            )

        assert result.imported == 0
        assert result.updated == 0
        assert result.skipped == 0

    def test_completely_empty_file_returns_zero_counts(self, db: Session, default_tenant):
        csv_content = b""
        with patch("app.services.client_import_service.audit_service") as mock_audit:
            mock_audit.log_action = MagicMock()
            result = import_from_file(
                db, default_tenant.id, csv_content, "import.csv", user_id=1
            )

        assert result.imported == 0

    def test_comma_delimiter_detected(self, db: Session, default_tenant):
        csv_content = "Nom,Prenom,Email\nDupont,Jean,jean@test.fr\n".encode("utf-8-sig")
        with patch("app.services.client_import_service.audit_service") as mock_audit:
            mock_audit.log_action = MagicMock()
            result = import_from_file(
                db, default_tenant.id, csv_content, "import.csv", user_id=1
            )

        assert result.imported == 1

    def test_audit_log_is_called(self, db: Session, default_tenant):
        csv_content = _make_csv([
            ["Nom", "Prenom"],
            ["Dupont", "Jean"],
        ])
        with patch("app.services.client_import_service.audit_service") as mock_audit:
            mock_audit.log_action = MagicMock()
            import_from_file(
                db, default_tenant.id, csv_content, "import.csv", user_id=99
            )
            mock_audit.log_action.assert_called_once()
            call_kwargs = mock_audit.log_action.call_args
            assert call_kwargs.args[2] == 99  # user_id


# ---------------------------------------------------------------------------
# Tests for duplicate detection (update path)
# ---------------------------------------------------------------------------

class TestImportDuplicateDetection:
    def test_existing_client_by_email_is_updated(self, db: Session, default_tenant):
        # Pre-create a customer
        existing = Customer(
            tenant_id=default_tenant.id,
            first_name="OldFirst",
            last_name="OldLast",
            email="existing@test.fr",
        )
        db.add(existing)
        db.commit()

        csv_content = _make_csv([
            ["Nom", "Prenom", "Email", "Telephone"],
            ["NewLast", "NewFirst", "existing@test.fr", "0612345678"],
        ])
        with patch("app.services.client_import_service.audit_service") as mock_audit:
            mock_audit.log_action = MagicMock()
            result = import_from_file(
                db, default_tenant.id, csv_content, "import.csv", user_id=1
            )

        assert result.imported == 0
        assert result.updated == 1

        db.refresh(existing)
        assert existing.last_name == "NewLast"
        assert existing.first_name == "NewFirst"
        assert existing.phone == "0612345678"

    def test_existing_client_no_changes_is_skipped(self, db: Session, default_tenant):
        existing = Customer(
            tenant_id=default_tenant.id,
            first_name="Jean",
            last_name="Dupont",
            email="same@test.fr",
        )
        db.add(existing)
        db.commit()

        # Import the same data — no fields change
        csv_content = _make_csv([
            ["Nom", "Prenom", "Email"],
            ["Dupont", "Jean", "same@test.fr"],
        ])
        with patch("app.services.client_import_service.audit_service") as mock_audit:
            mock_audit.log_action = MagicMock()
            result = import_from_file(
                db, default_tenant.id, csv_content, "import.csv", user_id=1
            )

        assert result.imported == 0
        assert result.updated == 0
        assert result.skipped == 1

    def test_duplicate_check_is_scoped_to_tenant(self, db: Session, default_tenant):
        """A customer in a different tenant should NOT trigger update."""
        from app.models.tenant import Organization, Tenant

        other_org = Organization(name="Other Org", slug="other-org", plan="solo")
        db.add(other_org)
        db.flush()
        other_tenant = Tenant(
            organization_id=other_org.id,
            name="Other Shop",
            slug="other-shop",
        )
        db.add(other_tenant)
        db.flush()

        other_customer = Customer(
            tenant_id=other_tenant.id,
            first_name="Jean",
            last_name="Dupont",
            email="shared@test.fr",
        )
        db.add(other_customer)
        db.commit()

        csv_content = _make_csv([
            ["Nom", "Prenom", "Email"],
            ["Dupont", "Jean", "shared@test.fr"],
        ])
        with patch("app.services.client_import_service.audit_service") as mock_audit:
            mock_audit.log_action = MagicMock()
            result = import_from_file(
                db, default_tenant.id, csv_content, "import.csv", user_id=1
            )

        # Creates a new record for default_tenant, does NOT update other_tenant's record
        assert result.imported == 1
        assert result.updated == 0

    def test_deleted_customer_not_matched_as_duplicate(self, db: Session, default_tenant):
        from datetime import UTC, datetime

        soft_deleted = Customer(
            tenant_id=default_tenant.id,
            first_name="Jean",
            last_name="Dupont",
            email="deleted@test.fr",
            deleted_at=datetime.now(UTC),
        )
        db.add(soft_deleted)
        db.commit()

        csv_content = _make_csv([
            ["Nom", "Prenom", "Email"],
            ["Dupont", "Jean", "deleted@test.fr"],
        ])
        with patch("app.services.client_import_service.audit_service") as mock_audit:
            mock_audit.log_action = MagicMock()
            result = import_from_file(
                db, default_tenant.id, csv_content, "import.csv", user_id=1
            )

        # Soft-deleted customer should not block a fresh import
        assert result.imported == 1


# ---------------------------------------------------------------------------
# Tests for column mapping
# ---------------------------------------------------------------------------

class TestColumnMapping:
    @pytest.mark.parametrize("header,expected_last_name", [
        ("Nom", "Rossi"),
        ("nom de famille", "Rossi"),
        ("last_name", "Rossi"),
        ("LastName", "Rossi"),
    ])
    def test_last_name_variants(self, db: Session, default_tenant, header: str, expected_last_name: str):
        csv_content = _make_csv([
            [header, "Prenom"],
            ["Rossi", "Mario"],
        ])
        with patch("app.services.client_import_service.audit_service") as mock_audit:
            mock_audit.log_action = MagicMock()
            result = import_from_file(
                db, default_tenant.id, csv_content, f"import_{header}.csv", user_id=1
            )

        assert result.imported == 1
        customer = db.query(Customer).filter(
            Customer.tenant_id == default_tenant.id,
            Customer.last_name == expected_last_name,
        ).first()
        assert customer is not None

    @pytest.mark.parametrize("header", [
        "Prenom", "prénom", "first_name", "FirstName",
    ])
    def test_first_name_variants(self, db: Session, default_tenant, header: str):
        csv_content = _make_csv([
            ["Nom", header],
            ["TestFirst", "Mario"],
        ])
        with patch("app.services.client_import_service.audit_service") as mock_audit:
            mock_audit.log_action = MagicMock()
            import_from_file(
                db, default_tenant.id, csv_content, f"import_{header}.csv", user_id=1
            )

        customer = db.query(Customer).filter(
            Customer.tenant_id == default_tenant.id,
            Customer.last_name == "TestFirst",
        ).first()
        assert customer is not None
        assert customer.first_name == "Mario"

    @pytest.mark.parametrize("header", [
        "Email", "e-mail", "mail", "adresse email",
    ])
    def test_email_column_variants(self, db: Session, default_tenant, header: str):
        csv_content = _make_csv([
            ["Nom", header],
            ["EmailVariant", "test@example.com"],
        ])
        with patch("app.services.client_import_service.audit_service") as mock_audit:
            mock_audit.log_action = MagicMock()
            import_from_file(
                db, default_tenant.id, csv_content, "import.csv", user_id=1
            )

        customer = db.query(Customer).filter(
            Customer.tenant_id == default_tenant.id,
            Customer.last_name == "EmailVariant",
        ).first()
        assert customer is not None
        assert customer.email == "test@example.com"

    def test_unknown_columns_are_ignored(self, db: Session, default_tenant):
        csv_content = _make_csv([
            ["Nom", "Prenom", "ColonneInconnue", "AutreColonne"],
            ["Dupont", "Jean", "valeur1", "valeur2"],
        ])
        with patch("app.services.client_import_service.audit_service") as mock_audit:
            mock_audit.log_action = MagicMock()
            result = import_from_file(
                db, default_tenant.id, csv_content, "import.csv", user_id=1
            )

        assert result.imported == 1
        assert result.errors == []

    def test_all_optional_fields_mapped(self, db: Session, default_tenant):
        csv_content = _make_csv([
            ["Nom", "Prenom", "Email", "Telephone", "Adresse", "Ville", "Code postal", "Notes"],
            ["Dupont", "Jean", "full@test.fr", "0612345678", "12 rue de la Paix", "Paris", "75001", "VIP"],
        ])
        with patch("app.services.client_import_service.audit_service") as mock_audit:
            mock_audit.log_action = MagicMock()
            import_from_file(
                db, default_tenant.id, csv_content, "import.csv", user_id=1
            )

        customer = db.query(Customer).filter(
            Customer.tenant_id == default_tenant.id,
            Customer.email == "full@test.fr",
        ).first()
        assert customer is not None
        assert customer.city == "Paris"
        assert customer.postal_code == "75001"
        assert customer.notes == "VIP"


# ---------------------------------------------------------------------------
# Tests for generate_import_template
# ---------------------------------------------------------------------------

class TestGenerateImportTemplate:
    def test_returns_bytes(self):
        template = generate_import_template()
        assert isinstance(template, bytes)

    def test_contains_expected_headers(self):
        template = generate_import_template()
        text = template.decode("utf-8-sig")
        assert "Nom" in text
        assert "Prenom" in text
        assert "Email" in text

    def test_contains_example_row(self):
        template = generate_import_template()
        text = template.decode("utf-8-sig")
        assert "Dupont" in text

    def test_uses_semicolon_delimiter(self):
        template = generate_import_template()
        text = template.decode("utf-8-sig")
        first_line = text.split("\n")[0]
        assert ";" in first_line


# ---------------------------------------------------------------------------
# Test error cap
# ---------------------------------------------------------------------------

class TestErrorCap:
    def test_errors_capped_at_50(self, db: Session, default_tenant):
        """More than 50 invalid rows: result.errors must be capped at 50."""
        rows = [["Nom", "Prenom"]]
        for i in range(60):
            rows.append(["", f"NoLastName{i}"])  # missing last name → skipped + error

        csv_content = _make_csv(rows)
        with patch("app.services.client_import_service.audit_service") as mock_audit:
            mock_audit.log_action = MagicMock()
            result = import_from_file(
                db, default_tenant.id, csv_content, "import.csv", user_id=1
            )

        assert result.skipped == 60
        assert len(result.errors) == 50
