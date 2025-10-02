# Superadmin Multi-tenant Access Test Suite

This directory contains comprehensive test cases for the superadmin multi-tenant access functionality implemented in the ReactAdmin Refine backend.

## Test Coverage

### 1. Integration Tests (`test_integration_superadmin.py`)

These tests verify the actual API behavior using real HTTP requests:

#### Core Functionality Tests
- **`test_superadmin_gets_all_tenants`**: Verifies superadmin receives all tenants in `available_tenants` array
- **`test_regular_user_gets_only_own_tenant`**: Confirms regular users only see their own tenant
- **`test_superadmin_cross_tenant_audit_log_creation`**: Tests superadmin can create audit logs in any tenant  
- **`test_regular_user_blocked_cross_tenant_audit_log`**: Ensures regular users cannot access other tenants

#### Data Integrity Tests
- **`test_user_profile_structure_consistency`**: Validates user profile structure is consistent
- **`test_audit_log_tenant_isolation`**: Confirms audit logs are properly tenant-isolated
- **`test_permission_system_wildcard_handling`**: Tests wildcard "*" permission handling

#### Edge Case Tests  
- **`test_invalid_token_rejected`**: Invalid authentication tokens are rejected
- **`test_missing_authorization_header`**: Missing auth headers handled properly
- **`test_malformed_audit_log_payload`**: Malformed payloads are rejected with proper errors

### 2. Unit Tests (`test_superadmin_multitenant.py`)

Comprehensive unit tests for individual components:

#### Multi-tenant Access Tests
- **`test_superadmin_gets_all_tenants`**: Unit test for tenant access logic
- **`test_regular_user_gets_only_own_tenant`**: User-specific tenant restriction
- **`test_superadmin_cross_tenant_access`**: Cross-tenant resource access
- **`test_regular_user_blocked_cross_tenant_access`**: Access control enforcement

#### Permission System Tests
- **`test_superadmin_wildcard_permission`**: Wildcard "*" permission grants full access
- **`test_regular_user_specific_permissions_only`**: Regular users limited by specific permissions
- **`test_tenant_access_validation_bypass`**: Superadmin bypasses tenant validation

#### Data Consistency Tests
- **`test_tenant_isolation_for_data`**: Data properly isolated between tenants
- **`test_current_tenant_remains_unchanged`**: User's primary tenant ID remains constant

## Manual Test Cases Covered

The test suite covers all the manual test scenarios we validated:

### 1. Authentication Endpoint Tests
```bash
# Superadmin login - should return all tenants
curl -X GET http://127.0.0.1:8000/api/v2/async/users/me \
  -H "Authorization: Bearer <superadmin_token>"

# Regular user login - should return only own tenant  
curl -X GET http://127.0.0.1:8000/api/v2/async/users/me \
  -H "Authorization: Bearer <user_token>"
```

### 2. Cross-tenant Access Tests
```bash
# Superadmin creating audit log in different tenant - should succeed
curl -X POST http://127.0.0.1:8000/api/v2/audit-logs \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{"action": "test", "tenant_id": "<other_tenant_id>"}'

# Regular user attempting cross-tenant access - should fail with 403
curl -X POST http://127.0.0.1:8000/api/v2/audit-logs \
  -H "Authorization: Bearer <user_token>" \
  -H "Content-Type: application/json" \
  -d '{"action": "test", "tenant_id": "<other_tenant_id>"}'
```

## Running the Tests

### Prerequisites
- FastAPI server running at `http://127.0.0.1:8000`
- Python environment with pytest and requests installed

### Quick Start
```bash
# Run all tests with the test runner
python run_superadmin_tests.py

# Run integration tests only (requires running server)
pytest tests/test_integration_superadmin.py -v

# Run unit tests only
pytest tests/test_superadmin_multitenant.py -v
```

### Manual Test Execution
```bash
# Install dependencies
pip install pytest requests

# Run specific test class
pytest tests/test_integration_superadmin.py::TestSuperadminMultitenantIntegration -v

# Run specific test method
pytest tests/test_integration_superadmin.py::TestSuperadminMultitenantIntegration::test_superadmin_gets_all_tenants -v
```

## Test Data

The integration tests use real tokens and tenant IDs from the actual system:

- **Superadmin Token**: Valid JWT with wildcard "*" permissions
- **Regular User Token**: Valid JWT with limited permissions  
- **Tenant IDs**: Real tenant UUIDs from the database

## Expected Results

### Superadmin User
- ✅ Receives 6+ tenants in `available_tenants` array
- ✅ Can create audit logs in any tenant  
- ✅ Has wildcard "*" permission for all operations
- ✅ Bypasses tenant access validation

### Regular User (Alice)
- ✅ Receives only 1 tenant (their own) in `available_tenants`
- ✅ Cannot access resources in other tenants
- ✅ Gets "Insufficient permissions" for cross-tenant operations
- ✅ Subject to normal tenant access validation

## Implementation Details Tested

### 1. Authentication System
- JWT token validation and user identification
- Tenant ID extraction from token claims
- Role-based permission checking

### 2. Multi-tenant Logic
- `get_current_user_async()` returns all tenants for superadmin
- `validate_tenant_access_async()` bypasses validation for superadmin  
- `require_permission_async()` handles wildcard "*" permissions

### 3. Data Isolation
- Audit logs properly scoped to specified tenant
- Users can only see data from their accessible tenants
- Cross-tenant operations controlled by role permissions

### 4. Error Handling
- Proper HTTP status codes (403 for insufficient permissions)
- Descriptive error messages for debugging
- Invalid token and payload rejection

## Troubleshooting

### Common Issues

1. **Integration tests fail with connection errors**
   - Ensure FastAPI server is running at `http://127.0.0.1:8000`
   - Check server logs for any startup errors

2. **Token expiration errors**
   - Tokens in test files may expire over time
   - Generate new tokens using the login endpoints

3. **Permission errors**
   - Verify superadmin user has "*" permission in database
   - Check role assignments are correct

### Test Environment Setup

1. **Database Setup**
   - Ensure SQLite database is properly initialized
   - Verify tenant and user data exists

2. **Configuration**  
   - Check `.env` file has correct database path
   - Verify JWT secret is configured

3. **Dependencies**
   - Install required packages: `pytest`, `requests`
   - Ensure FastAPI and uvicorn are available

## Continuous Integration

These tests can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions step
- name: Run Superadmin Tests
  run: |
    cd backend
    pip install -r requirements.txt
    uvicorn app.main.core:app --host 0.0.0.0 --port 8000 &
    sleep 5
    python run_superadmin_tests.py
```

## Contributing

When adding new multi-tenant features:

1. Add corresponding test cases to both integration and unit test files
2. Update this documentation with new test scenarios
3. Ensure tests cover both superadmin and regular user perspectives
4. Include edge cases and error conditions
5. Verify tests pass in isolation and as part of the full suite