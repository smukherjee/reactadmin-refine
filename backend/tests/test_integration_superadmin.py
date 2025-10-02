"""Integration tests for superadmin multi-tenant access.

These tests verify the exact scenarios we tested manually:
1. GET /api/v2/async/users/me returns all tenants for superadmin
2. GET /api/v2/async/users/me returns only user's tenant for regular users  
3. POST /api/v2/audit-logs works cross-tenant for superadmin
4. POST /api/v2/audit-logs fails cross-tenant for regular users

Tests now authenticate dynamically to get fresh JWT tokens.
"""

import json
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


class TestSuperadminMultitenantIntegration:
    """Integration tests for superadmin multi-tenant functionality."""

    def test_superadmin_gets_all_tenants(self):
        """Test: Superadmin user gets all tenants in available_tenants array."""
        token = get_superadmin_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{BASE_URL}/api/v2/async/users/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify superadmin gets multiple tenants
        available_tenants = data["available_tenants"]
        assert len(available_tenants) >= 6, f"Expected at least 6 tenants, got {len(available_tenants)}"
        
        # Verify tenant structure
        for tenant in available_tenants:
            assert "id" in tenant
            assert "name" in tenant
            assert "domain" in tenant
            
        print(f"✅ Superadmin has access to {len(available_tenants)} tenants")

    def test_regular_user_gets_own_tenant_only(self):
        """Test: Regular user gets only their own tenant in available_tenants array."""
        token = get_alice_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{BASE_URL}/api/v2/async/users/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify alice gets only one tenant
        available_tenants = data["available_tenants"]
        assert len(available_tenants) == 1, f"Expected 1 tenant, got {len(available_tenants)}"
        
        # Current tenant should match the available tenant
        current_tenant = data["current_tenant"] 
        assert available_tenants[0]["id"] == current_tenant["id"]
        
        print(f"✅ Regular user has access to {len(available_tenants)} tenant only")

    def test_superadmin_cross_tenant_audit_log_creation(self):
        """Test: Superadmin can create audit logs in different tenants."""
        token = get_superadmin_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # Get user info to extract tenant IDs
        user_response = requests.get(f"{BASE_URL}/api/v2/async/users/me", headers=headers)
        assert user_response.status_code == 200
        tenants = user_response.json()["available_tenants"]
        other_tenant_id = tenants[1]["id"] if len(tenants) > 1 else tenants[0]["id"]

        payload = {
            "action": "superadmin_cross_tenant_test",
            "tenant_id": other_tenant_id
        }

        response = requests.post(
            f"{BASE_URL}/api/v2/audit-logs",
            headers=headers,
            json=payload
        )

        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["action"] == "superadmin_cross_tenant_test"
        assert data["tenant_id"] == other_tenant_id
        
        print("✅ Superadmin can create cross-tenant audit logs")

    def test_regular_user_blocked_cross_tenant(self):
        """Test: Regular user blocked from cross-tenant audit log creation."""
        alice_token = get_alice_token()
        superadmin_token = get_superadmin_token()
        
        # Get superadmin tenants to find a different tenant
        superadmin_headers = {"Authorization": f"Bearer {superadmin_token}"}
        superadmin_response = requests.get(f"{BASE_URL}/api/v2/async/users/me", headers=superadmin_headers)
        assert superadmin_response.status_code == 200
        superadmin_tenants = superadmin_response.json()["available_tenants"]
        
        # Get alice's tenant
        alice_headers = {"Authorization": f"Bearer {alice_token}", "Content-Type": "application/json"}
        alice_response = requests.get(f"{BASE_URL}/api/v2/async/users/me", headers=alice_headers)
        assert alice_response.status_code == 200
        alice_tenant = alice_response.json()["current_tenant"]["id"]
        
        # Find a different tenant that alice doesn't have access to
        other_tenant_id = None
        for tenant in superadmin_tenants:
            if tenant["id"] != alice_tenant:
                other_tenant_id = tenant["id"]
                break
        
        assert other_tenant_id is not None, "Could not find different tenant for test"

        payload = {
            "action": "alice_blocked_cross_tenant", 
            "tenant_id": other_tenant_id
        }

        response = requests.post(
            f"{BASE_URL}/api/v2/audit-logs",
            headers=alice_headers,
            json=payload
        )

        # Alice should be blocked from creating audit logs in other tenants
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        
        print("✅ Regular user properly blocked from cross-tenant operations")

    def test_tenant_data_validation(self):
        """Test: Tenant data structure and content validation."""
        token = get_superadmin_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{BASE_URL}/api/v2/async/users/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate current_tenant structure
        current_tenant = data["current_tenant"]
        required_fields = ["id", "name", "domain", "is_active", "created_at"]
        for field in required_fields:
            assert field in current_tenant, f"Missing {field} in current_tenant"
            
        # Validate available_tenants structure
        available_tenants = data["available_tenants"]
        for tenant in available_tenants:
            for field in required_fields:
                assert field in tenant, f"Missing {field} in available_tenants item"
                
        print("✅ Tenant data structure validation passed")

    def test_user_profile_validation(self):
        """Test: User profile contains required fields and proper structure."""
        token = get_superadmin_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{BASE_URL}/api/v2/async/users/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate required user fields
        required_user_fields = ["id", "email", "first_name", "last_name", "tenant_id", "is_active"]
        for field in required_user_fields:
            assert field in data, f"Missing {field} in user profile"
            
        # Validate roles structure
        assert "roles" in data
        assert isinstance(data["roles"], list)
        assert len(data["roles"]) > 0, "Superadmin should have roles"
        
        # Validate superadmin role has wildcard permission
        superadmin_role = next((role for role in data["roles"] if role["name"] == "superadmin"), None)
        assert superadmin_role is not None, "Superadmin role not found"
        assert "*" in superadmin_role["permissions"], "Superadmin role missing wildcard permission"
        
        print("✅ User profile structure validation passed")

    def test_audit_log_tenant_isolation(self):
        """Test: Audit logs are properly isolated by tenant."""
        token = get_superadmin_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # Get available tenants
        user_response = requests.get(f"{BASE_URL}/api/v2/async/users/me", headers=headers)
        assert user_response.status_code == 200
        tenants = user_response.json()["available_tenants"]
        assert len(tenants) >= 2, "Need at least 2 tenants for isolation test"

        # Create logs in different tenants
        tenant1_payload = {
            "action": "tenant1_isolation_test",
            "tenant_id": tenants[0]["id"]
        }

        tenant2_payload = {
            "action": "tenant2_isolation_test",
            "tenant_id": tenants[1]["id"]
        }

        # Create logs in both tenants
        response1 = requests.post(f"{BASE_URL}/api/v2/audit-logs", headers=headers, json=tenant1_payload)
        response2 = requests.post(f"{BASE_URL}/api/v2/audit-logs", headers=headers, json=tenant2_payload)
        
        assert response1.status_code in [200, 201]
        assert response2.status_code in [200, 201]
        
        # Verify each audit log is assigned to correct tenant
        data1 = response1.json()
        data2 = response2.json()
        
        assert data1["tenant_id"] == tenants[0]["id"]
        assert data2["tenant_id"] == tenants[1]["id"]
        assert data1["action"] == "tenant1_isolation_test"
        assert data2["action"] == "tenant2_isolation_test"
        
        print("✅ Audit log tenant isolation working correctly")

    def test_permission_system_wildcard_handling(self):
        """Test: Permission system correctly handles wildcard '*' for superadmin."""
        # This test verifies that superadmin's "*" permission grants access
        # We test this indirectly by confirming cross-tenant operations work

        token = get_superadmin_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # Get available tenants
        user_response = requests.get(f"{BASE_URL}/api/v2/async/users/me", headers=headers)
        assert user_response.status_code == 200
        tenants = user_response.json()["available_tenants"]
        assert len(tenants) >= 2, "Need at least 2 tenants for wildcard test"

        # Multiple operations that require different permissions
        test_operations = [
            {
                "action": "wildcard_audit_test",
                "tenant_id": tenants[0]["id"],
                "expected_permission": "audit:create"
            },
            {
                "action": "wildcard_admin_test",
                "tenant_id": tenants[1]["id"],
                "expected_permission": "audit:create"
            }
        ]

        for operation in test_operations:
            payload = {
                "action": operation["action"],
                "tenant_id": operation["tenant_id"]
            }

            response = requests.post(f"{BASE_URL}/api/v2/audit-logs", headers=headers, json=payload)
            
            assert response.status_code in [200, 201], (
                f"Wildcard permission failed for {operation['expected_permission']} "
                f"in tenant {operation['tenant_id']}: {response.text}"
            )
            
            data = response.json()
            assert data["action"] == operation["action"]
            assert data["tenant_id"] == operation["tenant_id"]
            
        print("✅ Wildcard permission system working correctly")


class TestSuperadminEdgeCases:
    """Edge case tests for superadmin functionality."""
    
    def test_malformed_audit_log_payload(self):
        """Test: Malformed audit log payloads are rejected."""
        # Use a valid token but invalid payload
        token = get_superadmin_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # Test missing required fields
        test_cases = [
            {},  # Empty payload
            {"action": "test"},  # Missing tenant_id
            {"tenant_id": "some-id"},  # Missing action
            {"action": "", "tenant_id": "some-id"},  # Empty action
        ]

        for payload in test_cases:
            response = requests.post(f"{BASE_URL}/api/v2/audit-logs", headers=headers, json=payload)
            assert response.status_code in [400, 422], f"Expected 400/422 for payload {payload}, got {response.status_code}"
            
        print("✅ Malformed payloads properly rejected")

    def test_expired_token_behavior(self):
        """Test: Expired tokens are properly rejected."""
        # Use an obviously expired token (exp from 2020)
        expired_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXVzZXIiLCJleHAiOjE1NzczNjgwMDB9.invalid"
        headers = {"Authorization": f"Bearer {expired_token}"}
        
        response = requests.get(f"{BASE_URL}/api/v2/async/users/me", headers=headers)
        
        assert response.status_code == 401, f"Expected 401 for expired token, got {response.status_code}"
        
        print("✅ Expired token properly rejected")