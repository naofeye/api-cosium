"""Tests E2E V12 — PEC Intelligence module.

Covers the full PEC preparation workflow via HTTP endpoints,
consolidation logic, incoherence detection, and data quality.
"""

from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.domain.schemas.consolidation import (
    ConsolidatedClientProfile,
    ConsolidatedField,
)
from app.models import (
    Case,
    ClientMutuelle,
    CosiumInvoice,
    CosiumPrescription,
    Customer,
    Devis,
    DevisLigne,
    Tenant,
    User,
)
from app.services.consolidation_service import consolidate_client_for_pec
from app.services.incoherence_detector import detect_incoherences


# ---------------------------------------------------------------------------
# Helper to build ConsolidatedField quickly
# ---------------------------------------------------------------------------

def _field(value, source="test", confidence=1.0):
    return ConsolidatedField(
        value=value,
        source=source,
        source_label="Test",
        confidence=confidence,
        last_updated=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Fixtures shared across all tests
# ---------------------------------------------------------------------------

@pytest.fixture(name="tenant_id")
def _tenant_id(db):
    return db.query(Tenant).filter(Tenant.slug == "test-magasin").first().id


@pytest.fixture(name="user_id")
def _user_id(db):
    return db.query(User).first().id


@pytest.fixture(name="customer_full")
def _customer_full(db, tenant_id):
    """Customer with SSN and complete identity."""
    c = Customer(
        tenant_id=tenant_id,
        first_name="Marie",
        last_name="MARTIN",
        birth_date=date(1990, 6, 12),
        social_security_number="2900675123456",
        email="marie.martin@test.fr",
        phone="0611223344",
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@pytest.fixture(name="customer_minimal")
def _customer_minimal(db, tenant_id):
    """Customer with no SSN, no extras."""
    c = Customer(
        tenant_id=tenant_id,
        first_name="Pierre",
        last_name="SANS_SSN",
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@pytest.fixture(name="case_for_customer")
def _case_for_customer(db, tenant_id, customer_full):
    case = Case(
        tenant_id=tenant_id,
        customer_id=customer_full.id,
        status="en_cours",
        source="test",
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


@pytest.fixture(name="prescription_recent")
def _prescription_recent(db, tenant_id, customer_full):
    p = CosiumPrescription(
        tenant_id=tenant_id,
        cosium_id=9001,
        customer_id=customer_full.id,
        prescription_date="01/02/2026",
        file_date=datetime(2026, 2, 1, tzinfo=UTC),
        sphere_right=1.25,
        cylinder_right=-0.50,
        axis_right=85,
        addition_right=1.50,
        sphere_left=1.75,
        cylinder_left=-0.75,
        axis_left=95,
        addition_left=1.50,
        prescriber_name="Dr Lefevre",
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@pytest.fixture(name="devis_for_case")
def _devis_for_case(db, tenant_id, case_for_customer):
    d = Devis(
        tenant_id=tenant_id,
        case_id=case_for_customer.id,
        numero="D-V12-001",
        status="signe",
        montant_ht=500.00,
        tva=100.00,
        montant_ttc=600.00,
        part_secu=80.00,
        part_mutuelle=320.00,
        reste_a_charge=200.00,
    )
    db.add(d)
    db.flush()
    db.add(DevisLigne(
        tenant_id=tenant_id,
        devis_id=d.id,
        designation="Cadre titane",
        quantite=1,
        prix_unitaire_ht=166.67,
        taux_tva=20.0,
        montant_ht=166.67,
        montant_ttc=200.00,
    ))
    db.add(DevisLigne(
        tenant_id=tenant_id,
        devis_id=d.id,
        designation="Verre progressif OD",
        quantite=1,
        prix_unitaire_ht=166.67,
        taux_tva=20.0,
        montant_ht=166.67,
        montant_ttc=200.00,
    ))
    db.add(DevisLigne(
        tenant_id=tenant_id,
        devis_id=d.id,
        designation="Verre progressif OG",
        quantite=1,
        prix_unitaire_ht=166.67,
        taux_tva=20.0,
        montant_ht=166.67,
        montant_ttc=200.00,
    ))
    db.commit()
    db.refresh(d)
    return d


@pytest.fixture(name="mutuelle_active")
def _mutuelle_active(db, tenant_id, customer_full):
    m = ClientMutuelle(
        tenant_id=tenant_id,
        customer_id=customer_full.id,
        mutuelle_name="ALMERYS SANTE",
        numero_adherent="AL-789012",
        type_beneficiaire="assure",
        date_fin=date(2027, 12, 31),
        source="cosium_tpp",
        confidence=0.92,
        active=True,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


# ===========================================================================
# SECTION A: PEC Full Flow (8 tests) — HTTP endpoints
# ===========================================================================


class TestPecFullFlow:
    """End-to-end tests hitting the FastAPI endpoints."""

    def test_01_create_client_devis_prepare_pec(
        self, client: TestClient, auth_headers: dict, db, tenant_id,
    ):
        """1. Create client -> create devis -> prepare PEC -> verify consolidated data."""
        # Create client via API
        resp = client.post(
            "/api/v1/clients",
            json={
                "first_name": "Luc",
                "last_name": "Testeur",
                "email": "luc.testeur@test.fr",
                "social_security_number": "1950175111222",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        cust_id = resp.json()["id"]

        # Create case
        resp = client.post(
            "/api/v1/cases",
            json={"first_name": "Luc", "last_name": "Testeur", "source": "v12_test"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        case_id = resp.json()["id"]

        # Create devis
        resp = client.post(
            "/api/v1/devis",
            json={
                "case_id": case_id,
                "part_secu": 60,
                "part_mutuelle": 200,
                "lignes": [
                    {"designation": "Monture test", "quantite": 1, "prix_unitaire_ht": 100, "taux_tva": 20},
                    {"designation": "Verre OD test", "quantite": 1, "prix_unitaire_ht": 80, "taux_tva": 20},
                ],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201

        # Prepare PEC
        resp = client.post(
            f"/api/v1/clients/{cust_id}/pec-preparation",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["customer_id"] == cust_id
        assert data["consolidated_data"] is not None
        assert data["completude_score"] >= 0

    def test_02_prepare_without_prescription(
        self, client: TestClient, auth_headers: dict, db, tenant_id,
        customer_full, case_for_customer, devis_for_case, mutuelle_active,
    ):
        """2. PEC for client without prescription -> 'ordonnance requise' alert."""
        resp = client.post(
            f"/api/v1/clients/{customer_full.id}/pec-preparation",
            json={"devis_id": devis_for_case.id},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["errors_count"] > 0
        # Check consolidated data contains missing ordonnance
        consolidated = data["consolidated_data"]
        assert consolidated is not None
        missing = consolidated.get("champs_manquants", [])
        assert "date_ordonnance" in missing or "sphere_od" in missing

    def test_03_prepare_without_devis(
        self, client: TestClient, auth_headers: dict, db, tenant_id,
        customer_full, case_for_customer, prescription_recent, mutuelle_active,
    ):
        """3. PEC for client without devis -> 'devis requis' alert."""
        resp = client.post(
            f"/api/v1/clients/{customer_full.id}/pec-preparation",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        consolidated = data["consolidated_data"]
        missing = consolidated.get("champs_manquants", [])
        assert "montant_ttc" in missing

    def test_04_validate_field(
        self, client: TestClient, auth_headers: dict, db, tenant_id,
        customer_full, case_for_customer, prescription_recent, devis_for_case, mutuelle_active,
    ):
        """4. Validate a field -> user_validations updated."""
        # Create prep
        resp = client.post(
            f"/api/v1/clients/{customer_full.id}/pec-preparation",
            json={"devis_id": devis_for_case.id},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        prep_id = resp.json()["id"]

        # Validate 'nom'
        resp = client.post(
            f"/api/v1/pec-preparations/{prep_id}/validate-field",
            json={"field_name": "nom"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_validations"] is not None
        assert "nom" in data["user_validations"]
        assert data["user_validations"]["nom"]["validated"] is True

    def test_05_correct_field(
        self, client: TestClient, auth_headers: dict, db, tenant_id,
        customer_full, case_for_customer, prescription_recent, devis_for_case, mutuelle_active,
    ):
        """5. Correct a field -> user_corrections updated + alerts recalculated."""
        resp = client.post(
            f"/api/v1/clients/{customer_full.id}/pec-preparation",
            json={"devis_id": devis_for_case.id},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        prep_id = resp.json()["id"]

        # Correct numero_secu
        resp = client.post(
            f"/api/v1/pec-preparations/{prep_id}/correct-field",
            json={"field_name": "numero_secu", "new_value": "1990675999888"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_corrections"] is not None
        assert "numero_secu" in data["user_corrections"]
        assert data["user_corrections"]["numero_secu"]["corrected"] == "1990675999888"

    def test_06_refresh_preparation(
        self, client: TestClient, auth_headers: dict, db, tenant_id,
        customer_full, case_for_customer, prescription_recent, devis_for_case, mutuelle_active,
    ):
        """6. Refresh preparation -> data re-consolidated."""
        resp = client.post(
            f"/api/v1/clients/{customer_full.id}/pec-preparation",
            json={"devis_id": devis_for_case.id},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        prep_id = resp.json()["id"]
        original_score = resp.json()["completude_score"]

        # Refresh
        resp = client.post(
            f"/api/v1/pec-preparations/{prep_id}/refresh",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == prep_id
        assert data["consolidated_data"] is not None
        # Score should be same or recalculated
        assert data["completude_score"] >= 0

    def test_07_submit_preparation_creates_pec(
        self, client: TestClient, auth_headers: dict, db, tenant_id,
        customer_full, case_for_customer, prescription_recent, devis_for_case, mutuelle_active,
    ):
        """7. Submit ready preparation -> PecRequest created."""
        resp = client.post(
            f"/api/v1/clients/{customer_full.id}/pec-preparation",
            json={"devis_id": devis_for_case.id},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        prep_id = resp.json()["id"]

        # Force status to 'prete' if not already (some alerts may block)
        from app.repositories import pec_preparation_repo
        db_prep = pec_preparation_repo.get_by_id(db, prep_id, tenant_id)
        if db_prep and db_prep.status != "prete":
            pec_preparation_repo.update(db, db_prep, status="prete")

        # Attach required documents for submission validation
        resp_doc1 = client.post(
            f"/api/v1/pec-preparations/{prep_id}/documents",
            json={"document_role": "ordonnance"},
            headers=auth_headers,
        )
        assert resp_doc1.status_code == 201
        resp_doc2 = client.post(
            f"/api/v1/pec-preparations/{prep_id}/documents",
            json={"document_role": "devis"},
            headers=auth_headers,
        )
        assert resp_doc2.status_code == 201

        resp = client.post(
            f"/api/v1/pec-preparations/{prep_id}/submit",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["pec_request_id"] > 0
        assert data["status"] == "soumise"

    def test_08_submit_with_errors_rejected(
        self, client: TestClient, auth_headers: dict, db, tenant_id,
        customer_minimal,
    ):
        """8. Submit preparation with errors -> rejected (PREPARATION_NOT_READY)."""
        # Create a prep with minimal data -> will have errors
        resp = client.post(
            f"/api/v1/clients/{customer_minimal.id}/pec-preparation",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        prep_id = resp.json()["id"]
        assert resp.json()["status"] == "en_preparation"

        # Attempt to submit
        resp = client.post(
            f"/api/v1/pec-preparations/{prep_id}/submit",
            headers=auth_headers,
        )
        assert resp.status_code == 400
        error_body = resp.json().get("error", {})
        # PREPARATION_NOT_READY may appear in code or message depending on serialization
        error_text = f"{error_body.get('code', '')} {error_body.get('message', '')}"
        assert "PREPARATION_NOT_READY" in error_text


# ===========================================================================
# SECTION B: Consolidation (5 tests) — service level
# ===========================================================================


class TestConsolidationV12:
    """Consolidation service tests."""

    def test_09_full_data_high_score(
        self, db, tenant_id, customer_full, case_for_customer,
        prescription_recent, devis_for_case, mutuelle_active,
    ):
        """9. Consolidation with full data -> score > 80%."""
        profile = consolidate_client_for_pec(
            db, tenant_id, customer_full.id, devis_for_case.id,
        )
        assert profile.score_completude > 80.0

    def test_10_minimal_data_low_score(self, db, tenant_id, customer_minimal):
        """10. Consolidation with minimal data -> low score + many missing fields."""
        profile = consolidate_client_for_pec(db, tenant_id, customer_minimal.id)
        assert profile.score_completude < 50.0
        assert len(profile.champs_manquants) >= 5

    def test_11_source_traceability(
        self, db, tenant_id, customer_full, case_for_customer,
        prescription_recent, devis_for_case, mutuelle_active,
    ):
        """11. Every populated field records its source."""
        profile = consolidate_client_for_pec(
            db, tenant_id, customer_full.id, devis_for_case.id,
        )
        # Check identity from cosium_client
        assert profile.nom is not None
        assert profile.nom.source == "cosium_client"
        assert profile.nom.source_label is not None

        # Check optical from prescription
        assert profile.sphere_od is not None
        assert "cosium_prescription" in profile.sphere_od.source

        # Check financial from devis
        assert profile.montant_ttc is not None
        assert "devis" in profile.montant_ttc.source

        # Check mutuelle
        assert profile.mutuelle_nom is not None
        assert profile.mutuelle_nom.source_label is not None

    def test_12_consolidation_with_mutuelle(
        self, db, tenant_id, customer_full, mutuelle_active,
    ):
        """12. Consolidation with mutuelle -> mutuelle fields populated."""
        profile = consolidate_client_for_pec(db, tenant_id, customer_full.id)
        assert profile.mutuelle_nom is not None
        assert profile.mutuelle_nom.value == "ALMERYS SANTE"
        assert profile.mutuelle_numero_adherent is not None
        assert profile.mutuelle_numero_adherent.value == "AL-789012"

    def test_13_cosium_data_takes_priority(
        self, db, tenant_id, customer_full,
    ):
        """13. Cosium client data takes priority over other sources."""
        profile = consolidate_client_for_pec(db, tenant_id, customer_full.id)
        # Identity from Cosium client should have source cosium_client (priority 5)
        assert profile.nom is not None
        assert profile.nom.source == "cosium_client"
        assert profile.nom.confidence == 1.0


# ===========================================================================
# SECTION C: Incoherence Detection (5 tests) — unit level
# ===========================================================================


class TestIncoherenceDetectionV12:
    """Incoherence detection tests."""

    def test_14_expired_prescription_error(self):
        """14. Prescription > 3 years -> error alert."""
        old_date = (date.today() - timedelta(days=4 * 365)).strftime("%Y-%m-%d")
        profile = ConsolidatedClientProfile(
            nom=_field("TEST"),
            prenom=_field("User"),
            numero_secu=_field("1234567890123"),
            mutuelle_nom=_field("TEST MUT"),
            mutuelle_numero_adherent=_field("TM-001"),
            date_ordonnance=_field(old_date),
            sphere_od=_field(1.0),
            sphere_og=_field(1.0),
            montant_ttc=_field(500.0),
            part_secu=_field(100.0),
            part_mutuelle=_field(200.0),
            reste_a_charge=_field(200.0),
        )
        alerts = detect_incoherences(profile)
        ordo_errors = [
            a for a in alerts
            if a.severity == "error" and a.field == "date_ordonnance"
        ]
        assert len(ordo_errors) >= 1
        assert "perimee" in ordo_errors[0].message.lower()

    def test_15_financial_inconsistency(self):
        """15. secu + mutuelle > TTC -> error alert."""
        profile = ConsolidatedClientProfile(
            nom=_field("TEST"),
            prenom=_field("User"),
            numero_secu=_field("1234567890123"),
            mutuelle_nom=_field("TEST MUT"),
            mutuelle_numero_adherent=_field("TM-001"),
            date_ordonnance=_field(
                (date.today() - timedelta(days=10)).strftime("%Y-%m-%d")
            ),
            sphere_od=_field(1.0),
            sphere_og=_field(1.0),
            montant_ttc=_field(400.0),
            part_secu=_field(250.0),
            part_mutuelle=_field(250.0),
            reste_a_charge=_field(0.0),
        )
        alerts = detect_incoherences(profile)
        financial_errors = [
            a for a in alerts
            if a.severity == "error" and a.field == "financial"
        ]
        assert len(financial_errors) >= 1
        assert "depasse" in financial_errors[0].message.lower()

    def test_16_missing_ssn_error(self):
        """16. Missing SSN -> error alert."""
        profile = ConsolidatedClientProfile(
            nom=_field("TEST"),
            prenom=_field("User"),
            # numero_secu intentionally omitted
            mutuelle_nom=_field("TEST MUT"),
            mutuelle_numero_adherent=_field("TM-001"),
            date_ordonnance=_field(
                (date.today() - timedelta(days=10)).strftime("%Y-%m-%d")
            ),
            sphere_od=_field(1.0),
            sphere_og=_field(1.0),
            montant_ttc=_field(500.0),
            part_secu=_field(100.0),
            part_mutuelle=_field(200.0),
            reste_a_charge=_field(200.0),
        )
        alerts = detect_incoherences(profile)
        ssn_errors = [
            a for a in alerts
            if a.severity == "error" and a.field == "numero_secu"
        ]
        assert len(ssn_errors) >= 1

    def test_17_valid_profile_no_errors(self):
        """17. Valid profile -> no error-level alerts."""
        recent = (date.today() - timedelta(days=15)).strftime("%Y-%m-%d")
        profile = ConsolidatedClientProfile(
            nom=_field("DUPONT"),
            prenom=_field("Jean"),
            numero_secu=_field("1850375123456"),
            mutuelle_nom=_field("HARMONIE"),
            mutuelle_numero_adherent=_field("HM-999"),
            date_ordonnance=_field(recent),
            sphere_od=_field(2.50),
            sphere_og=_field(3.00),
            montant_ttc=_field(700.0),
            part_secu=_field(100.0),
            part_mutuelle=_field(350.0),
            reste_a_charge=_field(250.0),
        )
        alerts = detect_incoherences(profile)
        errors = [a for a in alerts if a.severity == "error"]
        assert len(errors) == 0

    def test_18_multiple_warnings_sorted(self):
        """18. Multiple warnings -> correct severity sorting (errors first)."""
        profile = ConsolidatedClientProfile(
            # Missing SSN -> error
            # Missing ordonnance -> error
            # Missing montant_ttc -> error
            # part_mutuelle > 0 but no mutuelle_nom -> warning
            part_mutuelle=_field(300.0),
            reste_a_charge=_field(-10.0),  # negative RAC -> error
        )
        alerts = detect_incoherences(profile)
        assert len(alerts) >= 3
        # Verify sorting: all errors before all warnings
        seen_warning = False
        for alert in alerts:
            if alert.severity == "warning":
                seen_warning = True
            if alert.severity == "error" and seen_warning:
                pytest.fail("Error found after warning: sorting is incorrect")


# ===========================================================================
# SECTION D: Data Quality (2 tests)
# ===========================================================================


class TestDataQualityV12:
    """Data quality endpoint tests."""

    def test_19_data_quality_returns_link_rates(
        self, client: TestClient, auth_headers: dict, db, tenant_id,
        customer_full,
    ):
        """19. GET /admin/data-quality returns correct link rates."""
        # Insert a CosiumInvoice linked to customer
        inv = CosiumInvoice(
            tenant_id=tenant_id,
            cosium_id=8001,
            invoice_number="INV-001",
            customer_id=customer_full.id,
            type="invoice",
        )
        db.add(inv)
        # Insert an orphan CosiumInvoice (no customer_id)
        inv2 = CosiumInvoice(
            tenant_id=tenant_id,
            cosium_id=8002,
            invoice_number="INV-002",
            customer_id=None,
            type="invoice",
        )
        db.add(inv2)
        db.commit()

        resp = client.get("/api/v1/admin/data-quality", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "invoices" in data
        invoices = data["invoices"]
        assert invoices["total"] >= 2
        assert invoices["linked"] >= 1
        assert invoices["orphan"] >= 1
        assert 0.0 <= invoices["link_rate"] <= 100.0

    def test_20_client_mutuelle_detection(
        self, db, tenant_id, customer_full, mutuelle_active,
    ):
        """20. Client mutuelle detected and populated in consolidation."""
        profile = consolidate_client_for_pec(db, tenant_id, customer_full.id)
        assert profile.mutuelle_nom is not None
        assert profile.mutuelle_nom.value == "ALMERYS SANTE"
        assert profile.mutuelle_numero_adherent is not None
        assert profile.type_beneficiaire is not None
        assert profile.type_beneficiaire.value == "assure"
