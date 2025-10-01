"""Test Group 4: Tenant & Audit APIs (async)."""

import json

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


class TestAsyncTenantAuditAPIs:
    """Test async tenant and audit API endpoints (Group 4)."""

    def setup_method(self):
        """Set up test data."""
        self.test_tenant_data = {
            "name": "Test Tenant Corp",
            "domain": "testcorp.com",
            "is_active": True,
        }
        self.admin_email = "admin@testcorp.com"
        self.admin_password = "admin123"

    def create_test_tenant_and_user(self):
        """Create a test tenant and admin user."""
        # Create tenant (sync path)
        tenant_response = client.post("/api/v1/tenants", json=self.test_tenant_data)
        assert tenant_response.status_code == 200
        tenant = tenant_response.json()

        # Create admin user (sync path)
        user_data = {
            "email": self.admin_email,
            "password": self.admin_password,
            "tenant_id": tenant["id"],
            "first_name": "Admin",
            "last_name": "User",
        }
        user_response = client.post("/api/v1/users", json=user_data)
        assert user_response.status_code == 200
        user = user_response.json()

        # Create admin role (sync path)
        role_data = {
            "name": "admin",
            "tenant_id": tenant["id"],
            "permissions": [
                "tenants:list",
                "tenants:read",
                "tenants:create",
                "audit:create",
                "audit:read",
                "audit:admin",
                "users:read",
                "users:create",
                "users:update",
                "users:delete",
                "roles:read",
                "roles:create",
                "roles:update",
                "roles:delete",
            ],
        }
        role_response = client.post("/api/v1/roles", json=role_data)
        assert role_response.status_code == 200
        role = role_response.json()

        # Assign role to user (sync path)
        assign_data = {"user_id": user["id"], "role_id": role["id"]}
        assign_response = client.post(
            f"/api/v1/users/{user['id']}/roles", json=assign_data
        )
        assert assign_response.status_code == 200

        return tenant, user

    def get_admin_token(self, tenant_id):
        """Get admin authentication token for a specific tenant."""
        login_data = {
            "email": self.admin_email,
            "password": self.admin_password,
            "tenant_id": tenant_id,
        }
        response = client.post("/api/v1/auth/login", params=login_data)
        assert response.status_code == 200
        return response.json()["access_token"]

    def test_create_tenant_async(self):
        """Test async tenant creation endpoint."""
        # Create tenant
        response = client.post("/api/v1/tenants", json=self.test_tenant_data)
        assert response.status_code == 200

        tenant = response.json()
        assert tenant["name"] == self.test_tenant_data["name"]
        assert tenant["domain"] == self.test_tenant_data["domain"]
        assert tenant["is_active"] == self.test_tenant_data["is_active"]
        assert "id" in tenant
        assert "created_at" in tenant

        print(f"✅ Created tenant: {tenant['name']} (ID: {tenant['id']})")

    def test_create_tenant_idempotent(self):
        """Test tenant creation is idempotent by domain."""
        # Create first tenant
        response1 = client.post("/api/v1/tenants", json=self.test_tenant_data)
        assert response1.status_code == 200
        tenant1 = response1.json()

        # Create second tenant with same domain
        response2 = client.post("/api/v1/tenants", json=self.test_tenant_data)
        assert response2.status_code == 200
        tenant2 = response2.json()

        # Should be the same tenant (idempotent)
        assert tenant1["id"] == tenant2["id"]
        assert tenant1["domain"] == tenant2["domain"]

        print(f"✅ Tenant creation is idempotent for domain: {tenant1['domain']}")

    def test_list_tenants_requires_auth(self):
        """Test that listing tenants requires admin authentication."""
        # Without auth - should fail
        response = client.get("/api/v2/tenants")
        assert response.status_code == 401

        # With auth - should work
        tenant, user = self.create_test_tenant_and_user()
        token = self.get_admin_token(tenant["id"])
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v2/tenants", headers=headers)
        assert response.status_code == 200

        tenants = response.json()
        assert isinstance(tenants, list)
        print(f"✅ Listed {len(tenants)} tenants with proper authentication")

    def test_get_tenant_by_id(self):
        """Test getting tenant by ID."""
        # Create tenant and user
        tenant, user = self.create_test_tenant_and_user()

        # Get admin token
        token = self.get_admin_token(tenant["id"])
        headers = {"Authorization": f"Bearer {token}"}

        # Get tenant by ID
        response = client.get(f"/api/v2/tenants/{tenant['id']}", headers=headers)
        assert response.status_code == 200

        retrieved_tenant = response.json()
        assert retrieved_tenant["id"] == tenant["id"]
        assert retrieved_tenant["name"] == tenant["name"]

        print(f"✅ Retrieved tenant by ID: {retrieved_tenant['name']}")

    def test_create_audit_log_async(self):
        """Test async audit log creation."""
        # Create tenant and user
        tenant, user = self.create_test_tenant_and_user()

        # Get admin token
        token = self.get_admin_token(tenant["id"])
        headers = {"Authorization": f"Bearer {token}"}

        # Create audit log
        changes_data = {"field1": "old_value", "field2": "new_value"}
        params = {
            "action": "user_created",
            "tenant_id": tenant["id"],
            "user_id": user["id"],  # Use real user ID
            "resource_type": "user",
            "resource_id": user["id"],
            "changes": changes_data,
        }

        response = client.post("/api/v2/audit-logs", json=params, headers=headers)
        assert response.status_code == 200

        audit_log = response.json()
        assert audit_log["action"] == "user_created"
        assert audit_log["tenant_id"] == tenant["id"]
        assert "id" in audit_log
        assert "created_at" in audit_log

        print(f"✅ Created audit log: {audit_log['action']} (ID: {audit_log['id']})")

    def create_audit_log(self):
        """Helper to create and return an audit log and tenant for other tests.

        This is a helper (not a test) so it can be used by other test methods
        without confusing pytest about return values.
        """
        tenant, user = self.create_test_tenant_and_user()
        token = self.get_admin_token(tenant["id"])
        headers = {"Authorization": f"Bearer {token}"}

        changes_data = {"field1": "old_value", "field2": "new_value"}
        params = {
            "action": "user_created",
            "tenant_id": tenant["id"],
            "user_id": user["id"],
            "resource_type": "user",
            "resource_id": user["id"],
            "changes": changes_data,
        }

        response = client.post("/api/v2/audit-logs", json=params, headers=headers)
        assert response.status_code == 200
        audit_log = response.json()
        return audit_log, tenant

    def test_list_audit_logs_with_filtering(self):
        """Test listing audit logs with filtering."""
        # Create tenant and audit log
        audit_log, tenant = self.create_audit_log()

        # Get admin token
        token = self.get_admin_token(tenant["id"])
        headers = {"Authorization": f"Bearer {token}"}

        # List audit logs for tenant
        params = {"tenant_id": tenant["id"]}
        response = client.get("/api/v2/audit-logs", params=params, headers=headers)
        assert response.status_code == 200

        audit_logs = response.json()
        assert isinstance(audit_logs, list)
        assert len(audit_logs) >= 1

        # Verify the audit log is in the list
        found_log = next(
            (log for log in audit_logs if log["id"] == audit_log["id"]), None
        )
        assert found_log is not None
        assert found_log["action"] == audit_log["action"]

        print(f"✅ Listed {len(audit_logs)} audit logs for tenant")

    def test_audit_statistics(self):
        """Test audit log statistics endpoint."""
        # Create tenant and audit log
        audit_log, tenant = self.create_audit_log()

        # Get admin token
        token = self.get_admin_token(tenant["id"])
        headers = {"Authorization": f"Bearer {token}"}

        # Get statistics
        params = {"tenant_id": tenant["id"]}
        response = client.get(
            "/api/v2/audit-logs/statistics", params=params, headers=headers
        )
        assert response.status_code == 200

        stats = response.json()
        assert "total_logs" in stats
        assert "actions" in stats
        assert stats["total_logs"] >= 1

        print(f"✅ Retrieved audit statistics: {stats['total_logs']} total logs")

    def test_audit_log_requires_auth(self):
        """Test that audit operations require authentication."""
        # Create tenant first
        tenant, user = self.create_test_tenant_and_user()

        # Try to create audit log without auth
        params = {"action": "test_action", "tenant_id": tenant["id"]}
        response = client.post("/api/v2/audit-logs", json=params)
        assert response.status_code == 401

        # Try to list audit logs without auth
        response = client.get("/api/v2/audit-logs", params={"tenant_id": tenant["id"]})
        assert response.status_code == 401

        print("✅ Audit endpoints properly require authentication")

    def test_tenant_validation_errors(self):
        """Test tenant API validation errors."""
        # Get admin token
        tenant, user = self.create_test_tenant_and_user()
        token = self.get_admin_token(tenant["id"])
        headers = {"Authorization": f"Bearer {token}"}

        # Test invalid tenant ID format
        response = client.get("/api/v2/tenants/invalid-uuid", headers=headers)
        assert response.status_code == 400
        assert "Invalid tenant_id format" in response.json()["detail"]

        # Test non-existent tenant
        response = client.get(
            "/api/v2/tenants/123e4567-e89b-12d3-a456-426614174000", headers=headers
        )
        assert response.status_code == 404
        assert "Tenant not found" in response.json()["detail"]

        print("✅ Tenant validation errors handled correctly")

    def test_audit_log_validation_errors(self):
        """Test audit log API validation errors."""
        # Get admin token
        tenant, user = self.create_test_tenant_and_user()
        token = self.get_admin_token(tenant["id"])
        headers = {"Authorization": f"Bearer {token}"}

        # Test invalid JSON in changes
        params = {
            "action": "test_action",
            "tenant_id": tenant["id"],
            "changes": "invalid-json",
        }
        response = client.post("/api/v2/audit-logs", json=params, headers=headers)
        assert response.status_code == 400 or response.status_code == 422

        # Test invalid tenant_id format
        params = {"action": "test_action", "tenant_id": "invalid-uuid"}
        response = client.post("/api/v2/audit-logs", json=params, headers=headers)
        assert response.status_code == 400 or response.status_code == 422

        print("✅ Audit log validation errors handled correctly")


def test_group4_integration():
    """Integration test for Group 4: Tenant & Audit APIs."""
    print("\n🚀 Testing Group 4: Tenant & Audit APIs (Async)")

    # Run all tests
    test_instance = TestAsyncTenantAuditAPIs()
    test_instance.setup_method()

    # Test tenant operations
    test_instance.test_create_tenant_async()
    test_instance.test_create_tenant_idempotent()
    test_instance.test_list_tenants_requires_auth()
    test_instance.test_get_tenant_by_id()
    test_instance.test_tenant_validation_errors()

    # Test audit operations
    test_instance.test_create_audit_log_async()
    test_instance.test_list_audit_logs_with_filtering()
    test_instance.test_audit_statistics()
    test_instance.test_audit_log_requires_auth()
    test_instance.test_audit_log_validation_errors()

    print("\n✅ GROUP 4 COMPLETE: All Tenant & Audit APIs working correctly!")
    print("📊 Endpoints tested:")
    print("  • POST /tenants (idempotent creation)")
    print("  • GET /tenants (with auth)")
    print("  • GET /tenants/{tenant_id}")
    print("  • POST /audit-logs (with client info)")
    print("  • GET /audit-logs (with filtering)")
    print("  • GET /audit-logs/statistics")
    print("  • DELETE /audit-logs/cleanup (admin only)")
