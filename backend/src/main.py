"""
FastAPI application entry point with health endpoints and service routing.

This module provides the main FastAPI application instance with CORS configuration,
health check endpoints, global exception handling, and modular service routing.
Includes startup and shutdown lifecycle events for resource management.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.api.v1.auth import router as auth_router
from src.api.v1.cart import router as cart_router
from src.api.v1.configuration import router as configuration_router
from src.api.v1.dealer import router as dealer_router
from src.api.v1.dealer_management import router as dealer_management_router
from src.api.v1.orders import router as orders_router
from src.api.v1.payments import router as payments_router
from src.api.v1.recommendations import router as recommendations_router
from src.api.v1.saved_configurations import router as saved_configurations_router
from src.api.v1.vehicles import router as vehicles_router
from src.core.config import get_settings
from src.core.logging import (
    clear_context,
    configure_logging,
    get_logger,
    log_performance,
    set_request_id,
)
from src.core.security import get_csp_headers
from src.database.connection import get_db_session

# Configure logging before application initialization
configure_logging()
logger = get_logger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


async def cleanup_expired_carts():
    """
    Background task to clean up expired carts and release reservations.

    Runs periodically to remove expired anonymous carts and authenticated
    user carts that exceed their expiration periods.
    """
    from src.services.cart.service import get_cart_service

    while True:
        try:
            async with get_db_session() as session:
                service = await get_cart_service(session)
                await service.cleanup_expired_carts()
                logger.info("Expired carts cleanup completed")
        except Exception as e:
            logger.error(
                "Failed to cleanup expired carts",
                error=str(e),
                error_type=type(e).__name__,
            )
        await asyncio.sleep(300)  # Run every 5 minutes


async def cleanup_expired_reservations():
    """
    Background task to clean up expired inventory reservations.

    Runs periodically to release inventory reservations that have exceeded
    their 15-minute TTL without being converted to orders.
    """
    from src.services.cart.inventory_reservation import InventoryReservationService

    while True:
        try:
            async with get_db_session() as session:
                service = InventoryReservationService(session)
                await service.cleanup_expired_reservations()
                logger.info("Expired reservations cleanup completed")
        except Exception as e:
            logger.error(
                "Failed to cleanup expired reservations",
                error=str(e),
                error_type=type(e).__name__,
            )
        await asyncio.sleep(60)  # Run every minute


async def update_recommendation_models():
    """
    Background task to update recommendation models.

    Runs periodically to refresh recommendation models based on recent
    user interactions and configuration selections.
    """
    from src.services.recommendations.service import RecommendationService

    while True:
        try:
            async with get_db_session() as session:
                service = RecommendationService(
                    db_session=session,
                    redis_client=None,
                    enable_cache=False,
                    enable_analytics=True,
                )
                await service.update_recommendation_models()
                logger.info("Recommendation models updated successfully")
        except Exception as e:
            logger.error(
                "Failed to update recommendation models",
                error=str(e),
                error_type=type(e).__name__,
            )
        await asyncio.sleep(3600)  # Run every hour


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

    # Start background tasks
    cart_cleanup_task = asyncio.create_task(cleanup_expired_carts())
    reservation_cleanup_task = asyncio.create_task(cleanup_expired_reservations())
    recommendation_update_task = asyncio.create_task(update_recommendation_models())
    logger.info("Background tasks started for cart, reservation cleanup, and recommendation model updates")

    yield

    # Shutdown
    logger.info("Application shutting down")
    with log_performance(logger, "application_shutdown"):
        # Cancel background tasks
        cart_cleanup_task.cancel()
        reservation_cleanup_task.cancel()
        recommendation_update_task.cancel()
        try:
            await cart_cleanup_task
        except asyncio.CancelledError:
            pass
        try:
            await reservation_cleanup_task
        except asyncio.CancelledError:
            pass
        try:
            await recommendation_update_task
        except asyncio.CancelledError:
            pass
        logger.info("Background tasks stopped")
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

# Configure rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
async def security_headers_middleware(request: Request, call_next):
    """
    Middleware for adding security headers to responses.

    Adds CSP, X-Content-Type-Options, X-Frame-Options, and other
    security headers based on environment configuration.

    Args:
        request: Incoming HTTP request
        call_next: Next middleware or route handler

    Returns:
        HTTP response with security headers
    """
    response = await call_next(request)
    
    # Add security headers
    security_headers = get_csp_headers()
    for header, value in security_headers.items():
        response.headers[header] = value
    
    return response


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
        "environment": settings.environment,
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
    db_status = "healthy"
    
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
        db_status = "unhealthy"

    if not dependencies_ready:
        logger.warning("Readiness check failed", dependencies_ready=False)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "service": settings.app_name,
                "dependencies_ready": False,
                "database": db_status,
            },
        )

    return {
        "status": "ready",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "dependencies_ready": dependencies_ready,
        "database": db_status,
    }


@app.get(
    "/live",
    status_code=status.HTTP_200_OK,
    tags=["Health"],
    summary="Liveness check endpoint",
    response_description="Application liveness status",
)
async def liveness_check() -> dict[str, str]:
    """
    Liveness check endpoint for Kubernetes.

    Indicates whether the application is alive and should not be restarted.
    Returns 200 OK if application is running.

    Returns:
        Dictionary with liveness status
    """
    return {
        "status": "alive",
        "service": settings.app_name,
        "version": settings.app_version,
    }


# Include authentication router
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])

# Include vehicles router
app.include_router(vehicles_router, prefix="/api/v1/vehicles", tags=["Vehicles"])

# Include dealer router
app.include_router(dealer_router, prefix="/api/v1/dealer", tags=["Dealer"])

# Include configuration router
app.include_router(configuration_router, prefix="/api/v1", tags=["Configuration"])

# Include cart router
app.include_router(cart_router, prefix="/api/v1/cart", tags=["Cart"])

# Include saved configurations router
app.include_router(
    saved_configurations_router,
    prefix="/api/v1",
    tags=["Saved Configurations"]
)

# Include recommendations router
app.include_router(
    recommendations_router,
    prefix="/api/v1",
    tags=["Recommendations"]
)

# Include dealer management router
app.include_router(
    dealer_management_router,
    prefix="/api/v1",
    tags=["Dealer Management"]
)

# Include payments router
app.include_router(
    payments_router,
    prefix="/api/v1/payments",
    tags=["Payments"]
)

# Include orders router
app.include_router(
    orders_router,
    prefix="/api/v1/orders",
    tags=["Orders"]
)

# Service routers will be added here
# Example:
# from src.services.catalog.routes import router as catalog_router
# app.include_router(catalog_router, prefix="/api/v1/catalog", tags=["Catalog"])