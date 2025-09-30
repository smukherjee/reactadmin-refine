import os
import time
from fastapi.testclient import TestClient
from backend.main import app


def test_security_headers_present():
    client = TestClient(app)
    res = client.get("/api/v1/info")
    assert res.status_code == 200
    # security headers should be present
    assert "X-Frame-Options" in res.headers
    assert "Content-Security-Policy" in res.headers
    assert "Strict-Transport-Security" in res.headers


def test_rate_limit_exceeded(monkeypatch):
    # configure small rate limit window for test
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "3")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "2")
    # reload centralized settings so middleware picks up the new env vars
    from backend.app.core.config import reload_settings
    reload_settings()

    import uuid

    client = TestClient(app)

    # use a unique identifier for this test to avoid shared in-memory counters
    unique_ip = f"test-{uuid.uuid4()}"

    # send 4 requests quickly - the fourth should be rate limited
    for i in range(3):
        r = client.get("/api/v1/info", headers={"x-forwarded-for": unique_ip})
        assert r.status_code == 200

    r = client.get("/api/v1/info", headers={"x-forwarded-for": unique_ip})
    assert r.status_code == 429
    assert r.json().get("detail") == "Rate limit exceeded."

    # wait for window to expire then a request should succeed
    time.sleep(2)
    r2 = client.get("/api/v1/info", headers={"x-forwarded-for": unique_ip})
    assert r2.status_code == 200
