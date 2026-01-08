"""
FastAPI application entry point with health endpoints and service routing.

This module provides the main FastAPI application instance with CORS configuration,
health check endpoints, global exception handling, and modular service routing.
Includes startup and shutdown lifecycle events for resource management.
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.v1.auth import router as auth_router
from src.api.v1.vehicles import router as vehicles_router
from src.core.config import get_settings
from src.core.logging import (
    clear_context,
    configure_logging,
    get_logger,
    log_performance,
    set_request_id,
)
from src.database.connection import get_db_session

# Configure logging before application initialization
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Application lifespan context manager for startup and shutdown events.

    Handles resource initialization on startup and cleanup on shutdown.
    Logs application lifecycle events with structured context.

    Args:
        app: FastAPI application instance

    Yields:
        None during application runtime
    """
    settings = get_settings()

    # Startup
    logger.info(
        "Application starting",
        environment=settings.environment,
        debug=settings.debug,
        version=settings.app_version,
    )

    with log_performance(logger, "application_startup"):
        # Initialize resources here (database, cache, etc.)
        logger.info("Resources initialized successfully")

    yield

    # Shutdown
    logger.info("Application shutting down")
    with log_performance(logger, "application_shutdown"):
        # Cleanup resources here
        logger.info("Resources cleaned up successfully")


# Initialize FastAPI application
settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Car ordering platform backend API",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    debug=settings.debug,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """
    Middleware for request logging and correlation ID management.

    Sets request ID for correlation, logs request details, and measures
    response time. Clears context after request processing.

    Args:
        request: Incoming HTTP request
        call_next: Next middleware or route handler

    Returns:
        HTTP response with X-Request-ID header
    """
    request_id = request.headers.get("X-Request-ID")
    request_id = set_request_id(request_id)

    logger.info(
        "Request received",
        method=request.method,
        path=request.url.path,
        client_host=request.client.host if request.client else None,
    )

    try:
        with log_performance(
            logger,
            "request_processing",
            method=request.method,
            path=request.url.path,
        ):
            response = await call_next(request)

        response.headers["X-Request-ID"] = request_id

        logger.info(
            "Request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
        )

        return response
    except Exception as e:
        logger.error(
            "Request failed",
            method=request.method,
            path=request.url.path,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise
    finally:
        clear_context()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handle request validation errors with structured error response.

    Args:
        request: HTTP request that caused validation error
        exc: Validation exception with error details

    Returns:
        JSON response with validation error details
    """
    logger.warning(
        "Request validation failed",
        method=request.method,
        path=request.url.path,
        errors=exc.errors(),
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "message": "Request validation failed",
            "details": exc.errors(),
            "request_id": get_request_id(),
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """
    Handle unexpected exceptions with structured error response.

    Logs error with full context and returns generic error message
    to avoid exposing internal details.

    Args:
        request: HTTP request that caused exception
        exc: Exception that was raised

    Returns:
        JSON response with error details
    """
    logger.error(
        "Unhandled exception",
        method=request.method,
        path=request.url.path,
        error=str(exc),
        error_type=type(exc).__name__,
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "request_id": get_request_id(),
        },
    )


@app.get(
    "/health",
    status_code=status.HTTP_200_OK,
    tags=["Health"],
    summary="Health check endpoint",
    response_description="Application health status",
)
async def health_check() -> dict[str, str]:
    """
    Basic health check endpoint.

    Returns application health status for monitoring and load balancers.
    Always returns 200 OK if application is running.

    Returns:
        Dictionary with health status
    """
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
    }


@app.get(
    "/ready",
    status_code=status.HTTP_200_OK,
    tags=["Health"],
    summary="Readiness check endpoint",
    response_description="Application readiness status",
)
async def readiness_check() -> dict[str, str | bool]:
    """
    Readiness check endpoint for Kubernetes and orchestration.

    Verifies that application is ready to accept traffic by checking
    dependencies like database, cache, etc. Returns 200 OK when ready.

    Returns:
        Dictionary with readiness status and dependency checks
    """
    # Check database connectivity
    dependencies_ready = True
    try:
        async with get_db_session() as session:
            await session.execute("SELECT 1")
    except Exception as e:
        logger.warning(
            "Database connectivity check failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        dependencies_ready = False

    if not dependencies_ready:
        logger.warning("Readiness check failed", dependencies_ready=False)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "service": settings.app_name,
                "dependencies_ready": False,
            },
        )

    return {
        "status": "ready",
        "service": settings.app_name,
        "version": settings.app_version,
        "dependencies_ready": dependencies_ready,
    }


# Include authentication router
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])

# Include vehicles router
app.include_router(vehicles_router, prefix="/api/v1/vehicles", tags=["Vehicles"])

# Service routers will be added here
# Example:
# from src.services.catalog.routes import router as catalog_router
# app.include_router(catalog_router, prefix="/api/v1/catalog", tags=["Catalog"])