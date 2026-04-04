import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.core.rate_limiter import _global_attempts
from app.models import DocumentType, Organization, ReminderTemplate, Tenant, TenantUser, User
from app.seed import DOCUMENT_TYPES
from app.security import hash_password


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
    tenant = Tenant(organization_id=org.id, name="Test Magasin", slug="test-magasin")
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
        email="test@optiflow.local",
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
        json={"email": "test@optiflow.local", "password": "test123"},
    )
    token = resp.cookies.get("optiflow_token")
    return {"Authorization": f"Bearer {token}"}
