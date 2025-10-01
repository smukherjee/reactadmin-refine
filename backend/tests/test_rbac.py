import uuid
from datetime import datetime, timedelta

from backend.app.cache import core as cache
from backend.app.crud import core as crud
from backend.app.models import core as models
from backend.app.schemas import core as schemas


def test_protected_endpoint_allowed_and_forbidden(db_session, client):
    r = client.post(
        "/api/v1/tenants", json={"name": "RBAC Corp", "domain": "rbac.local"}
    )
    assert r.status_code == 200
    tenant = r.json()

    ra = client.post(
        "/api/v1/users",
        json={
            "email": "alice.rbac@example.com",
            "password": "pass1234",
            "tenant_id": tenant["id"],
            "first_name": "Alice",
            "last_name": "RBAC",
        },
    )
    assert ra.status_code == 200
    alice = ra.json()

    rb = client.post(
        "/api/v1/users",
        json={
            "email": "bob.rbac@example.com",
            "password": "pass1234",
            "tenant_id": tenant["id"],
            "first_name": "Bob",
            "last_name": "RBAC",
        },
    )
    assert rb.status_code == 200
    bob = rb.json()

    la = client.post(
        "/api/v1/auth/login",
        params={
            "email": "alice.rbac@example.com",
            "password": "pass1234",
            "tenant_id": tenant["id"],
        },
    )
    assert la.status_code == 200
    token = la.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    role_obj = schemas.RoleCreate(
        name="reader", permissions=["read:protected"], tenant_id=tenant["id"]
    )
    role_db = crud.create_role(db_session, role_obj)
    crud.assign_role_to_user(
        db_session, alice["id"], str(role_db.id), assigned_by=alice["id"]
    )
    db_session.commit()

    rprot = client.get("/api/v1/protected/resource", headers=headers)
    assert rprot.status_code == 200

    lb = client.post(
        "/api/v1/auth/login",
        params={
            "email": "bob.rbac@example.com",
            "password": "pass1234",
            "tenant_id": tenant["id"],
        },
    )
    assert lb.status_code == 200
    btoken = lb.json()["access_token"]
    bheaders = {"Authorization": f"Bearer {btoken}"}
    rprot2 = client.get("/api/v1/protected/resource", headers=bheaders)
    assert rprot2.status_code == 403


def test_permission_combination_and_expiry(db_session, client):
    r = client.post("/api/v1/tenants", json={"name": "RBAC2", "domain": "rbac2.local"})
    assert r.status_code == 200
    t = r.json()
    ru = client.post(
        "/api/v1/users",
        json={
            "email": "carol@example.com",
            "password": "pass1234",
            "tenant_id": t["id"],
            "first_name": "Carol",
            "last_name": "X",
        },
    )
    assert ru.status_code == 200
    carol = ru.json()
    role_obj = schemas.RoleCreate(
        name="combo", permissions=["read:protected", "roles:create"], tenant_id=t["id"]
    )
    role = crud.create_role(db_session, role_obj)
    crud.assign_role_to_user(
        db_session, carol["id"], str(role.id), assigned_by=carol["id"]
    )
    db_session.commit()
    perms = crud.get_user_permissions(db_session, carol["id"])
    assert "read:protected" in perms
    assert "roles:create" in perms
    la = client.post(
        "/api/v1/auth/login",
        params={
            "email": "carol@example.com",
            "password": "pass1234",
            "tenant_id": t["id"],
        },
    )
    assert la.status_code == 200
    headers = {"Authorization": f"Bearer {la.json()['access_token']}"}
    rprot = client.get("/api/v1/protected/resource", headers=headers)
    assert rprot.status_code == 200
    rb = client.post(
        "/api/v1/users",
        json={
            "email": "dave@example.com",
            "password": "pass1234",
            "tenant_id": t["id"],
            "first_name": "Dave",
            "last_name": "Y",
        },
    )
    assert rb.status_code == 200
    lb = client.post(
        "/api/v1/auth/login",
        params={
            "email": "dave@example.com",
            "password": "pass1234",
            "tenant_id": t["id"],
        },
    )
    assert lb.status_code == 200
    bheaders = {"Authorization": f"Bearer {lb.json()['access_token']}"}
    rprot2 = client.get("/api/v1/protected/resource", headers=bheaders)
    assert rprot2.status_code == 403


def test_role_expiry(db_session, client):
    r = client.post("/api/v1/tenants", json={"name": "RBAC3", "domain": "rbac3.local"})
    assert r.status_code == 200
    t = r.json()
    ru = client.post(
        "/api/v1/users",
        json={
            "email": "eve@example.com",
            "password": "pass1234",
            "tenant_id": t["id"],
            "first_name": "Eve",
            "last_name": "Z",
        },
    )
    assert ru.status_code == 200
    eve = ru.json()
    role_obj = schemas.RoleCreate(
        name="temp", permissions=["read:protected"], tenant_id=t["id"]
    )
    role = crud.create_role(db_session, role_obj)
    from datetime import timezone

    expired_ur = models.UserRole(
        user_id=uuid.UUID(eve["id"]),
        role_id=role.id,
        assigned_by=uuid.UUID(eve["id"]),
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add(expired_ur)
    db_session.commit()

    # Expired roles should not return permissions
    perms = crud.get_user_permissions(db_session, eve["id"])
    assert "read:protected" not in perms

    le = client.post(
        "/api/v1/auth/login",
        params={
            "email": "eve@example.com",
            "password": "pass1234",
            "tenant_id": t["id"],
        },
    )
    assert le.status_code == 200
    headers = {"Authorization": f"Bearer {le.json()['access_token']}"}
    rprot = client.get("/api/v1/protected/resource", headers=headers)
    assert rprot.status_code == 403


def test_multiple_roles_aggregation(db_session, client):
    r = client.post("/api/v1/tenants", json={"name": "RBAC4", "domain": "rbac4.local"})
    assert r.status_code == 200
    t = r.json()
    ru = client.post(
        "/api/v1/users",
        json={
            "email": "frank@example.com",
            "password": "pass1234",
            "tenant_id": t["id"],
            "first_name": "Frank",
            "last_name": "W",
        },
    )
    assert ru.status_code == 200
    frank = ru.json()
    role1 = crud.create_role(
        db_session,
        schemas.RoleCreate(
            name="reader", permissions=["read:protected"], tenant_id=t["id"]
        ),
    )
    role2 = crud.create_role(
        db_session,
        schemas.RoleCreate(
            name="creator", permissions=["roles:create"], tenant_id=t["id"]
        ),
    )
    crud.assign_role_to_user(
        db_session, frank["id"], str(role1.id), assigned_by=frank["id"]
    )
    crud.assign_role_to_user(
        db_session, frank["id"], str(role2.id), assigned_by=frank["id"]
    )
    db_session.commit()
    perms = crud.get_user_permissions(db_session, frank["id"])
    assert "read:protected" in perms and "roles:create" in perms
    lf = client.post(
        "/api/v1/auth/login",
        params={
            "email": "frank@example.com",
            "password": "pass1234",
            "tenant_id": t["id"],
        },
    )
    assert lf.status_code == 200
    headers = {"Authorization": f"Bearer {lf.json()['access_token']}"}
    rprot = client.get("/api/v1/protected/resource", headers=headers)
    assert rprot.status_code == 200


def test_permission_revocation(db_session, client):
    r = client.post("/api/v1/tenants", json={"name": "RBAC5", "domain": "rbac5.local"})
    assert r.status_code == 200
    t = r.json()
    ru = client.post(
        "/api/v1/users",
        json={
            "email": "gina@example.com",
            "password": "pass1234",
            "tenant_id": t["id"],
            "first_name": "Gina",
            "last_name": "V",
        },
    )
    assert ru.status_code == 200
    gina = ru.json()
    role = crud.create_role(
        db_session,
        schemas.RoleCreate(
            name="reader", permissions=["read:protected"], tenant_id=t["id"]
        ),
    )
    ur = crud.assign_role_to_user(
        db_session, gina["id"], str(role.id), assigned_by=gina["id"]
    )
    db_session.commit()
    perms = crud.get_user_permissions(db_session, gina["id"])
    assert "read:protected" in perms
    db_session.delete(ur)
    db_session.commit()
    # Manually invalidate cache since we're deleting directly via SQLAlchemy
    cache.invalidate_user_cache(t["id"], gina["id"])
    perms2 = crud.get_user_permissions(db_session, gina["id"])
    assert "read:protected" not in perms2
    lg = client.post(
        "/api/v1/auth/login",
        params={
            "email": "gina@example.com",
            "password": "pass1234",
            "tenant_id": t["id"],
        },
    )
    assert lg.status_code == 200
    headers = {"Authorization": f"Bearer {lg.json()['access_token']}"}
    rprot = client.get("/api/v1/protected/resource", headers=headers)
    assert rprot.status_code == 403


def test_forbidden_action(db_session, client):
    r = client.post("/api/v1/tenants", json={"name": "RBAC6", "domain": "rbac6.local"})
    assert r.status_code == 200
    t = r.json()
    ru = client.post(
        "/api/v1/users",
        json={
            "email": "harry@example.com",
            "password": "pass1234",
            "tenant_id": t["id"],
            "first_name": "Harry",
            "last_name": "U",
        },
    )
    assert ru.status_code == 200
    harry = ru.json()
    lh = client.post(
        "/api/v1/auth/login",
        params={
            "email": "harry@example.com",
            "password": "pass1234",
            "tenant_id": t["id"],
        },
    )
    assert lh.status_code == 200
    headers = {"Authorization": f"Bearer {lh.json()['access_token']}"}
    rprot = client.get("/api/v1/protected/resource", headers=headers)
    assert rprot.status_code == 403


def test_invalid_token(client):
    headers = {"Authorization": "Bearer invalid.token.value"}
    rprot = client.get("/api/v1/protected/resource", headers=headers)
    assert rprot.status_code == 401
