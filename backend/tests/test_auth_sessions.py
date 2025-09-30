import sys
import os
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from typing import Any, cast

# ensure repo root
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
import sys
import os
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

# ensure repo root
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from backend.main import app

client = TestClient(app)


def test_refresh_cookie_rotation_and_session_listing(db_session, client):
    # create tenant and user
    r = client.post('/api/v1/tenants', json={'name':'AuthTest','domain':'authtest.local'})
    assert r.status_code == 200
    t = r.json()

    ru = client.post('/api/v1/users', json={'email':'cookie@example.com','password':'pass1234','client_id': t['id'],'first_name':'C','last_name':'K'})
    assert ru.status_code == 200

    # login should set refresh_token cookie and session_id cookie
    login_resp = client.post('/api/v1/auth/login', params={'email':'cookie@example.com','password':'pass1234','client_id': t['id']})
    assert login_resp.status_code == 200
    assert 'refresh_token' in login_resp.cookies
    assert 'session_id' in login_resp.cookies
    session_id = login_resp.cookies.get('session_id')

    # call refresh endpoint to rotate tokens; TestClient will send cookies automatically
    refresh_resp = client.post('/api/v1/auth/refresh')
    assert refresh_resp.status_code == 200
    assert 'refresh_token' in refresh_resp.cookies
    assert 'session_id' in refresh_resp.cookies
    new_session_id = refresh_resp.cookies.get('session_id')
    assert new_session_id == session_id  # rotation keeps same session row but updates hashes

    # list sessions should show at least one session
    # need Authorization header using access token returned in refresh response body
    access_token = refresh_resp.json()['access_token']
    headers = {'Authorization': f'Bearer {access_token}'}
    ls = client.get('/api/v1/auth/sessions', headers=headers)
    assert ls.status_code == 200
    sessions = ls.json()
    assert isinstance(sessions, list)
    assert any(s['id'] == session_id for s in sessions)

    # logout the session
    lg = client.post('/api/v1/auth/logout', params={'session_id': session_id}, headers=headers)
    assert lg.status_code == 200
    # after logout, sessions list should be empty
    ls2 = client.get('/api/v1/auth/sessions', headers=headers)
    assert ls2.status_code == 200
    assert all(s['id'] != session_id for s in ls2.json())


def test_logout_all_revokes_all(db_session, client):
    r = client.post('/api/v1/tenants', json={'name':'AuthTest2','domain':'authtest2.local'})
    t = r.json()
    ru = client.post('/api/v1/users', json={'email':'multi@example.com','password':'pass1234','client_id': t['id'],'first_name':'M','last_name':'U'})
    assert ru.status_code == 200

    # login twice to create two sessions
    l1 = client.post('/api/v1/auth/login', params={'email':'multi@example.com','password':'pass1234','client_id': t['id']})
    assert l1.status_code == 200
    sess1 = l1.cookies.get('session_id')
    # perform another login in a new client to simulate second device
    other = TestClient(client.app)
    # copy dependency overrides so other client uses the in-memory DB
    cast(Any, other.app).dependency_overrides.update(cast(Any, client.app).dependency_overrides)
    l2 = other.post('/api/v1/auth/login', params={'email':'multi@example.com','password':'pass1234','client_id': t['id']})
    assert l2.status_code == 200
    sess2 = l2.cookies.get('session_id')
    assert sess1 != sess2

    # Logout-all from first client
    token = l1.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}
    r_logout_all = client.post('/api/v1/auth/logout-all', headers=headers)
    assert r_logout_all.status_code == 200

    # both clients should see no sessions
    ls1 = client.get('/api/v1/auth/sessions', headers=headers)
    assert ls1.status_code == 200
    assert ls1.json() == []
    token2 = l2.json()['access_token']
    headers2 = {'Authorization': f'Bearer {token2}'}
    ls2 = other.get('/api/v1/auth/sessions', headers=headers2)
    assert ls2.status_code == 200
    assert ls2.json() == []
