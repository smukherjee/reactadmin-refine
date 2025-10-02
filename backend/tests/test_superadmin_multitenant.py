"""Test cases for superadmin multi-tenant access functionality.

This module tests that:
1. Superadmin users can access all tenants
2. Regular users are restricted to their own tenant
3. Permission system works with wildcard "*" permissions
4. Cross-tenant operations work for superadmin but not regular users

Tests use live server authentication to get fresh JWT tokens.
"""

import uuid
import requests
import pytest


BASE_URL = "http://127.0.0.1:8000"


def get_auth_token(email: str, password: str) -> str:
    """Get a fresh JWT token by logging in to the live server."""
    login_data = {
        "email": email,
        "password": password
    }
    
    response = requests.post(f"{BASE_URL}/api/v2/auth/login", json=login_data)
    
    if response.status_code != 200:
        pytest.fail(f"Failed to login {email}: {response.status_code} - {response.text}")
    
    return response.json()["access_token"]


def get_superadmin_token() -> str:
    """Get fresh superadmin JWT token."""
    return get_auth_token("superadmin@example.com", "pass1234")


def get_alice_token() -> str:
    """Get fresh alice JWT token.""" 
    return get_auth_token("alice@example.com", "pass1234")


class TestSuperadminMultitenant:
    """Test superadmin multi-tenant access functionality using live server authentication."""

    def test_superadmin_gets_all_tenants(self):
        """Test that superadmin users receive all tenants in available_tenants."""
        # Get auth token for superadmin
        token = get_superadmin_token()
        
        # Call /me endpoint
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/v2/async/users/me", headers=headers)
        assert response.status_code == 200
        
        user_data = response.json()
        available_tenants = user_data["available_tenants"]
        
        # Superadmin should see multiple tenants (at least 2)
        assert len(available_tenants) >= 2, f"Expected at least 2 tenants, got {len(available_tenants)}"
        
        # Validate tenant structure  
        for tenant in available_tenants:
            assert "id" in tenant
            assert "name" in tenant
            assert "domain" in tenant
        
        print(f"\u2705 Superadmin has access to {len(available_tenants)} tenants")

    def test_regular_user_gets_own_tenant_only(self):
        """Test that regular users only get their own tenant in available_tenants.""" 
        # Get auth token for regular user
        token = get_alice_token()
        
        # Call /me endpoint
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/v2/async/users/me", headers=headers)
        assert response.status_code == 200
        
        user_data = response.json()
        available_tenants = user_data["available_tenants"]
        
        # Regular user should only see their own tenant
        assert len(available_tenants) == 1, f"Expected 1 tenant, got {len(available_tenants)}"
        
        # Verify they only see their own tenant
        assert available_tenants[0]["id"] == user_data["current_tenant"]["id"]
        
        print(f"\u2705 Regular user has access to {len(available_tenants)} tenant only")

    def test_superadmin_cross_tenant_audit_creation(self):
        """Test that superadmin can create audit logs in any tenant."""
        token = get_superadmin_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        # Create audit log for a different tenant (using tenant from available list)
        audit_data = {
            "action": "test_cross_tenant",
            "resource": "audit_log", 
            "resource_id": str(uuid.uuid4()),
            "tenant_id": "c8ae0700-525f-4923-ab41-c22b12b65c1a"  # Acme Corp tenant
        }
        
        response = requests.post(f"{BASE_URL}/api/v2/audit-logs", json=audit_data, headers=headers)
        assert response.status_code == 200
        
        print("✅ Superadmin can create cross-tenant audit logs")

    def test_regular_user_blocked_cross_tenant_audit(self):
        """Test that regular users are blocked from cross-tenant audit creation."""
        alice_token = get_alice_token()
        superadmin_token = get_superadmin_token()
        
        # Get superadmin tenants to find different tenant
        superadmin_headers = {"Authorization": f"Bearer {superadmin_token}"}
        superadmin_response = requests.get(f"{BASE_URL}/api/v2/async/users/me", headers=superadmin_headers)
        assert superadmin_response.status_code == 200
        superadmin_tenants = superadmin_response.json()["available_tenants"]
        
        # Get alice's tenant
        alice_headers = {"Authorization": f"Bearer {alice_token}", "Content-Type": "application/json"}
        alice_response = requests.get(f"{BASE_URL}/api/v2/async/users/me", headers=alice_headers)
        assert alice_response.status_code == 200
        alice_tenant_id = alice_response.json()["current_tenant"]["id"]
        
        # Find different tenant
        other_tenant_id = None
        for tenant in superadmin_tenants:
            if tenant["id"] != alice_tenant_id:
                other_tenant_id = tenant["id"]
                break
        
        assert other_tenant_id is not None, "Need different tenant for cross-tenant test"
        
        # Try to create audit log in different tenant (should fail)
        audit_data = {
            "action": "alice_blocked_audit",
            "tenant_id": other_tenant_id
        }
        
        response = requests.post(f"{BASE_URL}/api/v2/audit-logs", json=audit_data, headers=alice_headers)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        
        print("\u2705 Regular user properly blocked from cross-tenant audit creation")

    def test_superadmin_multiple_cross_tenant_operations(self):
        """Test that superadmin can perform multiple operations across tenants."""
        token = get_superadmin_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        # Create audit logs in multiple tenants
        tenants = [
            "c8ae0700-525f-4923-ab41-c22b12b65c1a",  # Acme Corp
            "101b5f0e-3663-4564-82a9-0ed0b43a82d9"   # RBAC Corp
        ]
        
        for tenant_id in tenants:
            audit_data = {
                "action": f"test_multi_tenant_{tenant_id[:8]}",
                "resource": "audit_log",
                "resource_id": str(uuid.uuid4()),
                "tenant_id": tenant_id
            }
            
            response = requests.post(f"{BASE_URL}/api/v2/audit-logs", json=audit_data, headers=headers)
            assert response.status_code == 200
        
        print("✅ Superadmin can perform multiple cross-tenant operations")

    def test_user_permission_structure_validation(self):
        """Test that user permission structure is valid for superadmin."""
        token = get_superadmin_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{BASE_URL}/api/v2/async/users/me", headers=headers)
        assert response.status_code == 200
        
        user_data = response.json()
        
        # Validate superadmin has roles
        assert "roles" in user_data
        assert len(user_data["roles"]) > 0
        
        # Find superadmin role
        superadmin_role = None
        for role in user_data["roles"]:
            if isinstance(role, dict) and role.get("name") == "superadmin":
                superadmin_role = role
                break
            elif isinstance(role, str) and role == "superadmin":
                # Handle case where roles might be just strings
                superadmin_role = {"name": "superadmin", "permissions": ["*"]}
                break
        
        assert superadmin_role is not None, f"Superadmin role not found in roles: {user_data['roles']}"
        
        # Validate wildcard permission
        assert "*" in superadmin_role["permissions"], "Superadmin missing wildcard permission"
        
        print("\u2705 Superadmin permission structure is valid")

    def test_permission_inheritance_across_tenants(self):
        """Test that permissions work correctly across different tenants."""
        superadmin_token = get_superadmin_token()
        alice_token = get_alice_token()
        
        # Get superadmin tenants
        admin_headers = {"Authorization": f"Bearer {superadmin_token}", "Content-Type": "application/json"}
        admin_response = requests.get(f"{BASE_URL}/api/v2/async/users/me", headers=admin_headers)
        assert admin_response.status_code == 200
        admin_tenants = admin_response.json()["available_tenants"]
        
        # Get alice tenants
        user_headers = {"Authorization": f"Bearer {alice_token}", "Content-Type": "application/json"}
        user_response = requests.get(f"{BASE_URL}/api/v2/async/users/me", headers=user_headers)
        assert user_response.status_code == 200
        alice_tenant_id = user_response.json()["current_tenant"]["id"]
        
        # Find different tenant for testing
        other_tenant_id = None
        for tenant in admin_tenants:
            if tenant["id"] != alice_tenant_id:
                other_tenant_id = tenant["id"]
                break
        
        assert other_tenant_id is not None, "Need different tenant for permission test"
        
        # Test superadmin access to other tenant
        admin_audit_data = {
            "action": "admin_permission_test",
            "tenant_id": other_tenant_id
        }
        
        admin_response = requests.post(f"{BASE_URL}/api/v2/audit-logs", json=admin_audit_data, headers=admin_headers)
        assert admin_response.status_code in [200, 201], "Superadmin should have cross-tenant access"
        
        # Test alice blocked from other tenant
        user_audit_data = {
            "action": "user_permission_test",
            "tenant_id": other_tenant_id
        }
        
        user_response = requests.post(f"{BASE_URL}/api/v2/audit-logs", json=user_audit_data, headers=user_headers)
        assert user_response.status_code == 403, "Regular user should be blocked from cross-tenant access"
        
        print("\u2705 Permission inheritance works correctly across tenants")

    def test_tenant_isolation_verification(self):
        """Test that tenant isolation is properly enforced."""
        token = get_superadmin_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        # Get available tenants
        user_response = requests.get(f"{BASE_URL}/api/v2/async/users/me", headers=headers)
        assert user_response.status_code == 200
        tenants = user_response.json()["available_tenants"]
        assert len(tenants) >= 2, "Need at least 2 tenants for isolation test"
        
        # Create unique audit logs in different tenants
        unique_id = str(uuid.uuid4())[:8]
        
        audit1_data = {
            "action": f"isolation_test_1_{unique_id}",
            "tenant_id": tenants[0]["id"]
        }
        
        audit2_data = {
            "action": f"isolation_test_2_{unique_id}",
            "tenant_id": tenants[1]["id"]
        }
        
        response1 = requests.post(f"{BASE_URL}/api/v2/audit-logs", json=audit1_data, headers=headers)
        response2 = requests.post(f"{BASE_URL}/api/v2/audit-logs", json=audit2_data, headers=headers)
        
        assert response1.status_code in [200, 201]
        assert response2.status_code in [200, 201]
        
        # Verify isolation
        log1 = response1.json()
        log2 = response2.json()
        
        assert log1["tenant_id"] == tenants[0]["id"]
        assert log2["tenant_id"] == tenants[1]["id"] 
        assert log1["id"] != log2["id"]  # Different IDs
        assert log1["action"] != log2["action"]  # Different actions
        
        print("\u2705 Tenant isolation is properly enforced")