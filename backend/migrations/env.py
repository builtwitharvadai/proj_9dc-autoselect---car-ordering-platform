"""
Alembic environment configuration for async database migrations.

This module configures the Alembic migration environment with async support,
model imports, and proper migration context for both offline and online modes.
Supports PostgreSQL with asyncpg driver and includes comprehensive error handling.
"""

import asyncio
from logging.config import fileConfig
from typing import Optional

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from src.core.config import get_settings
from src.core.logging import get_logger
from src.database.base import Base

# Import all models to ensure they are registered with Base.metadata
from src.database.models.configuration import Configuration  # noqa: F401
from src.database.models.inventory import Inventory  # noqa: F401
from src.database.models.order import Order, OrderItem  # noqa: F401
from src.database.models.user import User  # noqa: F401
from src.database.models.vehicle import Vehicle  # noqa: F401

# Alembic Config object provides access to values within the .ini file
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Get application settings and logger
settings = get_settings()
logger = get_logger(__name__)

# Set target metadata for autogenerate support
target_metadata = Base.metadata

# Override sqlalchemy.url from environment if available
if settings.database_url:
    config.set_main_option("sqlalchemy.url", settings.database_url)
    logger.info(
        "Database URL configured from environment",
        url_prefix=settings.database_url.split("@")[0].split("://")[0],
    )


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine,
    though an Engine is acceptable here as well. By skipping the Engine
    creation we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    if not url:
        logger.error("No database URL configured for offline migrations")
        raise ValueError("Database URL is required for migrations")

    logger.info("Running migrations in offline mode", url_prefix=url.split("@")[0])

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
    )

    try:
        with context.begin_transaction():
            context.run_migrations()
        logger.info("Offline migrations completed successfully")
    except Exception as e:
        logger.error(
            "Offline migration failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise


def do_run_migrations(connection: Connection) -> None:
    """
    Execute migrations with the given connection.

    Args:
        connection: SQLAlchemy connection to use for migrations
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
        transaction_per_migration=True,
    )

    try:
        with context.begin_transaction():
            context.run_migrations()
        logger.info("Migration execution completed successfully")
    except Exception as e:
        logger.error(
            "Migration execution failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise


async def run_async_migrations() -> None:
    """
    Run migrations in 'online' mode with async support.

    Creates an async Engine and associates a connection with the context.
    This is the primary migration mode for production use with FastAPI.
    """
    configuration = config.get_section(config.config_ini_section, {})
    if not configuration:
        logger.error("No configuration section found in alembic.ini")
        raise ValueError("Alembic configuration is missing")

    # Override URL from settings if available
    if settings.database_url:
        configuration["sqlalchemy.url"] = settings.database_url

    # Configure connection pool for migrations
    configuration["poolclass"] = pool.NullPool

    logger.info(
        "Creating async engine for migrations",
        pool_size=configuration.get("pool_size", "NullPool"),
    )

    try:
        connectable = async_engine_from_config(
            configuration,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
            future=True,
        )

        async with connectable.connect() as connection:
            logger.info("Database connection established for migrations")

            await connection.run_sync(do_run_migrations)

        await connectable.dispose()
        logger.info("Migration engine disposed successfully")

    except Exception as e:
        logger.error(
            "Async migration failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    Entry point for online migrations that delegates to async implementation.
    This function is called by Alembic when running migrations.
    """
    logger.info("Running migrations in online mode")

    try:
        asyncio.run(run_async_migrations())
        logger.info("Online migrations completed successfully")
    except Exception as e:
        logger.error(
            "Online migration failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise


# Determine migration mode and execute
if context.is_offline_mode():
    logger.info("Alembic running in offline mode")
    run_migrations_offline()
else:
    logger.info("Alembic running in online mode")
    run_migrations_online()