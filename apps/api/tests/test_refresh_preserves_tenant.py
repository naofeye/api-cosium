"""Regression test for Codex audit M2 (2026-05-02).

`auth_service.refresh()` regenerait les tokens sur `tenants[0]` plutot que
sur le tenant courant choisi via `switch_tenant()`. Apres correction, le
refresh doit preserver le tenant lie au refresh token.
"""
from app.models import Organization, Tenant, TenantUser, User
from app.repositories import refresh_token_repo
from app.security import generate_refresh_token, get_refresh_token_expiry, hash_password
from app.services import auth_service


def _make_user_with_two_tenants(db):
    org = db.query(Organization).filter(Organization.slug == "test-org").first()
    user = User(
        email="multi@test.com",
        password_hash=hash_password("pwd"),
        role="admin",
        is_active=True,
    )
    db.add(user)
    db.flush()
    tenant_a = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
    tenant_b = Tenant(
        organization_id=org.id,
        name="Magasin B",
        slug="magasin-b",
        erp_type="cosium",
        cosium_tenant="t",
        cosium_login="l",
        cosium_password_enc="p",
    )
    db.add(tenant_b)
    db.flush()
    db.add(TenantUser(user_id=user.id, tenant_id=tenant_a.id, role="admin"))
    db.add(TenantUser(user_id=user.id, tenant_id=tenant_b.id, role="manager"))
    db.commit()
    return user, tenant_a, tenant_b


def test_refresh_preserves_tenant_id_from_token(db):
    user, tenant_a, tenant_b = _make_user_with_two_tenants(db)

    # On simule un refresh token emis pour le tenant B (le user a "switch" vers B).
    raw_token = generate_refresh_token()
    refresh_token_repo.create(
        db,
        raw_token,
        user.id,
        get_refresh_token_expiry(),
        tenant_id=tenant_b.id,
    )
    db.commit()

    result = auth_service.refresh(db, raw_token)

    # Le nouveau token doit pointer sur tenant_b, pas tenant_a (premier dans la liste).
    assert result.tenant_id == tenant_b.id, (
        f"Refresh devrait preserver tenant_b ({tenant_b.id}), "
        f"got {result.tenant_id}"
    )
    assert result.role == "manager"


def test_refresh_falls_back_when_tenant_id_is_null(db):
    """Tokens emis avant la migration (NULL tenant_id) tombent sur tenants[0]."""
    user, tenant_a, _tenant_b = _make_user_with_two_tenants(db)

    raw_token = generate_refresh_token()
    refresh_token_repo.create(
        db,
        raw_token,
        user.id,
        get_refresh_token_expiry(),
        tenant_id=None,
    )
    db.commit()

    result = auth_service.refresh(db, raw_token)
    # Pas de tenant_id sur le token : retombe sur tenants[0] (tenant_a).
    assert result.tenant_id == tenant_a.id


def test_refresh_falls_back_when_tenant_no_longer_accessible(db):
    """Si l'user perd l'acces au tenant initial, retombe sur tenants[0]."""
    user, tenant_a, tenant_b = _make_user_with_two_tenants(db)

    raw_token = generate_refresh_token()
    refresh_token_repo.create(
        db,
        raw_token,
        user.id,
        get_refresh_token_expiry(),
        tenant_id=tenant_b.id,
    )
    db.commit()

    # Revoque l'acces de l'user au tenant_b.
    tu_b = db.query(TenantUser).filter(
        TenantUser.user_id == user.id, TenantUser.tenant_id == tenant_b.id
    ).first()
    tu_b.is_active = False
    db.commit()

    result = auth_service.refresh(db, raw_token)
    # Tenant B inaccessible, fallback sur tenant_a (seul restant accessible).
    assert result.tenant_id == tenant_a.id
