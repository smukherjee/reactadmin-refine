"""Alembic environment for migrations. Uses application settings for DB URL.

This env.py is intentionally self-contained within backend/ so no root files are created.
"""
from logging.config import fileConfig
import os
import sys
from sqlalchemy import engine_from_config
from sqlalchemy import pool

# allow importing the application package from backend/
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import settings from the application to read the DATABASE URL
try:
    from backend.app.core.config import settings
except Exception:
    settings = None

# set sqlalchemy.url dynamically if available
if settings and getattr(settings, "DATABASE_URL", None):
    config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# add your model's MetaData object here for 'autogenerate' support
try:
    # import the application's Base (SQLAlchemy declarative base)
    from backend.app.db.core import Base as AppBase

    target_metadata = AppBase.metadata
except Exception:
    # Fallback: no metadata available
    target_metadata = None


def run_migrations_offline():
    # prefer explicit alembic config value, fall back to env var or sensible default
    url = config.get_main_option("sqlalchemy.url")
    if not url:
        url = os.getenv("DATABASE_URL")
    if not url:
        # default to a backend-local sqlite file
        default_db = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "db", "dev.db"))
        url = f"sqlite:///{default_db}"

    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    cfg_section = config.get_section(config.config_ini_section) or {}
    connectable = engine_from_config(
        cfg_section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
