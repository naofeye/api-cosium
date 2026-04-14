"""Tests for PEC intelligence: consolidation, incoherence detection, preparation service."""

import json
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import (
    Case,
    ClientMutuelle,
    CosiumPrescription,
    Customer,
    Devis,
    DevisLigne,
    Document,
    DocumentExtraction,
    DocumentType,
    Organization,
    PayerOrganization,
    PecPreparation,
    PecPreparationDocument,
    ReminderTemplate,
    Tenant,
    TenantUser,
    User,
)
from app.security import hash_password
from app.seed import DOCUMENT_TYPES
from app.services.consolidation_service import consolidate_client_for_pec
from app.services.incoherence_detector import (
    detect_financial_incoherences,
    detect_identity_incoherences,
    detect_incoherences,
    detect_missing_data,
    detect_optical_incoherences,
)
from app.services import pec_preparation_service
from app.domain.schemas.consolidation import (
    ConsolidatedClientProfile,
    ConsolidatedField,
    ConsolidationAlert,
)


@pytest.fixture(name="test_db")
def test_db_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = TestSession()

    # Seed org + tenant
    org = Organization(name="Test Org", slug="test-org", plan="solo")
    db.add(org)
    db.flush()
    tenant = Tenant(organization_id=org.id, name="Test Magasin", slug="test-magasin")
    db.add(tenant)
    db.flush()

    # Seed document types
    for dt_data in DOCUMENT_TYPES:
        db.add(DocumentType(**dt_data))

    # Seed reminder template
    db.add(ReminderTemplate(
        tenant_id=tenant.id,
        name="Default", channel="email", payer_type="client",
        subject="Relance", body="body", is_default=True,
    ))

    # Seed user
    user = User(email="test@optiflow.com", password_hash=hash_password("test123"), role="admin", is_active=True)
    db.add(user)
    db.flush()
    db.add(TenantUser(user_id=user.id, tenant_id=tenant.id, role="admin"))
    db.commit()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(name="tenant_id")
def tenant_id_fixture(test_db):
    return test_db.query(Tenant).first().id


@pytest.fixture(name="user_id")
def user_id_fixture(test_db):
    return test_db.query(User).first().id


@pytest.fixture(name="customer")
def customer_fixture(test_db, tenant_id):
    c = Customer(
        tenant_id=tenant_id,
        first_name="Jean",
        last_name="DUPONT",
        birth_date=date(1985, 3, 15),
        social_security_number="1850375123456",
        email="jean.dupont@test.fr",
        phone="0601020304",
    )
    test_db.add(c)
    test_db.commit()
    test_db.refresh(c)
    return c


@pytest.fixture(name="case_obj")
def case_fixture(test_db, tenant_id, customer):
    case = Case(tenant_id=tenant_id, customer_id=customer.id, status="en_cours", source="manual")
    test_db.add(case)
    test_db.commit()
    test_db.refresh(case)
    return case


@pytest.fixture(name="prescription")
def prescription_fixture(test_db, tenant_id, customer):
    p = CosiumPrescription(
        tenant_id=tenant_id,
        cosium_id=1001,
        customer_id=customer.id,
        prescription_date="15/03/2026",
        file_date=datetime(2026, 3, 15, tzinfo=UTC),
        sphere_right=2.50,
        cylinder_right=-0.75,
        axis_right=90,
        addition_right=2.00,
        sphere_left=3.00,
        cylinder_left=-1.00,
        axis_left=180,
        addition_left=2.00,
        prescriber_name="Dr Martin",
    )
    test_db.add(p)
    test_db.commit()
    test_db.refresh(p)
    return p


@pytest.fixture(name="devis_obj")
def devis_fixture(test_db, tenant_id, case_obj):
    d = Devis(
        tenant_id=tenant_id,
        case_id=case_obj.id,
        numero="D-2026-042",
        status="signe",
        montant_ht=600.00,
        tva=120.00,
        montant_ttc=720.00,
        part_secu=100.00,
        part_mutuelle=400.00,
        reste_a_charge=220.00,
    )
    test_db.add(d)
    test_db.flush()
    # Add lignes
    test_db.add(DevisLigne(
        tenant_id=tenant_id, devis_id=d.id,
        designation="Monture Ray-Ban RB5154",
        quantite=1, prix_unitaire_ht=125.00, taux_tva=20.0,
        montant_ht=125.00, montant_ttc=150.00,
    ))
    test_db.add(DevisLigne(
        tenant_id=tenant_id, devis_id=d.id,
        designation="Verre progressif OD Essilor",
        quantite=1, prix_unitaire_ht=233.33, taux_tva=20.0,
        montant_ht=233.33, montant_ttc=280.00,
    ))
    test_db.add(DevisLigne(
        tenant_id=tenant_id, devis_id=d.id,
        designation="Verre progressif OG Essilor",
        quantite=1, prix_unitaire_ht=241.67, taux_tva=20.0,
        montant_ht=241.67, montant_ttc=290.00,
    ))
    test_db.commit()
    test_db.refresh(d)
    return d


@pytest.fixture(name="mutuelle")
def mutuelle_fixture(test_db, tenant_id, customer):
    m = ClientMutuelle(
        tenant_id=tenant_id,
        customer_id=customer.id,
        mutuelle_name="HARMONIE MUTUELLE",
        numero_adherent="HM-123456",
        type_beneficiaire="assure",
        date_fin=date(2027, 12, 31),
        source="cosium_tpp",
        confidence=0.9,
        active=True,
    )
    test_db.add(m)
    test_db.commit()
    test_db.refresh(m)
    return m


# ============================================================
# STEP 5: Consolidation tests
# ============================================================


class TestConsolidation:
    """Tests for the consolidation service."""

    def test_consolidation_full_data(self, test_db, tenant_id, customer, case_obj, prescription, devis_obj, mutuelle):
        """Test consolidation with all data sources present."""
        profile = consolidate_client_for_pec(test_db, tenant_id, customer.id, devis_obj.id)

        assert profile.nom is not None
        assert profile.nom.value == "DUPONT"
        assert profile.nom.source == "cosium_client"

        assert profile.prenom is not None
        assert profile.prenom.value == "Jean"

        assert profile.numero_secu is not None
        assert profile.numero_secu.value == "1850375123456"

        assert profile.sphere_od is not None
        assert profile.sphere_od.value == 2.50

        assert profile.sphere_og is not None
        assert profile.sphere_og.value == 3.00

        assert profile.prescripteur is not None
        assert profile.prescripteur.value == "Dr Martin"

        assert profile.montant_ttc is not None
        assert profile.montant_ttc.value == 720.00

        assert profile.mutuelle_nom is not None
        assert profile.mutuelle_nom.value == "HARMONIE MUTUELLE"

        assert profile.monture is not None
        assert "Ray-Ban" in str(profile.monture.value)

        assert len(profile.verres) == 2

        assert profile.score_completude > 0
        assert len(profile.sources_utilisees) >= 3

    def test_consolidation_missing_prescription(self, test_db, tenant_id, customer, case_obj, devis_obj, mutuelle):
        """Test consolidation when no prescription exists."""
        profile = consolidate_client_for_pec(test_db, tenant_id, customer.id, devis_obj.id)

        assert profile.nom is not None
        assert profile.sphere_od is None
        assert profile.sphere_og is None
        assert profile.date_ordonnance is None
        assert "date_ordonnance" in profile.champs_manquants
        assert "sphere_od" in profile.champs_manquants

    def test_consolidation_missing_devis(self, test_db, tenant_id, customer, case_obj, prescription, mutuelle):
        """Test consolidation when no devis exists."""
        profile = consolidate_client_for_pec(test_db, tenant_id, customer.id)

        assert profile.nom is not None
        assert profile.sphere_od is not None
        assert profile.montant_ttc is None
        assert "montant_ttc" in profile.champs_manquants

    def test_consolidation_missing_mutuelle(self, test_db, tenant_id, customer, case_obj, prescription, devis_obj):
        """Test consolidation when no mutuelle exists."""
        profile = consolidate_client_for_pec(test_db, tenant_id, customer.id, devis_obj.id)

        assert profile.mutuelle_nom is None
        assert "mutuelle_nom" in profile.champs_manquants

    def test_consolidation_minimal_data(self, test_db, tenant_id, customer):
        """Test consolidation with only customer data."""
        profile = consolidate_client_for_pec(test_db, tenant_id, customer.id)

        assert profile.nom is not None
        assert profile.prenom is not None
        assert profile.numero_secu is not None
        assert profile.sphere_od is None
        assert profile.montant_ttc is None
        assert profile.mutuelle_nom is None
        assert len(profile.champs_manquants) > 5

    def test_completude_score_full(self, test_db, tenant_id, customer, case_obj, prescription, devis_obj, mutuelle):
        """Test that completude score is high when all data is present."""
        profile = consolidate_client_for_pec(test_db, tenant_id, customer.id, devis_obj.id)
        assert profile.score_completude >= 80.0

    def test_completude_score_minimal(self, test_db, tenant_id, customer):
        """Test that completude score is low with minimal data."""
        profile = consolidate_client_for_pec(test_db, tenant_id, customer.id)
        assert profile.score_completude < 50.0

    def test_source_traceability(self, test_db, tenant_id, customer, case_obj, prescription, devis_obj, mutuelle):
        """Test that each field records its source."""
        profile = consolidate_client_for_pec(test_db, tenant_id, customer.id, devis_obj.id)

        # Cosium client source for identity
        assert profile.nom.source == "cosium_client"
        assert profile.nom.confidence == 1.0

        # Prescription source for optical
        assert "cosium_prescription" in profile.sphere_od.source

        # Devis source for financial
        assert "devis" in profile.montant_ttc.source


# ============================================================
# STEP 6: Incoherence detection tests
# ============================================================


class TestIncoherenceDetection:
    """Tests for the incoherence detector."""

    def _make_field(self, value, source="test", confidence=1.0):
        return ConsolidatedField(
            value=value, source=source, source_label="Test", confidence=confidence,
            last_updated=datetime.now(UTC),
        )

    def test_expired_ordonnance_3_years(self):
        """Ordonnance older than 3 years should be ERROR."""
        old_date = (date.today() - timedelta(days=4*365)).strftime("%Y-%m-%d")
        profile = ConsolidatedClientProfile(
            date_ordonnance=self._make_field(old_date),
        )
        alerts = detect_optical_incoherences(profile)
        error_alerts = [a for a in alerts if a.severity == "error" and a.field == "date_ordonnance"]
        assert len(error_alerts) == 1
        assert "perimee" in error_alerts[0].message.lower()

    def test_expired_ordonnance_1_year(self):
        """Ordonnance older than 1 year but less than 3 should be WARNING."""
        old_date = (date.today() - timedelta(days=2*365)).strftime("%Y-%m-%d")
        profile = ConsolidatedClientProfile(
            date_ordonnance=self._make_field(old_date),
        )
        alerts = detect_optical_incoherences(profile)
        warning_alerts = [a for a in alerts if a.severity == "warning" and a.field == "date_ordonnance"]
        assert len(warning_alerts) == 1
        assert "expiree" in warning_alerts[0].message.lower()

    def test_recent_ordonnance_no_alert(self):
        """Recent ordonnance should not trigger alerts."""
        recent_date = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")
        profile = ConsolidatedClientProfile(
            date_ordonnance=self._make_field(recent_date),
        )
        alerts = detect_optical_incoherences(profile)
        assert len(alerts) == 0

    def test_addition_mismatch(self):
        """Large addition OD/OG difference should trigger warning."""
        profile = ConsolidatedClientProfile(
            addition_od=self._make_field(2.00),
            addition_og=self._make_field(3.00),
        )
        alerts = detect_optical_incoherences(profile)
        assert any(a.field == "addition" for a in alerts)

    def test_financial_secu_plus_mutuelle_exceeds_ttc(self):
        """Part secu + part mutuelle > montant TTC should be ERROR."""
        profile = ConsolidatedClientProfile(
            montant_ttc=self._make_field(500.0),
            part_secu=self._make_field(300.0),
            part_mutuelle=self._make_field(300.0),
        )
        alerts = detect_financial_incoherences(profile)
        error_alerts = [a for a in alerts if a.severity == "error" and a.field == "financial"]
        assert len(error_alerts) == 1
        assert "depasse" in error_alerts[0].message.lower()

    def test_financial_negative_rac(self):
        """Negative reste a charge should be ERROR."""
        profile = ConsolidatedClientProfile(
            reste_a_charge=self._make_field(-50.0),
        )
        alerts = detect_financial_incoherences(profile)
        error_alerts = [a for a in alerts if a.severity == "error" and a.field == "reste_a_charge"]
        assert len(error_alerts) == 1

    def test_financial_mutuelle_without_name(self):
        """Part mutuelle > 0 but no mutuelle name should be WARNING."""
        profile = ConsolidatedClientProfile(
            part_mutuelle=self._make_field(200.0),
        )
        alerts = detect_financial_incoherences(profile)
        warning_alerts = [a for a in alerts if a.severity == "warning" and a.field == "mutuelle_nom"]
        assert len(warning_alerts) == 1

    def test_expired_mutuelle_rights(self):
        """Expired mutuelle rights should be ERROR."""
        expired_date = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")
        profile = ConsolidatedClientProfile(
            date_fin_droits=self._make_field(expired_date),
        )
        alerts = detect_identity_incoherences(profile)
        error_alerts = [a for a in alerts if a.severity == "error" and a.field == "date_fin_droits"]
        assert len(error_alerts) == 1
        assert "expires" in error_alerts[0].message.lower()

    def test_missing_secu_number(self):
        """Missing numero secu should be ERROR."""
        profile = ConsolidatedClientProfile()
        alerts = detect_missing_data(profile)
        assert any(a.field == "numero_secu" and a.severity == "error" for a in alerts)

    def test_missing_ordonnance(self):
        """Missing ordonnance should be ERROR."""
        profile = ConsolidatedClientProfile()
        alerts = detect_missing_data(profile)
        assert any(a.field == "date_ordonnance" and a.severity == "error" for a in alerts)

    def test_missing_devis(self):
        """Missing devis/montant should be ERROR."""
        profile = ConsolidatedClientProfile()
        alerts = detect_missing_data(profile)
        assert any(a.field == "montant_ttc" and a.severity == "error" for a in alerts)

    def test_missing_mutuelle_warning(self):
        """Missing mutuelle should be WARNING (not blocking)."""
        profile = ConsolidatedClientProfile()
        alerts = detect_missing_data(profile)
        mut_alerts = [a for a in alerts if a.field == "mutuelle_nom"]
        assert len(mut_alerts) == 1
        assert mut_alerts[0].severity == "warning"

    def test_full_detect_sorts_by_severity(self):
        """The full detect function should sort errors before warnings."""
        profile = ConsolidatedClientProfile(
            reste_a_charge=self._make_field(-10.0),  # error
        )
        alerts = detect_incoherences(profile)
        severities = [a.severity for a in alerts]
        # All errors should come before warnings
        seen_warning = False
        for s in severities:
            if s == "warning":
                seen_warning = True
            if s == "error" and seen_warning:
                pytest.fail("Error found after warning — sort is wrong")

    def test_valid_profile_no_blocking_errors(self):
        """A fully valid profile should have no blocking errors (may have warnings)."""
        recent = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")
        profile = ConsolidatedClientProfile(
            nom=self._make_field("DUPONT"),
            prenom=self._make_field("Jean"),
            numero_secu=self._make_field("1850375123456"),
            mutuelle_nom=self._make_field("HARMONIE"),
            mutuelle_numero_adherent=self._make_field("HM-123"),
            date_ordonnance=self._make_field(recent),
            sphere_od=self._make_field(2.50),
            sphere_og=self._make_field(3.00),
            montant_ttc=self._make_field(720.0),
            part_secu=self._make_field(100.0),
            part_mutuelle=self._make_field(400.0),
            reste_a_charge=self._make_field(220.0),
        )
        alerts = detect_incoherences(profile)
        errors = [a for a in alerts if a.severity == "error"]
        assert len(errors) == 0


# ============================================================
# STEP 7 & 8: PEC Preparation tests
# ============================================================


class TestPecPreparation:
    """Tests for PEC preparation service."""

    def test_create_preparation(self, test_db, tenant_id, user_id, customer, case_obj, prescription, devis_obj, mutuelle):
        """Test creating a PEC preparation with full data."""
        result = pec_preparation_service.prepare_pec(
            test_db, tenant_id, customer.id, devis_obj.id, user_id,
        )
        assert result.id > 0
        assert result.customer_id == customer.id
        assert result.devis_id == devis_obj.id
        assert result.completude_score > 0
        assert result.consolidated_data is not None
        assert result.status in ("en_preparation", "prete")

    def test_create_preparation_minimal(self, test_db, tenant_id, user_id, customer):
        """Test creating a PEC preparation with minimal data."""
        result = pec_preparation_service.prepare_pec(
            test_db, tenant_id, customer.id, user_id=user_id,
        )
        assert result.id > 0
        assert result.errors_count > 0
        assert result.status == "en_preparation"

    def test_get_preparation(self, test_db, tenant_id, user_id, customer, case_obj, prescription, devis_obj, mutuelle):
        """Test getting a PEC preparation by ID."""
        created = pec_preparation_service.prepare_pec(
            test_db, tenant_id, customer.id, devis_obj.id, user_id,
        )
        fetched = pec_preparation_service.get_preparation(test_db, tenant_id, created.id)
        assert fetched.id == created.id
        assert fetched.customer_id == customer.id

    def test_list_preparations(self, test_db, tenant_id, user_id, customer, case_obj, prescription, devis_obj, mutuelle):
        """Test listing PEC preparations for a customer."""
        pec_preparation_service.prepare_pec(test_db, tenant_id, customer.id, devis_obj.id, user_id)
        pec_preparation_service.prepare_pec(test_db, tenant_id, customer.id, user_id=user_id)

        results = pec_preparation_service.list_preparations_for_customer(
            test_db, tenant_id, customer.id,
        )
        assert len(results) == 2

    def test_validate_field(self, test_db, tenant_id, user_id, customer, case_obj, prescription, devis_obj, mutuelle):
        """Test validating a field in a preparation."""
        prep = pec_preparation_service.prepare_pec(
            test_db, tenant_id, customer.id, devis_obj.id, user_id,
        )
        result = pec_preparation_service.validate_field(
            test_db, tenant_id, prep.id, "nom", user_id,
        )
        assert result.user_validations is not None
        assert "nom" in result.user_validations

    def test_correct_field(self, test_db, tenant_id, user_id, customer, case_obj, prescription, devis_obj, mutuelle):
        """Test correcting a field value and recalculating alerts."""
        prep = pec_preparation_service.prepare_pec(
            test_db, tenant_id, customer.id, devis_obj.id, user_id,
        )
        result = pec_preparation_service.correct_field(
            test_db, tenant_id, prep.id, "numero_secu", "2850375999999", user_id,
        )
        assert result.user_corrections is not None
        corrections = result.user_corrections
        assert "numero_secu" in corrections
        assert corrections["numero_secu"]["corrected"] == "2850375999999"

    def test_refresh_preparation(self, test_db, tenant_id, user_id, customer, case_obj, prescription, devis_obj, mutuelle):
        """Test refreshing a preparation re-runs consolidation."""
        prep = pec_preparation_service.prepare_pec(
            test_db, tenant_id, customer.id, devis_obj.id, user_id,
        )
        refreshed = pec_preparation_service.refresh_preparation(
            test_db, tenant_id, prep.id,
        )
        assert refreshed.id == prep.id
        assert refreshed.consolidated_data is not None

    def test_submit_preparation_creates_pec(self, test_db, tenant_id, user_id, customer, case_obj, prescription, devis_obj, mutuelle):
        """Test that submitting a ready preparation creates a PEC request."""
        prep = pec_preparation_service.prepare_pec(
            test_db, tenant_id, customer.id, devis_obj.id, user_id,
        )
        # If the prep has errors, correct them to make it ready
        if prep.status != "prete":
            # Force status to prete for testing
            from app.repositories import pec_preparation_repo
            db_prep = pec_preparation_repo.get_by_id(test_db, prep.id, tenant_id)
            pec_preparation_repo.update(test_db, db_prep, status="prete")
            prep = pec_preparation_service.get_preparation(test_db, tenant_id, prep.id)

        # Attach required documents for submission
        pec_preparation_service.add_document(
            test_db, tenant_id, prep.id, document_role="ordonnance",
        )
        pec_preparation_service.add_document(
            test_db, tenant_id, prep.id, document_role="devis",
        )

        result = pec_preparation_service.create_pec_from_preparation(
            test_db, tenant_id, prep.id, user_id,
        )
        assert result["pec_request_id"] > 0
        assert result["status"] == "soumise"

    def test_submit_not_ready_fails(self, test_db, tenant_id, user_id, customer):
        """Test that submitting a non-ready preparation raises an error."""
        prep = pec_preparation_service.prepare_pec(
            test_db, tenant_id, customer.id, user_id=user_id,
        )
        # Should be en_preparation since minimal data
        assert prep.status == "en_preparation"

        from app.core.exceptions import BusinessError
        with pytest.raises(BusinessError) as exc_info:
            pec_preparation_service.create_pec_from_preparation(
                test_db, tenant_id, prep.id, user_id,
            )
        assert "PREPARATION_NOT_READY" in str(exc_info.value)

    def test_add_and_list_documents(self, test_db, tenant_id, user_id, customer, case_obj, prescription, devis_obj, mutuelle):
        """Test attaching and listing documents."""
        prep = pec_preparation_service.prepare_pec(
            test_db, tenant_id, customer.id, devis_obj.id, user_id,
        )

        doc = pec_preparation_service.add_document(
            test_db, tenant_id, prep.id,
            cosium_document_id=5001,
            document_role="ordonnance",
        )
        assert doc.preparation_id == prep.id
        assert doc.document_role == "ordonnance"

        docs = pec_preparation_service.list_documents(test_db, tenant_id, prep.id)
        assert len(docs) == 1
        assert docs[0].cosium_document_id == 5001

    def test_preparation_not_found(self, test_db, tenant_id):
        """Test that accessing a non-existent preparation raises NotFoundError."""
        from app.core.exceptions import NotFoundError
        with pytest.raises(NotFoundError):
            pec_preparation_service.get_preparation(test_db, tenant_id, 99999)

    def test_customer_not_found(self, test_db, tenant_id, user_id):
        """Test that preparing PEC for non-existent customer raises NotFoundError."""
        from app.core.exceptions import NotFoundError
        with pytest.raises(NotFoundError):
            pec_preparation_service.prepare_pec(test_db, tenant_id, 99999, user_id=user_id)

    def test_refresh_preserves_corrections(self, test_db, tenant_id, user_id, customer, case_obj, prescription, devis_obj, mutuelle):
        """Test that refreshing preserves user corrections."""
        prep = pec_preparation_service.prepare_pec(
            test_db, tenant_id, customer.id, devis_obj.id, user_id,
        )
        # Make a correction
        pec_preparation_service.correct_field(
            test_db, tenant_id, prep.id, "numero_secu", "NEW_VALUE", user_id,
        )
        # Refresh
        refreshed = pec_preparation_service.refresh_preparation(
            test_db, tenant_id, prep.id,
        )
        # The correction should still be applied
        data = refreshed.consolidated_data
        assert data is not None
        assert data.get("numero_secu", {}).get("value") == "NEW_VALUE"
        assert data.get("numero_secu", {}).get("source") == "manual"
