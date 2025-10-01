#!/usr/bin/env python3
import requests

base_url = "http://localhost:8000"
tenant_id = "c802c2fe-f0e6-442d-bbd1-52581ee4c24a"
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyOGEwNDE5NC04ZDA0LTQyYmItOGNiMS01YTQ0Y2Y3NThjOTYiLCJlbWFpbCI6InN1cGVyYWRtaW5AZXhhbXBsZS5jb20iLCJjbGllbnRfaWQiOiJjODAyYzJmZS1mMGU2LTQ0MmQtYmJkMS01MjU4MWVlNGMyNGEiLCJleHAiOjE3NTkzNzM2NDUsImp0aSI6ImI4ZjYyY2UzLTMxNjYtNDQ3Ni1iNjliLTFkZDBhMDQ3ODQwNiJ9.h1sclDVIoWb-ufiVwvuAmzYpt698mUTze48qukfFgOQ"

headers = {"Authorization": f"Bearer {token}"}

# Create roles
roles = [
    {"name": "superadmin", "description": "Super administrator", "permissions": ["*"]},
    {"name": "clientadmin", "description": "Client administrator", "permissions": ["users:create", "roles:manage"]},
    {"name": "user", "description": "Regular user", "permissions": ["read:protected"]}
]

role_ids = {}
for role in roles:
    role_data = {**role, "tenant_id": tenant_id}
    resp = requests.post(f"{base_url}/api/v1/roles", json=role_data, headers=headers)
    if resp.status_code == 200:
        role_ids[role["name"]] = resp.json()["id"]
        print(f"Created role {role['name']}: {resp.json()['id']}")
    else:
        print(f"Failed to create role {role['name']}: {resp.text}")

# Assign superadmin role to superadmin user
user_id = "28a04194-8d04-42bb-8cb1-5a44cf758c96"
superadmin_role_id = role_ids["superadmin"]
assign_resp = requests.post(f"{base_url}/api/v1/users/{user_id}/roles", json={"role_id": superadmin_role_id}, headers=headers)
if assign_resp.status_code == 200:
    print("Assigned superadmin role to superadmin user")
else:
    print(f"Failed to assign role: {assign_resp.text}")

# Create other users
users = [
    {"email": "admin@example.com", "password": "admin123", "first_name": "Admin", "last_name": "User", "role": "clientadmin"},
    {"email": "user@example.com", "password": "user123", "first_name": "Regular", "last_name": "User", "role": "user"}
]

for user in users:
    user_data = {
        "email": user["email"],
        "password": user["password"],
        "tenant_id": tenant_id,
        "first_name": user["first_name"],
        "last_name": user["last_name"]
    }
    resp = requests.post(f"{base_url}/api/v1/users", json=user_data)
    if resp.status_code == 200:
        uid = resp.json()["id"]
        print(f"Created user {user['email']}: {uid}")
        # Assign role
        rid = role_ids[user["role"]]
        assign_resp = requests.post(f"{base_url}/api/v1/users/{uid}/roles", json={"role_id": rid}, headers=headers)
        if assign_resp.status_code == 200:
            print(f"Assigned {user['role']} role to {user['email']}")
        else:
            print(f"Failed to assign role to {user['email']}: {assign_resp.text}")
    else:
        print(f"Failed to create user {user['email']}: {resp.text}")

print("Done")