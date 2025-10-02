"""Live integration tests for superadmin multi-tenant functionality.

These tests authenticate dynamically against the running server to get fresh JWT tokens.
Tests validate:
1. Superadmin can see multiple tenants  
2. Regular user sees limited access
3. Cross-tenant operations work correctly
"""

import requests
import pytest

BASE_URL = "http://127.0.0.1:8000"

def get_auth_token(email: str, password: str) -> str:
    """Get a fresh JWT token by logging in."""
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


class TestSuperadminBasic:
    """Basic tests using dynamic authentication."""

    def test_superadmin_sees_multiple_tenants(self):
        """Test that superadmin can see multiple tenants."""
        token = get_superadmin_token()
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/v2/async/users/me", headers=headers)
        
        assert response.status_code == 200, f"Failed to get user info: {response.status_code} - {response.text}"
        
        user_data = response.json()
        available_tenants = user_data.get("available_tenants", [])
        
        # Superadmin should see multiple tenants (at least 6 from manual testing)
        assert len(available_tenants) >= 2, f"Superadmin should see multiple tenants, got {len(available_tenants)}"
        
        # Should have proper data structure
        assert "email" in user_data
        assert "current_tenant" in user_data
        assert "roles" in user_data
        
        print(f"✅ Superadmin sees {len(available_tenants)} tenants")
        
    def test_superadmin_cross_tenant_audit_log(self):
        """Test that superadmin can create audit logs across tenants."""
        token = get_superadmin_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        # Get available tenants first
        user_response = requests.get(f"{BASE_URL}/api/v2/async/users/me", headers=headers)
        assert user_response.status_code == 200
        tenants = user_response.json()["available_tenants"]
        other_tenant_id = tenants[1]["id"] if len(tenants) > 1 else tenants[0]["id"]
        
        # Try to create audit log in different tenant
        audit_data = {
            "action": "test_cross_tenant_access",
            "tenant_id": other_tenant_id
        }
        
        response = requests.post(f"{BASE_URL}/api/v2/audit-logs", json=audit_data, headers=headers)
        
        # Should succeed for superadmin
        assert response.status_code in [200, 201], f"Superadmin cross-tenant failed: {response.status_code} - {response.text}"
        
        audit_log = response.json()
        assert audit_log["action"] == "test_cross_tenant_access"
        assert audit_log["tenant_id"] == other_tenant_id
        
        print("✅ Superadmin can create cross-tenant audit logs")
        
    def test_regular_user_limited_access(self):
        """Test that regular user has limited access."""
        token = get_alice_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        # Check /me endpoint
        response = requests.get(f"{BASE_URL}/api/v2/async/users/me", headers=headers)
        
        assert response.status_code == 200, f"Failed to get user info: {response.status_code}"
        
        user_data = response.json()
        available_tenants = user_data.get("available_tenants", [])
        
        # Alice should only see her own tenant
        assert len(available_tenants) == 1, f"Regular user should see 1 tenant, got {len(available_tenants)}"
        alice_tenant_id = available_tenants[0]["id"]
        
        # Try to create audit log - should fail due to insufficient permissions
        audit_data = {
            "action": "regular_user_test",
            "tenant_id": alice_tenant_id  # Her own tenant
        }
        
        audit_response = requests.post(f"{BASE_URL}/api/v2/audit-logs", json=audit_data, headers=headers)
        assert audit_response.status_code == 403, f"Regular user should be blocked: {audit_response.status_code}"
        assert audit_response.json()["detail"] == "Insufficient permissions"
        
        print("✅ Regular user access is properly restricted")
        
    def test_cross_tenant_access_validation(self):
        """Test that cross-tenant access works for superadmin but not regular users."""
        # Get tokens
        superadmin_token = get_superadmin_token()
        alice_token = get_alice_token()
        
        # Get superadmin tenants
        superadmin_headers = {"Authorization": f"Bearer {superadmin_token}", "Content-Type": "application/json"}
        superadmin_user_response = requests.get(f"{BASE_URL}/api/v2/async/users/me", headers=superadmin_headers)
        assert superadmin_user_response.status_code == 200
        superadmin_tenants = superadmin_user_response.json()["available_tenants"]
        
        # Get alice tenants to find different tenant
        alice_headers = {"Authorization": f"Bearer {alice_token}", "Content-Type": "application/json"}
        alice_user_response = requests.get(f"{BASE_URL}/api/v2/async/users/me", headers=alice_headers)
        assert alice_user_response.status_code == 200
        alice_tenant_id = alice_user_response.json()["current_tenant"]["id"]
        
        # Find different tenant
        other_tenant_id = None
        for tenant in superadmin_tenants:
            if tenant["id"] != alice_tenant_id:
                other_tenant_id = tenant["id"]
                break
        
        assert other_tenant_id is not None, "Need different tenant for cross-tenant test"
        
        # Test superadmin cross-tenant access
        superadmin_audit_data = {
            "action": "superadmin_cross_tenant", 
            "tenant_id": other_tenant_id
        }
        
        superadmin_response = requests.post(f"{BASE_URL}/api/v2/audit-logs", json=superadmin_audit_data, headers=superadmin_headers)
        
        assert superadmin_response.status_code in [200, 201], f"Superadmin should succeed: {superadmin_response.text}"
        
        # Test regular user blocked from cross-tenant access
        alice_audit_data = {
            "action": "alice_blocked", 
            "tenant_id": other_tenant_id  # Different tenant
        }
        
        alice_response = requests.post(f"{BASE_URL}/api/v2/audit-logs", json=alice_audit_data, headers=alice_headers)
        assert alice_response.status_code == 403, f"Alice should be blocked: {alice_response.text}"
        
        print("✅ Cross-tenant access validation works correctly")

    def test_tenant_structure_validation(self):
        """Test that tenant data structure is correct."""
        token = get_superadmin_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{BASE_URL}/api/v2/async/users/me", headers=headers)
        
        assert response.status_code == 200, f"Failed to get user data: {response.status_code}"
        
        user_data = response.json()
        
        # Validate current_tenant structure
        current_tenant = user_data["current_tenant"]
        required_tenant_fields = ["id", "name", "domain"]
        for field in required_tenant_fields:
            assert field in current_tenant, f"Missing field {field} in current_tenant"
            
        # Validate available_tenants structure
        available_tenants = user_data["available_tenants"]
        for tenant in available_tenants:
            for field in required_tenant_fields:
                assert field in tenant, f"Missing field {field} in available_tenants item"
                
        print(f"✅ Tenant data structure is valid for {len(available_tenants)} tenants")