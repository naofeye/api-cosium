"""Integration tests for the full PEC flow using real OCR extraction data.

Validates that consolidation merges data from ALL sources (Cosium, OCR, devis),
incoherence detection works, and PEC preparation auto-attaches documents.
"""

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
from app.services.incoherence_detector import detect_incoherences
from app.services import pec_preparation_service


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
    user = User(
        email="test@optiflow.local",
        password_hash=hash_password("test123"),
        role="admin",
        is_active=True,
    )
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
        first_name="Marie",
        last_name="LAMBERT",
        birth_date=date(1978, 6, 22),
        social_security_number="2780622123456",
        email="marie.lambert@test.fr",
        phone="0607080910",
    )
    test_db.add(c)
    test_db.commit()
    test_db.refresh(c)
    return c


@pytest.fixture(name="case_obj")
def case_fixture(test_db, tenant_id, customer):
    case = Case(
        tenant_id=tenant_id,
        customer_id=customer.id,
        status="en_cours",
        source="cosium",
    )
    test_db.add(case)
    test_db.commit()
    test_db.refresh(case)
    return case


@pytest.fixture(name="prescription")
def prescription_fixture(test_db, tenant_id, customer):
    recent_date = (date.today() - timedelta(days=45)).strftime("%d/%m/%Y")
    p = CosiumPrescription(
        tenant_id=tenant_id,
        cosium_id=2001,
        customer_id=customer.id,
        prescription_date=recent_date,
        file_date=datetime.now(UTC) - timedelta(days=45),
        sphere_right=-1.50,
        cylinder_right=-0.50,
        axis_right=85,
        addition_right=1.75,
        sphere_left=-2.00,
        cylinder_left=-0.75,
        axis_left=95,
        addition_left=1.75,
        prescriber_name="Dr Lefebvre",
    )
    test_db.add(p)
    test_db.commit()
    test_db.refresh(p)
    return p


@pytest.fixture(name="ocr_ordonnance")
def ocr_ordonnance_fixture(test_db, tenant_id, case_obj):
    """Simulate an OCR-extracted ordonnance document."""
    doc = Document(
        tenant_id=tenant_id,
        case_id=case_obj.id,
        type="ordonnance",
        filename="ordonnance_scan.pdf",
        storage_key="docs/ordonnance_scan.pdf",
    )
    test_db.add(doc)
    test_db.flush()

    structured = {
        "prescripteur": "Dr Lefebvre",
        "date_ordonnance": (date.today() - timedelta(days=45)).strftime("%Y-%m-%d"),
        "sphere_od": -1.50,
        "cylinder_od": -0.50,
        "axis_od": 85,
        "addition_od": 1.75,
        "sphere_og": -2.00,
        "cylinder_og": -0.75,
        "axis_og": 95,
        "addition_og": 1.75,
        "ecart_pupillaire": 63.5,
    }
    extraction = DocumentExtraction(
        tenant_id=tenant_id,
        document_id=doc.id,
        document_type="ordonnance",
        extraction_method="tesseract_gpt4",
        ocr_confidence=0.92,
        structured_data=json.dumps(structured),
        raw_text="Dr Lefebvre - Ordonnance optique...",
    )
    test_db.add(extraction)
    test_db.commit()
    test_db.refresh(extraction)
    return extraction


@pytest.fixture(name="ocr_attestation")
def ocr_attestation_fixture(test_db, tenant_id, case_obj):
    """Simulate an OCR-extracted attestation mutuelle document."""
    doc = Document(
        tenant_id=tenant_id,
        case_id=case_obj.id,
        type="attestation_mutuelle",
        filename="attestation_harmonie.pdf",
        storage_key="docs/attestation_harmonie.pdf",
    )
    test_db.add(doc)
    test_db.flush()

    structured = {
        "mutuelle_nom": "HARMONIE MUTUELLE",
        "numero_adherent": "HM-789012",
        "code_organisme": "422",
        "numero_secu": "2780622123456",
        "date_debut_droits": "2025-01-01",
        "date_fin_droits": "2027-12-31",
    }
    extraction = DocumentExtraction(
        tenant_id=tenant_id,
        document_id=doc.id,
        document_type="attestation_mutuelle",
        extraction_method="tesseract_gpt4",
        ocr_confidence=0.88,
        structured_data=json.dumps(structured),
        raw_text="HARMONIE MUTUELLE - Attestation de droits...",
    )
    test_db.add(extraction)
    test_db.commit()
    test_db.refresh(extraction)
    return extraction


@pytest.fixture(name="ocr_devis")
def ocr_devis_fixture(test_db, tenant_id, case_obj):
    """Simulate an OCR-extracted devis document."""
    doc = Document(
        tenant_id=tenant_id,
        case_id=case_obj.id,
        type="devis",
        filename="devis_optique.pdf",
        storage_key="docs/devis_optique.pdf",
    )
    test_db.add(doc)
    test_db.flush()

    structured = {
        "montant_ttc": 850.00,
        "part_secu": 120.00,
        "part_mutuelle": 450.00,
        "reste_a_charge": 280.00,
    }
    extraction = DocumentExtraction(
        tenant_id=tenant_id,
        document_id=doc.id,
        document_type="devis",
        extraction_method="tesseract_gpt4",
        ocr_confidence=0.85,
        structured_data=json.dumps(structured),
        raw_text="Devis optique - Monture + Verres progressifs...",
    )
    test_db.add(extraction)
    test_db.commit()
    test_db.refresh(extraction)
    return extraction


# ============================================================
# Integration tests: full PEC flow with real OCR data
# ============================================================


class TestPecRealFlow:
    """Integration tests for the full PEC flow using OCR extraction data."""

    def test_consolidation_merges_all_sources(
        self, test_db, tenant_id, customer, case_obj, prescription,
        ocr_ordonnance, ocr_attestation, ocr_devis,
    ):
        """Consolidation merges Cosium client, Cosium prescription, and OCR extractions.

        Cosium data takes priority, but OCR fills gaps (ecart_pupillaire,
        mutuelle info, financial data from OCR devis).
        """
        profile = consolidate_client_for_pec(test_db, tenant_id, customer.id)

        # Identity from Cosium client
        assert profile.nom is not None
        assert profile.nom.value == "LAMBERT"
        assert profile.nom.source == "cosium_client"

        # Optical from Cosium prescription (higher priority than OCR)
        assert profile.sphere_od is not None
        assert profile.sphere_od.value == -1.50
        assert "cosium_prescription" in profile.sphere_od.source

        # Ecart pupillaire from OCR only (not available in Cosium prescription)
        assert profile.ecart_pupillaire is not None
        assert profile.ecart_pupillaire.value == 63.5
        assert "document_ocr" in profile.ecart_pupillaire.source

        # Mutuelle from OCR attestation
        assert profile.mutuelle_nom is not None
        assert profile.mutuelle_nom.value == "HARMONIE MUTUELLE"
        assert "document_ocr" in profile.mutuelle_nom.source

        assert profile.mutuelle_numero_adherent is not None
        assert profile.mutuelle_numero_adherent.value == "HM-789012"

        assert profile.mutuelle_code_organisme is not None
        assert profile.mutuelle_code_organisme.value == "422"

        assert profile.date_fin_droits is not None
        assert profile.date_fin_droits.value == "2027-12-31"

        # Financial from OCR devis (no OptiFlow devis created)
        assert profile.montant_ttc is not None
        assert profile.montant_ttc.value == 850.00
        assert "document_ocr" in profile.montant_ttc.source

        assert profile.part_secu is not None
        assert profile.part_secu.value == 120.00

        assert profile.part_mutuelle is not None
        assert profile.part_mutuelle.value == 450.00

        assert profile.reste_a_charge is not None
        assert profile.reste_a_charge.value == 280.00

        # All sources should be tracked
        assert len(profile.sources_utilisees) >= 3
        assert profile.score_completude >= 80.0

    def test_incoherence_detection_with_ocr_data(
        self, test_db, tenant_id, customer, case_obj, prescription,
        ocr_ordonnance, ocr_attestation, ocr_devis,
    ):
        """Incoherence detection generates appropriate alerts from OCR-sourced data."""
        profile = consolidate_client_for_pec(test_db, tenant_id, customer.id)
        alerts = detect_incoherences(profile)

        # With complete and consistent data, there should be no blocking errors
        errors = [a for a in alerts if a.severity == "error"]
        assert len(errors) == 0, f"Unexpected errors: {[e.message for e in errors]}"

        # There might be warnings (e.g. ordonnance > 1 year) but that's OK
        # Our ordonnance is 45 days old, so no warning expected there
        ordo_alerts = [a for a in alerts if a.field == "date_ordonnance"]
        assert len(ordo_alerts) == 0

    def test_pec_preparation_auto_attaches_documents(
        self, test_db, tenant_id, user_id, customer, case_obj, prescription,
        ocr_ordonnance, ocr_attestation, ocr_devis,
    ):
        """PEC preparation auto-attaches ordonnance, attestation, and devis documents."""
        result = pec_preparation_service.prepare_pec(
            test_db, tenant_id, customer.id, user_id=user_id,
        )

        # Verify the preparation was created
        assert result.id > 0
        assert result.customer_id == customer.id

        # Check auto-attached documents
        docs = pec_preparation_service.list_documents(test_db, tenant_id, result.id)
        assert len(docs) == 3

        roles = {d.document_role for d in docs}
        assert "ordonnance" in roles
        assert "attestation_mutuelle" in roles
        assert "devis" in roles

        # Each document should have an extraction_id
        for doc in docs:
            assert doc.extraction_id is not None

    def test_completude_reflects_ocr_data(
        self, test_db, tenant_id, user_id, customer, case_obj,
        ocr_ordonnance, ocr_attestation, ocr_devis,
    ):
        """Completude score reflects data availability from OCR even without Cosium prescription.

        With OCR ordonnance + attestation + devis + Cosium client identity,
        the score should be high.
        """
        # No Cosium prescription fixture used here
        profile = consolidate_client_for_pec(test_db, tenant_id, customer.id)

        # Identity from Cosium client
        assert profile.nom is not None
        assert profile.prenom is not None
        assert profile.numero_secu is not None

        # Optical from OCR (filling the gap left by absent Cosium prescription)
        assert profile.sphere_od is not None
        assert profile.sphere_og is not None
        assert profile.date_ordonnance is not None

        # Financial from OCR devis
        assert profile.montant_ttc is not None

        # Mutuelle from OCR attestation
        assert profile.mutuelle_nom is not None
        assert profile.mutuelle_numero_adherent is not None

        # Score should be high (all required fields filled)
        assert profile.score_completude >= 80.0
        assert len(profile.champs_manquants) <= 2

    def test_full_pec_flow_end_to_end(
        self, test_db, tenant_id, user_id, customer, case_obj, prescription,
        ocr_ordonnance, ocr_attestation, ocr_devis,
    ):
        """Full end-to-end PEC flow: consolidate -> detect -> prepare -> submit.

        1. Create PEC preparation with auto-attached documents
        2. Verify completude is high
        3. Submit if ready (or verify it could be submitted)
        """
        # Step 1: Create PEC preparation
        prep = pec_preparation_service.prepare_pec(
            test_db, tenant_id, customer.id, user_id=user_id,
        )
        assert prep.id > 0
        assert prep.completude_score >= 80.0

        # Step 2: Verify consolidated data is complete
        assert prep.consolidated_data is not None
        profile_data = prep.consolidated_data
        assert profile_data.get("nom") is not None
        assert profile_data.get("mutuelle_nom") is not None
        assert profile_data.get("montant_ttc") is not None

        # Step 3: Verify documents are attached
        docs = pec_preparation_service.list_documents(test_db, tenant_id, prep.id)
        assert len(docs) == 3

        # Step 4: If status is "prete", we can submit
        if prep.status == "prete":
            result = pec_preparation_service.create_pec_from_preparation(
                test_db, tenant_id, prep.id, user_id,
            )
            assert result["pec_request_id"] > 0
            assert result["status"] == "soumise"
        else:
            # Force status to prete and submit
            from app.repositories import pec_preparation_repo
            db_prep = pec_preparation_repo.get_by_id(test_db, prep.id, tenant_id)
            pec_preparation_repo.update(test_db, db_prep, status="prete")

            result = pec_preparation_service.create_pec_from_preparation(
                test_db, tenant_id, prep.id, user_id,
            )
            assert result["pec_request_id"] > 0
            assert result["status"] == "soumise"
