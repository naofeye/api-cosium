from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.rate_limiter import _global_attempts
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import DocumentType, Organization, ReminderTemplate, Tenant, TenantUser, User
from app.security import hash_password
from app.seed import DOCUMENT_TYPES


@pytest.fixture(autouse=True)
def _mock_storage(monkeypatch):
    """Mock methodes S3/MinIO : MinIO n'est pas disponible en CI (seul postgres est service).

    Patch les methodes de l'instance singleton pour couvrir les modules qui
    importent `from app.integrations.storage import storage` (binding deja fige).
    """
    from app.integrations.storage import storage as storage_instance

    monkeypatch.setattr(storage_instance, "upload_file", MagicMock(return_value="mocked-key"))
    monkeypatch.setattr(storage_instance, "get_download_url", MagicMock(return_value="http://mocked-url/download"))
    monkeypatch.setattr(storage_instance, "download_file", MagicMock(return_value=b"mocked content"))
    monkeypatch.setattr(storage_instance, "delete_file", MagicMock(return_value=None))
    monkeypatch.setattr(storage_instance, "ensure_bucket", MagicMock(return_value=None))


@pytest.fixture(autouse=True)
def _mock_celery_delay(monkeypatch):
    """Mock Celery `.delay()` : Redis/kombu n'est pas dispo en CI.

    Toute `task.delay(...)` essaie de publier vers Redis broker -> kombu.OperationalError.
    Remplace la methode `.delay` sur chaque task Celery utilisee par un MagicMock.
    """
    from app.tasks.email_tasks import send_email_async

    monkeypatch.setattr(send_email_async, "delay", MagicMock())


# Tests preexistants casses — CI rouge depuis 2026-04-12.
# Ces suites dependent de services externes absents en CI (Redis, creds Cosium)
# ou sont desynchronisees avec le code (services refactores, schemas modifies).
# Skip explicite avec raison claire + tracking dans TODO.md P1 section "Tests preexistants".
# Chaque ligne = `nodeid` pytest (chemin::classe::methode ou chemin::methode).
_PREEXISTING_BROKEN_TESTS: dict[str, str] = {
    # test_batch_operations : FIX (patches passent de batch_operation_service a batch_processing_service)
    # test_restore_clears_deleted_at : FIX (check deleted_at en BDD au lieu de ClientResponse)
    # test_cookies_have_samesite_lax : FIX (renomme en test_cookies_have_samesite_strict)
    # test_cosium.* : FIX (creds Cosium fake seeds dans db_fixture du conftest)
    # test_cosium_document_sync.py::test_sync_customer_documents_handles_download_error : FIX (service attrape Exception generale)
    # test_cosium_sync_extended : FIX (tests updated pour mocker les services actuels, pas _get_connector_for_tenant)
    # Upload document : FIX (mock storage dans _mock_storage autouse fixture)
    # test_forgot_password : FIX (mock send_email_async.delay dans _mock_celery_delay autouse)
    # test_health.* : FIX (tests utilisent auth_headers + renomme _admin_requires_auth)
    # test_monthly_report_invalid_month : FIX (accepte 400 OU 422)
    # test_ocam_operators.* : FIX (schema specific_rules: list -> dict[str, Any])
    # test_pdfplumber_exception_handled : FIX (ocr_service catch Exception generale)
    # test_connect_cosium_failure : FIX (onboarding_service catch Exception generale)
    # test_pec_intelligence + test_pec_real_flow : FIX (re-exports pec_consolidation_service + pec_precontrol_service dans pec_preparation_service)
    # test_sync_integrity + test_sync_transactions : FIX (creds Cosium fake seeds dans db_fixture)
    # test_sync_all_returns_has_errors_on_partial_failure : FIX (test attend 207 Multi-Status, pattern REST valide pour erreurs partielles)
    # test_v12_e2e : FIX (re-exports pec_preparation_service)
}


def pytest_collection_modifyitems(config, items):
    """Skip les tests preexistants casses avec une raison claire."""
    for item in items:
        reason = _PREEXISTING_BROKEN_TESTS.get(item.nodeid)
        if reason:
            item.add_marker(pytest.mark.skip(reason=f"TODO fix: {reason}"))


@pytest.fixture(name="db")
def db_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = TestSession()
    # Seed default organization and tenant
    org = Organization(name="Test Org", slug="test-org", plan="solo")
    db.add(org)
    db.flush()
    tenant = Tenant(
        organization_id=org.id,
        name="Test Magasin",
        slug="test-magasin",
        erp_type="cosium",
        # Creds Cosium fake pour satisfaire _authenticate_connector dans les tests
        # qui mockent get_connector mais pas _authenticate_connector.
        cosium_tenant="test-tenant",
        cosium_login="test-login",
        cosium_password_enc="test-password-not-encrypted",
    )
    db.add(tenant)
    db.flush()
    # Seed document types for completeness tests
    for dt_data in DOCUMENT_TYPES:
        db.add(DocumentType(**dt_data))
    # Seed default reminder template
    db.add(ReminderTemplate(
        tenant_id=tenant.id,
        name="Relance client default", channel="email", payer_type="client",
        subject="Relance", body="Bonjour {{client_name}}, relance pour {{montant}} EUR.",
        is_default=True,
    ))
    db.commit()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(name="default_tenant")
def default_tenant_fixture(db):
    return db.query(Tenant).filter(Tenant.slug == "test-magasin").first()


@pytest.fixture(name="client")
def client_fixture(db):
    _global_attempts.clear()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    _global_attempts.clear()


@pytest.fixture(name="seed_user")
def seed_user_fixture(db):
    user = User(
        email="test@optiflow.com",
        password_hash=hash_password("test123"),
        role="admin",
        is_active=True,
    )
    db.add(user)
    db.flush()
    # Assign user to default tenant
    tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
    tu = TenantUser(user_id=user.id, tenant_id=tenant.id, role="admin")
    db.add(tu)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(name="auth_headers")
def auth_headers_fixture(client, seed_user):
    # Note: In production, auth uses httpOnly cookies only.
    # In tests, we extract the token from cookies and use Authorization header
    # because TestClient cookie persistence can be unreliable across fixtures.
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "test@optiflow.com", "password": "test123"},
    )
    token = resp.cookies.get("optiflow_token")
    return {"Authorization": f"Bearer {token}"}
