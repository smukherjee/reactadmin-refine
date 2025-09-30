from fastapi.testclient import TestClient
from backend.app.main.core import app


def run() -> None:
    client = TestClient(app)

    r = client.post("/tenants", json={"name": "RBAC Corp", "domain": "rbac.local"})
    print('tenants', r.status_code, r.json())

    tenant = r.json()

    payload = {"email": "alice.rbac@example.com", "password": "pass1234", "client_id": tenant["id"], "first_name": "Alice"}
    ru = client.post("/users", json=payload)
    print('create user', ru.status_code)
    try:
        print(ru.json())
    except Exception as e:
        print('no json body', ru.text)


if __name__ == "__main__":
    run()
