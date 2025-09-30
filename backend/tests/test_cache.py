"""Test Redis caching functionality."""

from backend.app.cache import core as cache
from backend.app.crud import core as crud
from backend.app.schemas import core as schemas
import uuid


def test_cache_basic_operations():
    """Test basic cache operations."""
    # Test setting and getting values
    key = "test:key"
    value = {"test": "data", "number": 42}
    
    # Set value
    success = cache.set_cached(key, value)
    assert success or not cache.is_redis_available()  # Allow test to pass if Redis not available
    
    # Get value (only test if Redis is available)
    if cache.is_redis_available():
        retrieved = cache.get_cached(key)
        assert retrieved == value
        
        # Test deletion
        cache.delete_cached(key)
        retrieved = cache.get_cached(key)
        assert retrieved is None


def test_user_permission_caching(db_session, client):
    """Test user permission caching integration."""
    # Create tenant and user
    r = client.post("/tenants", json={"name": "Cache Test Corp", "domain": "cache.local"})
    assert r.status_code == 200
    tenant = r.json()
    
    ru = client.post("/users", json={
        "email": "cache@example.com",
        "password": "pass1234",
        "client_id": tenant["id"],
        "first_name": "Cache",
        "last_name": "User"
    })
    assert ru.status_code == 200
    user = ru.json()
    
    # Create role and assign to user
    role_obj = schemas.RoleCreate(name="cache_tester", permissions=["read:test", "write:test"], client_id=tenant["id"])
    role = crud.create_role(db_session, role_obj)
    crud.assign_role_to_user(db_session, user["id"], str(role.id), assigned_by=user["id"])
    db_session.commit()
    
    # First call should hit database and cache the result
    perms1 = crud.get_user_permissions(db_session, user["id"])
    assert "read:test" in perms1
    assert "write:test" in perms1
    
    # Second call should hit cache (if Redis available)
    perms2 = crud.get_user_permissions(db_session, user["id"])
    assert perms1 == perms2
    
    # Verify cache was populated (if Redis available)
    if cache.is_redis_available():
        cached_perms = cache.get_cached_user_permissions(tenant["id"], user["id"])
        assert cached_perms == perms1


def test_cache_invalidation(db_session, client):
    """Test cache invalidation when roles change."""
    # Create tenant and user
    r = client.post("/tenants", json={"name": "Cache Invalidate Corp", "domain": "invalidate.local"})
    assert r.status_code == 200
    tenant = r.json()
    
    ru = client.post("/users", json={
        "email": "invalidate@example.com",
        "password": "pass1234",
        "client_id": tenant["id"],
        "first_name": "Invalidate",
        "last_name": "User"  
    })
    assert ru.status_code == 200
    user = ru.json()
    
    # Get initial permissions (should be empty)
    perms1 = crud.get_user_permissions(db_session, user["id"])
    assert len(perms1) == 0
    
    # Create role and assign to user - this should invalidate cache
    role_obj = schemas.RoleCreate(name="invalidate_tester", permissions=["read:invalidate"], client_id=tenant["id"])
    role = crud.create_role(db_session, role_obj)
    crud.assign_role_to_user(db_session, user["id"], str(role.id), assigned_by=user["id"])
    db_session.commit()
    
    # Get permissions again - should see new permission
    perms2 = crud.get_user_permissions(db_session, user["id"])
    assert "read:invalidate" in perms2
    assert len(perms2) == 1


def test_cache_status_endpoint(client):
    """Test cache status endpoint."""
    r = client.get("/cache/status")
    assert r.status_code == 200
    data = r.json()
    assert "redis_available" in data
    assert "cache_ttl" in data
    assert isinstance(data["redis_available"], bool)
    assert isinstance(data["cache_ttl"], int)