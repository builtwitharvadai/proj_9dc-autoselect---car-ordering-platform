"""
Database connection management with SQLAlchemy async engine.

This module provides async database connection management using SQLAlchemy 2.0
with connection pooling, health checks, and proper error handling. It implements
dependency injection patterns for FastAPI integration and includes retry logic
for connection failures.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.exc import (
    DBAPIError,
    OperationalError,
    SQLAlchemyError,
)
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, QueuePool

from src.core.config import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def _convert_database_url_to_async(url: str) -> str:
    """
    Convert PostgreSQL URL to async format.

    Args:
        url: Database connection URL

    Returns:
        Async-compatible database URL with asyncpg driver
    """
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def create_engine() -> AsyncEngine:
    """
    Create async SQLAlchemy engine with connection pooling.

    Returns:
        Configured async SQLAlchemy engine

    Raises:
        ValueError: If database URL is invalid
    """
    database_url = _convert_database_url_to_async(settings.database_url)

    pool_class = NullPool if settings.environment == "test" else QueuePool

    engine = create_async_engine(
        database_url,
        echo=settings.debug,
        poolclass=pool_class,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_pre_ping=True,
        pool_recycle=3600,
        connect_args={
            "server_settings": {
                "application_name": settings.app_name,
            },
            "command_timeout": 60,
            "timeout": 10,
        },
    )

    logger.info(
        "Database engine created",
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        environment=settings.environment,
    )

    return engine


def get_engine() -> AsyncEngine:
    """
    Get or create the global async database engine.

    Returns:
        Global async SQLAlchemy engine instance

    Raises:
        RuntimeError: If engine initialization fails
    """
    global _engine

    if _engine is None:
        try:
            _engine = create_engine()
        except Exception as e:
            logger.error(
                "Failed to create database engine",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise RuntimeError(f"Database engine initialization failed: {e}") from e

    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    Get or create the global session factory.

    Returns:
        Configured async session factory

    Raises:
        RuntimeError: If session factory initialization fails
    """
    global _session_factory

    if _session_factory is None:
        try:
            engine = get_engine()
            _session_factory = async_sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False,
            )
            logger.info("Database session factory created")
        except Exception as e:
            logger.error(
                "Failed to create session factory",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise RuntimeError(f"Session factory initialization failed: {e}") from e

    return _session_factory


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Create async database session with automatic cleanup.

    Yields:
        Async database session

    Raises:
        SQLAlchemyError: If session creation or cleanup fails
    """
    session_factory = get_session_factory()
    session = session_factory()

    try:
        logger.debug("Database session created")
        yield session
        await session.commit()
        logger.debug("Database session committed")
    except Exception as e:
        await session.rollback()
        logger.error(
            "Database session rolled back",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise
    finally:
        await session.close()
        logger.debug("Database session closed")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database session injection.

    Yields:
        Async database session for request handling

    Example:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    async with get_session() as session:
        yield session


async def check_database_health(max_retries: int = 3, retry_delay: float = 1.0) -> bool:
    """
    Check database connectivity with retry logic.

    Args:
        max_retries: Maximum number of connection attempts
        retry_delay: Delay between retries in seconds

    Returns:
        True if database is healthy, False otherwise
    """
    for attempt in range(max_retries):
        try:
            engine = get_engine()
            async with engine.connect() as conn:
                await conn.execute("SELECT 1")
                logger.info("Database health check passed", attempt=attempt + 1)
                return True
        except OperationalError as e:
            logger.warning(
                "Database health check failed - operational error",
                attempt=attempt + 1,
                max_retries=max_retries,
                error=str(e),
            )
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay * (2**attempt))
        except DBAPIError as e:
            logger.warning(
                "Database health check failed - DBAPI error",
                attempt=attempt + 1,
                max_retries=max_retries,
                error=str(e),
            )
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay * (2**attempt))
        except SQLAlchemyError as e:
            logger.error(
                "Database health check failed - SQLAlchemy error",
                attempt=attempt + 1,
                max_retries=max_retries,
                error=str(e),
                error_type=type(e).__name__,
            )
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay * (2**attempt))
        except Exception as e:
            logger.error(
                "Database health check failed - unexpected error",
                attempt=attempt + 1,
                max_retries=max_retries,
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

    logger.error("Database health check failed after all retries", max_retries=max_retries)
    return False


async def get_database_stats() -> dict:
    """
    Get database connection pool statistics.

    Returns:
        Dictionary containing pool statistics

    Raises:
        RuntimeError: If engine is not initialized
    """
    try:
        engine = get_engine()
        pool = engine.pool

        stats = {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "total_connections": pool.size() + pool.overflow(),
        }

        logger.debug("Database pool statistics retrieved", **stats)
        return stats
    except Exception as e:
        logger.error(
            "Failed to retrieve database statistics",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise RuntimeError(f"Failed to get database statistics: {e}") from e


async def close_database_connections() -> None:
    """
    Close all database connections and dispose of the engine.

    This should be called during application shutdown to ensure
    proper cleanup of database resources.
    """
    global _engine, _session_factory

    if _engine is not None:
        try:
            await _engine.dispose()
            logger.info("Database connections closed and engine disposed")
        except Exception as e:
            logger.error(
                "Error closing database connections",
                error=str(e),
                error_type=type(e).__name__,
            )
        finally:
            _engine = None
            _session_factory = None


async def initialize_database() -> None:
    """
    Initialize database connection and verify connectivity.

    This should be called during application startup to ensure
    database is accessible before handling requests.

    Raises:
        RuntimeError: If database initialization fails
    """
    try:
        logger.info("Initializing database connection")
        engine = get_engine()
        get_session_factory()

        is_healthy = await check_database_health(max_retries=5, retry_delay=2.0)
        if not is_healthy:
            raise RuntimeError("Database health check failed during initialization")

        stats = await get_database_stats()
        logger.info("Database initialized successfully", **stats)
    except Exception as e:
        logger.error(
            "Database initialization failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise RuntimeError(f"Failed to initialize database: {e}") from e