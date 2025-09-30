"""Test structured logging functionality."""

import json
import logging
import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from backend.app.core.logging import (
    StructuredFormatter,
    generate_request_id,
    get_logger,
    log_auth_event,
    log_cache_operation,
    log_database_operation,
    log_permission_check,
    set_request_context,
    setup_logging,
)
from backend.main import app


def test_structured_formatter():
    """Test that structured formatter produces valid JSON."""
    formatter = StructuredFormatter()

    # Create a log record
    logger = logging.getLogger("test")
    record = logger.makeRecord(
        name="test.module",
        level=logging.INFO,
        fn="test.py",
        lno=42,
        msg="Test message",
        args=(),
        exc_info=None,
    )

    # Format the record
    formatted = formatter.format(record)

    # Should be valid JSON
    log_data = json.loads(formatted)

    assert log_data["level"] == "INFO"
    assert log_data["logger"] == "test.module"
    assert log_data["message"] == "Test message"
    assert log_data["module"] == "test"
    assert log_data["line"] == 42
    assert "timestamp" in log_data


def test_structured_formatter_with_context():
    """Test structured formatter with request context."""
    formatter = StructuredFormatter()

    # Set request context
    request_id = generate_request_id()
    set_request_context(request_id, "user123", "tenant456")

    logger = logging.getLogger("test")
    record = logger.makeRecord(
        name="test.module",
        level=logging.INFO,
        fn="test.py",
        lno=42,
        msg="Test message with context",
        args=(),
        exc_info=None,
    )

    formatted = formatter.format(record)
    log_data = json.loads(formatted)

    assert log_data["request_id"] == request_id
    assert log_data["user_id"] == "user123"
    assert log_data["tenant_id"] == "tenant456"


def test_auth_event_logging():
    """Test authentication event logging."""
    logger = get_logger("auth.security")

    # Test successful login
    log_auth_event(
        "login", "user@example.com", success=True, details={"ip": "127.0.0.1"}
    )

    # Test failed login
    log_auth_event(
        "login",
        "user@example.com",
        success=False,
        details={"reason": "invalid_password"},
    )


def test_permission_check_logging():
    """Test permission check logging."""
    log_permission_check("users", "read", "user123", "tenant456", allowed=True)
    log_permission_check("admin", "delete", "user123", "tenant456", allowed=False)


def test_database_operation_logging():
    """Test database operation logging."""
    log_database_operation("SELECT", "users", 50.5, record_count=10)
    log_database_operation("UPDATE", "users", 1200.8, record_count=1)  # Slow query


def test_cache_operation_logging():
    """Test cache operation logging."""
    log_cache_operation("get", "user:123:permissions", hit=True, duration_ms=5.2)
    log_cache_operation("set", "user:123:roles", duration_ms=10.1)
    log_cache_operation("delete", "user:123:*")


def test_request_logging_middleware():
    """Test request logging middleware integration."""
    client = TestClient(app)

    # Make a request that should be logged (not in skip_paths)
    response = client.get("/api/v1/info")
    assert response.status_code == 200

    # Check that request ID header is present
    assert "X-Request-ID" in response.headers
    assert "X-Process-Time" in response.headers

    # Process time should be a valid float
    process_time = float(response.headers["X-Process-Time"])
    assert process_time >= 0


def test_performance_logging_middleware():
    """Test performance logging middleware for slow requests."""
    client = TestClient(app)

    # Test a normal request (not in skip_paths)
    response = client.get("/api/v1/info")
    assert response.status_code == 200

    # Process time header should be present
    assert "X-Process-Time" in response.headers


def test_logging_configuration():
    """Test logging configuration setup."""
    # Test development configuration
    os.environ["ENVIRONMENT"] = "development"
    os.environ["LOG_LEVEL"] = "DEBUG"
    # Refresh settings so setup_logging reads the updated ENVIRONMENT/LOG_LEVEL
    try:
        from backend.app.core import config as _config

        _config.reload_settings()
    except Exception:
        pass

    setup_logging()

    logger = get_logger("test")
    assert logger.level <= logging.DEBUG

    # Test production configuration
    os.environ["ENVIRONMENT"] = "production"
    try:
        from backend.app.core import config as _config

        _config.reload_settings()
    except Exception:
        pass
    setup_logging()

    # Should still work without errors


def test_request_id_generation():
    """Test request ID generation and uniqueness."""
    request_id1 = generate_request_id()
    request_id2 = generate_request_id()

    assert request_id1 != request_id2
    assert len(request_id1) > 0
    assert len(request_id2) > 0


def test_sensitive_data_sanitization():
    """Test that sensitive data is properly sanitized in middleware."""
    from backend.app.middleware.logging import RequestLoggingMiddleware

    middleware = RequestLoggingMiddleware(app)

    # Test data sanitization
    test_data = {
        "username": "testuser",
        "password": "secret123",
        "api_key": "abc123",
        "token": "jwt_token",
        "normal_field": "safe_value",
        "nested": {"authorization": "Bearer token", "safe_nested": "value"},
    }

    sanitized = middleware._sanitize_data(test_data)

    assert sanitized["username"] == "testuser"
    assert sanitized["password"] == "<redacted>"
    assert sanitized["api_key"] == "<redacted>"
    assert sanitized["token"] == "<redacted>"
    assert sanitized["normal_field"] == "safe_value"
    assert sanitized["nested"]["authorization"] == "<redacted>"
    assert sanitized["nested"]["safe_nested"] == "value"


def test_logging_with_detailed_health_endpoint():
    """Test that detailed health endpoint generates appropriate logs."""
    client = TestClient(app)

    response = client.get("/health/detailed")
    assert response.status_code == 200

    data = response.json()
    assert "components" in data
    assert "database" in data["components"]
    assert "redis" in data["components"]
    assert "system" in data["components"]


def test_log_file_creation():
    """Test that log files are created in production mode."""
    # Temporarily set production mode
    original_env = os.environ.get("ENVIRONMENT")
    os.environ["ENVIRONMENT"] = "production"

    try:
        setup_logging()

        # Check that logs directory exists
        assert os.path.exists("logs")

        # Generate a log entry
        logger = get_logger("test.production")
        logger.info("Test production log entry")

        # Log file should exist (though it might be empty due to buffering)
        assert os.path.exists("logs/app.log")

    finally:
        # Restore original environment
        if original_env:
            os.environ["ENVIRONMENT"] = original_env
        else:
            os.environ.pop("ENVIRONMENT", None)
        # Restore settings to original environment
        try:
            from backend.app.core import config as _config

            _config.reload_settings()
        except Exception:
            pass
