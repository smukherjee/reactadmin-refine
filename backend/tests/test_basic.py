import os
import sys

import pytest
from fastapi.testclient import TestClient

# Ensure repo root is on sys.path so we can import backend as a package
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from backend.main import app

client = TestClient(app)


def test_create_tenant_and_user():
    r = client.post(
        "/api/v1/tenants", json={"name": "Acme Corp", "domain": "acme.local"}
    )
    assert r.status_code == 200
    tenant = r.json()
    assert tenant["name"] == "Acme Corp"

    r2 = client.post(
        "/api/v1/users",
        json={
            "email": "alice@example.com",
            "password": "pass1234",
            "client_id": tenant["id"],
            "first_name": "Alice",
            "last_name": "Example",
        },
    )
    assert r2.status_code == 200
    user = r2.json()
    assert user["email"] == "alice@example.com"
