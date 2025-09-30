import os
import time
import json
import importlib
from fastapi.testclient import TestClient
from backend.main import app


def test_security_headers_present_on_key_endpoints():
    client = TestClient(app)
    endpoints = ["/", "/health", "/metrics", "/api/v1/info", "/cache/status"]
    for ep in endpoints:
        r = client.get(ep)
        # ensure responses are successful or handled
        assert r.status_code in (200, 404, 405)
        # security headers
        assert "X-Frame-Options" in r.headers
        assert "X-Content-Type-Options" in r.headers
        assert "Strict-Transport-Security" in r.headers
        assert "Content-Security-Policy" in r.headers


def test_refresh_cookie_flags_on_login():
    # login sets an HttpOnly refresh_token cookie; test that cookie flags are present
    client = TestClient(app)
    # use bogus credentials (should return 401) but TestClient still captures cookies if set
    r = client.post("/auth/login", data={"email": "nonexistent@example.com", "password": "bad", "client_id": "000"})
    # Expect 401 for invalid credentials (or 400/422 depending on validation) but ensure no 500
    assert r.status_code in (400, 401, 422)
    # If cookies present, ensure refresh_token is HttpOnly (server uses HttpOnly for refresh_token)
    cookies = r.cookies
    if "refresh_token" in cookies:
        # Note: TestClient returns cookie value but not flags; examine Set-Cookie header
        sc = r.headers.get("set-cookie", "")
        assert "refresh_token" in sc
        assert "httponly" in sc.lower()


def test_sql_injection_attempt_does_not_crash():
    client = TestClient(app)
    payload = {"email": "' OR '1'='1@example.com", "password": "x', ' OR '1'='1", "client_id": "000"}
    r = client.post("/auth/login", data=payload)
    # Application should not return 500 for crafted input; expect handled auth failure or validation error
    assert r.status_code != 500


def test_rate_limit_smoke():
    # basic smoke test: repeated requests should be handled (rate limiting may apply)
    client = TestClient(app)
    for i in range(5):
        r = client.get("/api/v1/info")
        assert r.status_code in (200, 429, 404, 405)


def test_auth_misconfiguration_and_broken_access_controls(db_session, client):
    # Create two tenants and users and ensure cross-tenant access is denied
    t1 = client.post('/api/v1/tenants', json={'name': 'TenantA', 'domain': 'a.local'}).json()
    t2 = client.post('/api/v1/tenants', json={'name': 'TenantB', 'domain': 'b.local'}).json()

    u1 = client.post('/api/v1/users', json={'email': 'usera@example.com', 'password': 'pass1234', 'client_id': t1['id'], 'first_name': 'A', 'last_name': 'One'})
    assert u1.status_code == 200
    u2 = client.post('/api/v1/users', json={'email': 'userb@example.com', 'password': 'pass1234', 'client_id': t2['id'], 'first_name': 'B', 'last_name': 'Two'})
    assert u2.status_code == 200

    # Login as user A and try to access tenant B's resources
    la = client.post('/api/v1/auth/login', params={'email': 'usera@example.com', 'password': 'pass1234', 'client_id': t1['id']})
    assert la.status_code == 200
    token = la.json().get('access_token')
    assert token
    headers = {'Authorization': f'Bearer {token}'}

    # Attempt to list users for tenant B using user A's token (should be 403 or empty)
    r = client.get(f"/api/v1/tenants/{t2['id']}/users", headers=headers)
    assert r.status_code in (200, 403, 404)
    if r.status_code == 200:
        # Ensure the returned list does not contain tenant B's internal-only data visible to other tenants
        users = r.json()
        assert all(u.get('client_id') != t2['id'] for u in users) or users == []


def test_insecure_deserialization_and_malformed_payloads(client):
    # Send payloads that could trigger unsafe deserialization if the app used pickle/unsafe eval
    # The app should reject or sanitize such payloads and not execute them.
    malicious_json = '{"__class__": "os.system", "cmd": "echo pwned"}'
    r = client.post('/api/v1/deserialize', data=malicious_json, headers={'Content-Type': 'application/json'})
    # endpoint may not exist; ensure we don't get 500. If implemented, should return 400/422
    assert r.status_code != 500


def test_jwt_and_token_hardening(client):
    # Create tenant and user and obtain JWT
    t = client.post('/api/v1/tenants', json={'name': 'JWTTest', 'domain': 'jwt.local'}).json()
    client.post('/users', json={'email': 'jwt@example.com', 'password': 'pass1234', 'client_id': t['id'], 'first_name': 'J', 'last_name': 'W'})
    l = client.post('/auth/login', params={'email': 'jwt@example.com', 'password': 'pass1234', 'client_id': t['id']})
    assert l.status_code == 200
    token = l.json().get('access_token')
    assert token
    # Modify token (tamper) and ensure server rejects it
    parts = token.split('.')
    if len(parts) == 3:
        tampered = parts[0] + '.' + parts[1] + '.tampered'
        r = client.get('/auth/sessions', headers={'Authorization': f'Bearer {tampered}'})
        assert r.status_code in (401, 403)


def test_basic_xss_reflection(client):
    # If any HTML endpoints exist, ensure reflected input is escaped
    r = client.get('/?q=<script>alert(1)</script>')
    assert r.status_code in (200, 404, 405)
    if 'text/html' in r.headers.get('content-type', ''):
        body = r.text.lower()
        assert '<script>' not in body
