def test_login_ok(client, seed_user):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "test@optiflow.com", "password": "test123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "admin"
    # Tokens are now in httpOnly cookies, not in body
    assert "optiflow_token" in resp.cookies
    assert "optiflow_refresh" in resp.cookies


def test_login_bad_email(client, seed_user):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@test.com", "password": "test123"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "AUTHENTICATION_ERROR"


def test_login_bad_password(client, seed_user):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "test@optiflow.com", "password": "wrong"},
    )
    assert resp.status_code == 401


def test_refresh_token(client, seed_user):
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "test@optiflow.com", "password": "test123"},
    )
    # Refresh token is in httpOnly cookie; TestClient forwards cookies automatically
    resp = client.post("/api/v1/auth/refresh")
    assert resp.status_code == 204
    # New cookies should be set
    assert "optiflow_token" in resp.cookies


def test_logout(client, seed_user):
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "test@optiflow.com", "password": "test123"},
    )
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 204

    # Refresh after logout should fail
    resp = client.post("/api/v1/auth/refresh")
    assert resp.status_code == 401


def test_access_without_token(client):
    resp = client.get("/api/v1/cases")
    assert resp.status_code == 401
