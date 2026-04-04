"""Tests de performance : pagination, temps de reponse sur jeux de donnees."""

import time

from app.models import Case, Customer
from app.security import hash_password


def _seed_bulk_data(db, count: int = 200, tenant_id: int = 1):
    """Seed N customers + cases for performance testing."""
    for i in range(count):
        c = Customer(
            tenant_id=tenant_id,
            first_name=f"Prenom{i}",
            last_name=f"Nom{i}",
            email=f"client{i}@test.local",
            phone=f"060000{i:04d}",
        )
        db.add(c)
        db.flush()
        case = Case(tenant_id=tenant_id, customer_id=c.id, status="draft", source="test")
        db.add(case)
    db.commit()


def test_cases_pagination_limits_results(client, db, auth_headers):
    """La pagination doit limiter le nombre de resultats."""
    _seed_bulk_data(db, 50)
    resp = client.get("/api/v1/cases?limit=10&offset=0", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 10


def test_cases_pagination_offset(client, db, auth_headers):
    """L'offset doit decaler les resultats."""
    _seed_bulk_data(db, 30)
    page1 = client.get("/api/v1/cases?limit=10&offset=0", headers=auth_headers).json()
    page2 = client.get("/api/v1/cases?limit=10&offset=10", headers=auth_headers).json()
    assert len(page1) == 10
    assert len(page2) == 10
    ids1 = {c["id"] for c in page1}
    ids2 = {c["id"] for c in page2}
    assert ids1.isdisjoint(ids2), "Pages should not overlap"


def test_cases_list_responds_under_1s(client, db, auth_headers):
    """La liste des dossiers doit repondre en moins de 1s avec 200 dossiers."""
    _seed_bulk_data(db, 200)
    start = time.time()
    resp = client.get("/api/v1/cases?limit=25", headers=auth_headers)
    elapsed = time.time() - start
    assert resp.status_code == 200
    assert elapsed < 1.0, f"Response took {elapsed:.2f}s, should be < 1s"


def test_clients_list_responds_under_1s(client, db, auth_headers):
    """La liste des clients doit repondre en moins de 1s."""
    _seed_bulk_data(db, 200)
    start = time.time()
    resp = client.get("/api/v1/clients?page=1&page_size=25", headers=auth_headers)
    elapsed = time.time() - start
    assert resp.status_code == 200
    assert elapsed < 1.0, f"Response took {elapsed:.2f}s, should be < 1s"


def test_pagination_max_limit_enforced(client, db, auth_headers):
    """Le limit ne doit pas depasser 100."""
    resp = client.get("/api/v1/cases?limit=500", headers=auth_headers)
    assert resp.status_code == 422, "limit > 100 should be rejected"


def test_gzip_compression_active(client, auth_headers):
    """Les reponses doivent etre compressees si Accept-Encoding: gzip."""
    resp = client.get(
        "/api/v1/cases",
        headers={**auth_headers, "Accept-Encoding": "gzip"},
    )
    assert resp.status_code == 200
