"""Tests that verify tenant isolation for session refresh and logout flows."""

from backend.app.cache import core as cache
from backend.app.crud import core as crud
from backend.app.schemas import core as schemas


def test_refresh_tenant_mismatch(db_session, client):
    # Create two tenants and a user in tenant A
    r1 = client.post("/api/v1/tenants", json={"name": "TenantA", "domain": "a.local"})
    assert r1.status_code == 200
    ta = r1.json()
    r2 = client.post("/api/v1/tenants", json={"name": "TenantB", "domain": "b.local"})
    assert r2.status_code == 200
    tb = r2.json()

    ru = client.post(
        "/api/v1/users",
        json={
            "email": "u1@example.com",
            "password": "pass1",
            "tenant_id": ta["id"],
            "first_name": "U",
            "last_name": "One",
        },
    )
    assert ru.status_code == 200
    u = ru.json()

    # Login to obtain refresh cookie (TestClient will receive cookies)
    L = client.post(
        "/api/v1/auth/login",
        params={"email": "u1@example.com", "password": "pass1", "tenant_id": ta["id"]},
    )
    assert L.status_code == 200

    # Replace tenant cookie with the other tenant
    client.cookies.set("tenant_id", tb["id"])

    # Attempt refresh should fail with 403 due to tenant mismatch
    R = client.post("/api/v1/auth/refresh")
    assert R.status_code == 403


def test_logout_tenant_mismatch(db_session, client):
    r1 = client.post("/api/v1/tenants", json={"name": "TenantX", "domain": "x.local"})
    assert r1.status_code == 200
    tx = r1.json()
    r2 = client.post("/api/v1/tenants", json={"name": "TenantY", "domain": "y.local"})
    assert r2.status_code == 200
    ty = r2.json()

    ru = client.post(
        "/api/v1/users",
        json={
            "email": "lx@example.com",
            "password": "pass1",
            "tenant_id": tx["id"],
            "first_name": "L",
            "last_name": "X",
        },
    )
    assert ru.status_code == 200
    u = ru.json()

    L = client.post(
        "/api/v1/auth/login",
        params={"email": "lx@example.com", "password": "pass1", "tenant_id": tx["id"]},
    )
    assert L.status_code == 200
    sess_id = client.cookies.get("session_id")

    # Authenticate as another tenant's user
    ru2 = client.post(
        "/api/v1/users",
        json={
            "email": "ly@example.com",
            "password": "pass2",
            "tenant_id": ty["id"],
            "first_name": "M",
            "last_name": "Y",
        },
    )
    assert ru2.status_code == 200
    # login as other tenant user to get current_user in context
    L2 = client.post(
        "/api/v1/auth/login",
        params={"email": "ly@example.com", "password": "pass2", "tenant_id": ty["id"]},
    )
    assert L2.status_code == 200

    # Attempt to logout the session from tenant X using tenant Y's auth -> should be 403
    token_y = L2.json().get("access_token")
    headers = {"Authorization": f"Bearer {token_y}"}
    resp = client.post(
        "/api/v1/auth/logout", params={"session_id": sess_id}, headers=headers
    )
    assert resp.status_code == 403
