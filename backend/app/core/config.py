from __future__ import annotations

from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Environment
    ENVIRONMENT: str = "development"

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_REQUEST_BODY: bool = False
    LOG_RESPONSE_BODY: bool = False
    APP_VERSION: str = "0.1.0"

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = False
    RATE_LIMIT_REQUESTS: int = 10000
    RATE_LIMIT_WINDOW_SECONDS: int = 600

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Cache
    CACHE_TTL: int = 300

    # Database
    DATABASE_URL: str = "sqlite:///./dev.db"

    # Auth
    SECRET_KEY: str = "dev-secret"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    TENANT_COOKIE_NAME: str = "tenant_id"
    TENANT_COOKIE_SECURE: bool = False

    # Security headers
    CSP_POLICY: str = "default-src 'self'"
    HSTS_MAX_AGE: int = 31536000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Module-level settings instance (import from other modules as `from backend.app.core.config import settings`)
settings = Settings()


def reload_settings() -> Settings:
    """Reload settings from the environment and return the new Settings instance.

    Use in tests after monkeypatch.setenv(...) to refresh the module-level `settings`.
    """
    import os

    global settings
    settings = Settings()

    # Apply explicit overrides from environment (useful for tests that monkeypatch env vars)
    def _get_bool(name: str, default: bool) -> bool:
        v = os.getenv(name)
        if v is None:
            return default
        return str(v).lower() in ("1", "true", "yes")

    def _get_int(name: str, default: int) -> int:
        v = os.getenv(name)
        if v is None:
            return default
        try:
            return int(v)
        except Exception:
            return default

    def _get_str(name: str, default: Optional[str]) -> Optional[str]:
        v = os.getenv(name)
        return v if v is not None else default

    # rate limiting
    settings.RATE_LIMIT_ENABLED = _get_bool("RATE_LIMIT_ENABLED", settings.RATE_LIMIT_ENABLED)
    settings.RATE_LIMIT_REQUESTS = _get_int("RATE_LIMIT_REQUESTS", settings.RATE_LIMIT_REQUESTS)
    settings.RATE_LIMIT_WINDOW_SECONDS = _get_int("RATE_LIMIT_WINDOW_SECONDS", settings.RATE_LIMIT_WINDOW_SECONDS)

    # environment
    settings.ENVIRONMENT = _get_str("ENVIRONMENT", settings.ENVIRONMENT) or settings.ENVIRONMENT

    # redis / cache
    settings.REDIS_URL = _get_str("REDIS_URL", settings.REDIS_URL) or settings.REDIS_URL
    settings.CACHE_TTL = _get_int("CACHE_TTL", settings.CACHE_TTL)

    # logging
    settings.LOG_REQUEST_BODY = _get_bool("LOG_REQUEST_BODY", settings.LOG_REQUEST_BODY)
    settings.LOG_RESPONSE_BODY = _get_bool("LOG_RESPONSE_BODY", settings.LOG_RESPONSE_BODY)
    settings.LOG_LEVEL = _get_str("LOG_LEVEL", settings.LOG_LEVEL) or settings.LOG_LEVEL

    # security
    settings.CSP_POLICY = _get_str("CSP_POLICY", settings.CSP_POLICY) or settings.CSP_POLICY
    settings.HSTS_MAX_AGE = _get_int("HSTS_MAX_AGE", settings.HSTS_MAX_AGE)

    # auth/db
    settings.SECRET_KEY = _get_str("SECRET_KEY", settings.SECRET_KEY) or settings.SECRET_KEY
    settings.DATABASE_URL = _get_str("DATABASE_URL", settings.DATABASE_URL) or settings.DATABASE_URL

    return settings


def get_settings() -> Settings:
    return settings

