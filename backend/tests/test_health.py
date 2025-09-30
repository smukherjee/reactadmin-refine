"""Test health and metrics endpoints."""

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health_endpoint():
    """Test basic health check endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "version" in data
    assert "environment" in data


def test_detailed_health_endpoint():
    """Test detailed health check endpoint."""
    response = client.get("/api/v1/health/detailed")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "timestamp" in data
    assert "version" in data
    assert "environment" in data
    assert "components" in data

    # Check components
    components = data["components"]
    assert "database" in components
    assert "redis" in components
    assert "system" in components

    # Database component should be healthy
    assert components["database"]["status"] == "healthy"
    assert "response_time_ms" in components["database"]

    # Redis component should be healthy
    assert components["redis"]["status"] == "healthy"
    assert "response_time_ms" in components["redis"]
    assert "memory_usage_mb" in components["redis"]
    assert "connected_clients" in components["redis"]

    # System component may be 'healthy' or 'initializing' in test environments
    assert components["system"]["status"] in ("healthy", "initializing")
    assert "cpu_percent" in components["system"]
    assert "memory_percent" in components["system"]
    assert "memory_available_mb" in components["system"]
    assert "disk_usage_percent" in components["system"]


def test_metrics_endpoint():
    """Test system metrics endpoint."""
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200

    data = response.json()
    assert "cpu_percent" in data
    assert "memory_percent" in data
    assert "memory_available_mb" in data
    assert "disk_usage_percent" in data
    assert "uptime_seconds" in data

    # Validate data types and ranges
    assert isinstance(data["cpu_percent"], (int, float))
    assert isinstance(data["memory_percent"], (int, float))
    assert isinstance(data["memory_available_mb"], (int, float))
    assert isinstance(data["disk_usage_percent"], (int, float))
    assert isinstance(data["uptime_seconds"], (int, float))

    # Basic range checks
    assert 0 <= data["cpu_percent"] <= 100
    assert 0 <= data["memory_percent"] <= 100
    assert data["memory_available_mb"] >= 0
    assert 0 <= data["disk_usage_percent"] <= 100
    assert data["uptime_seconds"] >= 0


def test_readiness_endpoint():
    """Test Kubernetes readiness probe endpoint."""
    response = client.get("/api/v1/readiness")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] in ["ready", "not_ready"]
    assert "timestamp" in data

    # If healthy, should be ready
    if data["status"] == "not_ready":
        assert "error" in data


def test_liveness_endpoint():
    """Test Kubernetes liveness probe endpoint."""
    response = client.get("/api/v1/liveness")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "alive"
    assert "timestamp" in data


def test_cache_status_endpoint():
    """Test cache status endpoint."""
    response = client.get("/api/v1/cache/status")
    assert response.status_code == 200

    data = response.json()
    assert "redis_available" in data
    assert "redis_url" in data
    assert "cache_ttl" in data

    assert isinstance(data["redis_available"], bool)
    assert isinstance(data["cache_ttl"], int)


def test_api_v1_info_endpoint():
    """Test API v1 info endpoint."""
    response = client.get("/api/v1/info")
    assert response.status_code == 200

    data = response.json()
    assert data["version"] == "v1"
    assert "description" in data
    assert "endpoints" in data

    endpoints = data["endpoints"]
    assert "health" in endpoints
    assert "auth" in endpoints
    assert "users" in endpoints
    assert "roles" in endpoints
