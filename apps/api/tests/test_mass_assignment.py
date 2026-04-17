"""Tests mass-assignment whitelist sur onboarding_repo."""

from app.repositories import onboarding_repo


class TestOrgMassAssignment:
    def test_rejects_unknown_field(self, db):
        org = onboarding_repo.create_organization(
            db,
            name="Test",
            slug="test-mass",
            contact_email="a@b.c",
            plan="trial",
            # Champ inconnu : doit etre ignore, pas AttributeError
            is_god_mode=True,  # type: ignore[arg-type]
        )
        assert not hasattr(org, "is_god_mode")
        assert org.name == "Test"


class TestUserMassAssignment:
    def test_does_not_allow_totp_fields_via_create(self, db):
        user = onboarding_repo.create_user(
            db,
            email="mass@test.com",
            password_hash="hash",
            role="admin",
            is_active=True,
            # Tentative injection :
            totp_enabled=True,  # type: ignore[arg-type]
            totp_secret_enc="SECRET",  # type: ignore[arg-type]
        )
        # Whitelist bloque -> defaults du modele appliques
        assert user.totp_enabled is False
        assert user.totp_secret_enc is None

    def test_keeps_whitelisted_fields(self, db):
        user = onboarding_repo.create_user(
            db,
            email="whitelist@test.com",
            password_hash="hash",
            role="manager",
            is_active=False,
        )
        assert user.email == "whitelist@test.com"
        assert user.role == "manager"
        assert user.is_active is False


class TestTenantMassAssignment:
    def test_rejects_require_admin_mfa_via_create(self, db):
        """`require_admin_mfa` ne doit etre togglable que via endpoint admin dedie."""
        # Creer une org minimale
        org = onboarding_repo.create_organization(
            db, name="Org", slug="mfa-test-org", contact_email="x@y.z", plan="trial",
        )
        tenant = onboarding_repo.create_tenant(
            db,
            organization_id=org.id,
            name="Mag",
            slug="mfa-test-mag",
            # Tentative injection
            require_admin_mfa=True,  # type: ignore[arg-type]
        )
        assert tenant.require_admin_mfa is False
