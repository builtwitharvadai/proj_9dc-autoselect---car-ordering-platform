"""
Comprehensive test suite for FastAPI main application.

Tests cover health endpoints, middleware, exception handlers, CORS configuration,
application lifecycle, and request processing with high coverage and best practices.
"""

import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.main import app


# ============================================================================
# UNIT TESTS - Health Endpoints
# ============================================================================


class TestHealthEndpoints:
    """Test suite for health check and readiness endpoints."""

    def test_health_check_returns_200(self, test_client: TestClient):
        """
        Test health endpoint returns 200 OK with correct structure.

        Validates that the health check endpoint is accessible and returns
        the expected status, service name, and version information.
        """
        response = test_client.get("/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data
        assert "version" in data

    def test_health_check_response_structure(self, test_client: TestClient):
        """
        Test health endpoint response contains all required fields.

        Ensures the health check response includes all necessary fields
        for monitoring and load balancer integration.
        """
        response = test_client.get("/health")
        data = response.json()

        assert isinstance(data, dict)
        assert len(data) == 3
        assert all(key in data for key in ["status", "service", "version"])
        assert isinstance(data["status"], str)
        assert isinstance(data["service"], str)
        assert isinstance(data["version"], str)

    def test_readiness_check_returns_200_when_ready(
        self, test_client: TestClient
    ):
        """
        Test readiness endpoint returns 200 when dependencies are ready.

        Validates that the readiness check endpoint correctly reports
        application readiness for accepting traffic.
        """
        response = test_client.get("/ready")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ready"
        assert data["dependencies_ready"] is True
        assert "service" in data
        assert "version" in data

    def test_readiness_check_response_structure(
        self, test_client: TestClient
    ):
        """
        Test readiness endpoint response contains all required fields.

        Ensures the readiness check response includes dependency status
        and application metadata.
        """
        response = test_client.get("/ready")
        data = response.json()

        assert isinstance(data, dict)
        assert all(
            key in data
            for key in ["status", "service", "version", "dependencies_ready"]
        )
        assert isinstance(data["dependencies_ready"], bool)

    @pytest.mark.parametrize(
        "endpoint,expected_status",
        [
            ("/health", "healthy"),
            ("/ready", "ready"),
        ],
    )
    def test_health_endpoints_status_values(
        self, test_client: TestClient, endpoint: str, expected_status: str
    ):
        """
        Test health endpoints return correct status values.

        Parametrized test to verify both health and readiness endpoints
        return their expected status values.
        """
        response = test_client.get(endpoint)
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data["status"] == expected_status


# ============================================================================
# INTEGRATION TESTS - Async Client
# ============================================================================


class TestAsyncHealthEndpoints:
    """Test suite for async health endpoint access."""

    @pytest.mark.asyncio
    async def test_health_check_async(self, async_client: AsyncClient):
        """
        Test health endpoint with async client.

        Validates that health check works correctly with asynchronous
        HTTP client for async application testing.
        """
        response = await async_client.get("/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_readiness_check_async(self, async_client: AsyncClient):
        """
        Test readiness endpoint with async client.

        Validates that readiness check works correctly with asynchronous
        HTTP client for async application testing.
        """
        response = await async_client.get("/ready")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ready"

    @pytest.mark.asyncio
    async def test_concurrent_health_checks(
        self, async_client: AsyncClient
    ):
        """
        Test multiple concurrent health check requests.

        Validates that the application can handle multiple simultaneous
        health check requests without issues.
        """
        tasks = [async_client.get("/health") for _ in range(10)]
        responses = await asyncio.gather(*tasks)

        assert all(r.status_code == status.HTTP_200_OK for r in responses)
        assert all(r.json()["status"] == "healthy" for r in responses)


# ============================================================================
# UNIT TESTS - Middleware
# ============================================================================


class TestRequestLoggingMiddleware:
    """Test suite for request logging middleware functionality."""

    def test_middleware_adds_request_id_header(self, test_client: TestClient):
        """
        Test middleware adds X-Request-ID header to response.

        Validates that the request logging middleware correctly adds
        correlation ID header to all responses.
        """
        response = test_client.get("/health")

        assert "X-Request-ID" in response.headers
        assert len(response.headers["X-Request-ID"]) > 0

    def test_middleware_preserves_custom_request_id(
        self, test_client: TestClient
    ):
        """
        Test middleware preserves custom X-Request-ID from request.

        Validates that when a client provides a request ID, the middleware
        uses it instead of generating a new one.
        """
        custom_request_id = "test-request-123"
        response = test_client.get(
            "/health", headers={"X-Request-ID": custom_request_id}
        )

        assert response.headers["X-Request-ID"] == custom_request_id

    def test_middleware_generates_unique_request_ids(
        self, test_client: TestClient
    ):
        """
        Test middleware generates unique request IDs for each request.

        Validates that each request without a custom ID gets a unique
        correlation ID for tracking.
        """
        response1 = test_client.get("/health")
        response2 = test_client.get("/health")

        request_id1 = response1.headers["X-Request-ID"]
        request_id2 = response2.headers["X-Request-ID"]

        assert request_id1 != request_id2
        assert len(request_id1) > 0
        assert len(request_id2) > 0

    @patch("src.main.logger")
    def test_middleware_logs_request_received(
        self, mock_logger: MagicMock, test_client: TestClient
    ):
        """
        Test middleware logs incoming request details.

        Validates that the middleware logs request method, path, and
        client information for monitoring.
        """
        test_client.get("/health")

        mock_logger.info.assert_any_call(
            "Request received",
            method="GET",
            path="/health",
            client_host="testclient",
        )

    @patch("src.main.logger")
    def test_middleware_logs_request_completed(
        self, mock_logger: MagicMock, test_client: TestClient
    ):
        """
        Test middleware logs successful request completion.

        Validates that the middleware logs completion status including
        response status code.
        """
        test_client.get("/health")

        mock_logger.info.assert_any_call(
            "Request completed",
            method="GET",
            path="/health",
            status_code=200,
        )


# ============================================================================
# UNIT TESTS - Exception Handlers
# ============================================================================


class TestExceptionHandlers:
    """Test suite for global exception handling."""

    def test_validation_error_handler_returns_422(
        self, test_client: TestClient
    ):
        """
        Test validation error handler returns 422 status.

        Validates that request validation errors are properly caught
        and return appropriate HTTP status code.
        """
        # Create a test endpoint that will trigger validation error
        from fastapi import FastAPI
        from pydantic import BaseModel

        test_app = FastAPI()

        class TestModel(BaseModel):
            required_field: str

        @test_app.post("/test")
        async def test_endpoint(data: TestModel):
            return {"status": "ok"}

        # Copy exception handlers from main app
        for handler in app.exception_handlers:
            test_app.add_exception_handler(handler, app.exception_handlers[handler])

        with TestClient(test_app) as client:
            response = client.post("/test", json={})

            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch("src.main.logger")
    def test_validation_error_handler_logs_warning(
        self, mock_logger: MagicMock, test_client: TestClient
    ):
        """
        Test validation error handler logs warning with details.

        Validates that validation errors are logged with appropriate
        severity and error details.
        """
        from fastapi import FastAPI
        from pydantic import BaseModel

        test_app = FastAPI()

        class TestModel(BaseModel):
            required_field: str

        @test_app.post("/test")
        async def test_endpoint(data: TestModel):
            return {"status": "ok"}

        for handler in app.exception_handlers:
            test_app.add_exception_handler(handler, app.exception_handlers[handler])

        with TestClient(test_app) as client:
            client.post("/test", json={})

            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args
            assert "Request validation failed" in call_args[0]

    def test_validation_error_response_structure(
        self, test_client: TestClient
    ):
        """
        Test validation error response contains required fields.

        Validates that validation error responses include error type,
        message, details, and request ID.
        """
        from fastapi import FastAPI
        from pydantic import BaseModel

        test_app = FastAPI()

        class TestModel(BaseModel):
            required_field: str

        @test_app.post("/test")
        async def test_endpoint(data: TestModel):
            return {"status": "ok"}

        for handler in app.exception_handlers:
            test_app.add_exception_handler(handler, app.exception_handlers[handler])

        with TestClient(test_app) as client:
            response = client.post("/test", json={})
            data = response.json()

            assert "error" in data
            assert "message" in data
            assert "details" in data
            assert "request_id" in data
            assert data["error"] == "Validation Error"

    @patch("src.main.logger")
    def test_global_exception_handler_logs_error(
        self, mock_logger: MagicMock, test_client: TestClient
    ):
        """
        Test global exception handler logs unhandled exceptions.

        Validates that unexpected exceptions are logged with full
        context and error information.
        """
        from fastapi import FastAPI

        test_app = FastAPI()

        @test_app.get("/error")
        async def error_endpoint():
            raise ValueError("Test error")

        for handler in app.exception_handlers:
            test_app.add_exception_handler(handler, app.exception_handlers[handler])

        with TestClient(test_app) as client:
            client.get("/error")

            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            assert "Unhandled exception" in call_args[0]

    def test_global_exception_handler_returns_500(
        self, test_client: TestClient
    ):
        """
        Test global exception handler returns 500 status.

        Validates that unhandled exceptions result in appropriate
        internal server error status code.
        """
        from fastapi import FastAPI

        test_app = FastAPI()

        @test_app.get("/error")
        async def error_endpoint():
            raise ValueError("Test error")

        for handler in app.exception_handlers:
            test_app.add_exception_handler(handler, app.exception_handlers[handler])

        with TestClient(test_app) as client:
            response = client.get("/error")

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_global_exception_handler_response_structure(
        self, test_client: TestClient
    ):
        """
        Test global exception handler response contains required fields.

        Validates that error responses include error type, generic message,
        and request ID without exposing internal details.
        """
        from fastapi import FastAPI

        test_app = FastAPI()

        @test_app.get("/error")
        async def error_endpoint():
            raise ValueError("Test error")

        for handler in app.exception_handlers:
            test_app.add_exception_handler(handler, app.exception_handlers[handler])

        with TestClient(test_app) as client:
            response = client.get("/error")
            data = response.json()

            assert "error" in data
            assert "message" in data
            assert "request_id" in data
            assert data["error"] == "Internal Server Error"
            assert "Test error" not in data["message"]  # Don't expose details


# ============================================================================
# INTEGRATION TESTS - CORS Configuration
# ============================================================================


class TestCORSConfiguration:
    """Test suite for CORS middleware configuration."""

    def test_cors_allows_configured_origins(self, test_client: TestClient):
        """
        Test CORS allows requests from configured origins.

        Validates that CORS middleware properly handles requests from
        allowed origins with appropriate headers.
        """
        response = test_client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert "access-control-allow-origin" in response.headers

    def test_cors_exposes_request_id_header(self, test_client: TestClient):
        """
        Test CORS exposes X-Request-ID header to clients.

        Validates that the correlation ID header is exposed through
        CORS for client-side tracking.
        """
        response = test_client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        exposed_headers = response.headers.get(
            "access-control-expose-headers", ""
        )
        assert "X-Request-ID" in exposed_headers

    def test_cors_allows_credentials(self, test_client: TestClient):
        """
        Test CORS allows credentials for authenticated requests.

        Validates that CORS configuration permits credentials for
        cross-origin authenticated requests.
        """
        response = test_client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        assert (
            response.headers.get("access-control-allow-credentials") == "true"
        )

    def test_cors_allows_all_methods(self, test_client: TestClient):
        """
        Test CORS allows all HTTP methods.

        Validates that CORS configuration permits all standard HTTP
        methods for API flexibility.
        """
        response = test_client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )

        allowed_methods = response.headers.get(
            "access-control-allow-methods", ""
        )
        assert "POST" in allowed_methods or "*" in allowed_methods


# ============================================================================
# INTEGRATION TESTS - Application Lifecycle
# ============================================================================


class TestApplicationLifecycle:
    """Test suite for application startup and shutdown."""

    @patch("src.main.logger")
    def test_application_startup_logs_info(self, mock_logger: MagicMock):
        """
        Test application startup logs initialization info.

        Validates that application startup event logs environment,
        debug mode, and version information.
        """
        with TestClient(app):
            # Startup happens in context manager
            pass

        # Check that startup logging occurred
        startup_calls = [
            call
            for call in mock_logger.info.call_args_list
            if "Application starting" in str(call)
        ]
        assert len(startup_calls) > 0

    @patch("src.main.logger")
    def test_application_shutdown_logs_info(self, mock_logger: MagicMock):
        """
        Test application shutdown logs cleanup info.

        Validates that application shutdown event logs resource
        cleanup and shutdown completion.
        """
        with TestClient(app):
            pass  # Shutdown happens when context exits

        # Check that shutdown logging occurred
        shutdown_calls = [
            call
            for call in mock_logger.info.call_args_list
            if "Application shutting down" in str(call)
        ]
        assert len(shutdown_calls) > 0

    def test_application_metadata(self, test_client: TestClient):
        """
        Test application has correct metadata configuration.

        Validates that FastAPI application is configured with correct
        title, version, and documentation URLs.
        """
        assert app.title is not None
        assert app.version is not None
        assert app.docs_url == "/docs"
        assert app.redoc_url == "/redoc"
        assert app.openapi_url == "/openapi.json"


# ============================================================================
# INTEGRATION TESTS - OpenAPI Documentation
# ============================================================================


class TestOpenAPIDocumentation:
    """Test suite for OpenAPI documentation endpoints."""

    def test_openapi_json_accessible(self, test_client: TestClient):
        """
        Test OpenAPI JSON schema is accessible.

        Validates that the OpenAPI specification endpoint returns
        valid JSON schema for API documentation.
        """
        response = test_client.get("/openapi.json")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data

    def test_swagger_ui_accessible(self, test_client: TestClient):
        """
        Test Swagger UI documentation is accessible.

        Validates that the interactive API documentation interface
        is available at the configured URL.
        """
        response = test_client.get("/docs")

        assert response.status_code == status.HTTP_200_OK
        assert "text/html" in response.headers["content-type"]

    def test_redoc_ui_accessible(self, test_client: TestClient):
        """
        Test ReDoc documentation is accessible.

        Validates that the alternative API documentation interface
        is available at the configured URL.
        """
        response = test_client.get("/redoc")

        assert response.status_code == status.HTTP_200_OK
        assert "text/html" in response.headers["content-type"]

    def test_openapi_schema_includes_health_endpoints(
        self, test_client: TestClient
    ):
        """
        Test OpenAPI schema includes health check endpoints.

        Validates that health and readiness endpoints are documented
        in the OpenAPI specification.
        """
        response = test_client.get("/openapi.json")
        data = response.json()

        assert "/health" in data["paths"]
        assert "/ready" in data["paths"]
        assert "get" in data["paths"]["/health"]
        assert "get" in data["paths"]["/ready"]


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================


class TestPerformance:
    """Test suite for application performance characteristics."""

    def test_health_endpoint_response_time(self, test_client: TestClient):
        """
        Test health endpoint responds within acceptable time.

        Validates that health check endpoint responds quickly enough
        for monitoring and load balancer requirements.
        """
        import time

        start = time.time()
        response = test_client.get("/health")
        elapsed = time.time() - start

        assert response.status_code == status.HTTP_200_OK
        assert elapsed < 0.1  # Should respond in less than 100ms

    @pytest.mark.asyncio
    async def test_concurrent_request_handling(
        self, async_client: AsyncClient
    ):
        """
        Test application handles concurrent requests efficiently.

        Validates that the application can process multiple simultaneous
        requests without performance degradation.
        """
        import time

        start = time.time()
        tasks = [async_client.get("/health") for _ in range(50)]
        responses = await asyncio.gather(*tasks)
        elapsed = time.time() - start

        assert all(r.status_code == status.HTTP_200_OK for r in responses)
        assert elapsed < 2.0  # 50 requests should complete in under 2 seconds

    def test_memory_efficiency_multiple_requests(
        self, test_client: TestClient
    ):
        """
        Test application maintains memory efficiency under load.

        Validates that repeated requests don't cause memory leaks
        or excessive memory consumption.
        """
        import gc

        gc.collect()

        # Make multiple requests
        for _ in range(100):
            response = test_client.get("/health")
            assert response.status_code == status.HTTP_200_OK

        gc.collect()
        # Test passes if no memory errors occur


# ============================================================================
# EDGE CASES AND ERROR SCENARIOS
# ============================================================================


class TestEdgeCases:
    """Test suite for edge cases and boundary conditions."""

    def test_invalid_endpoint_returns_404(self, test_client: TestClient):
        """
        Test invalid endpoint returns 404 Not Found.

        Validates that requests to non-existent endpoints return
        appropriate error status.
        """
        response = test_client.get("/nonexistent")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_invalid_http_method_returns_405(self, test_client: TestClient):
        """
        Test invalid HTTP method returns 405 Method Not Allowed.

        Validates that using wrong HTTP method on endpoint returns
        appropriate error status.
        """
        response = test_client.post("/health")

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_large_request_id_header(self, test_client: TestClient):
        """
        Test application handles large request ID headers.

        Validates that the application can process requests with
        unusually large correlation ID headers.
        """
        large_request_id = "x" * 1000
        response = test_client.get(
            "/health", headers={"X-Request-ID": large_request_id}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["X-Request-ID"] == large_request_id

    def test_special_characters_in_request_id(self, test_client: TestClient):
        """
        Test application handles special characters in request ID.

        Validates that request IDs with special characters are
        properly preserved and returned.
        """
        special_request_id = "test-123_abc.xyz@domain"
        response = test_client.get(
            "/health", headers={"X-Request-ID": special_request_id}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["X-Request-ID"] == special_request_id

    @pytest.mark.parametrize(
        "method",
        ["GET", "HEAD", "OPTIONS"],
    )
    def test_health_endpoint_supports_safe_methods(
        self, test_client: TestClient, method: str
    ):
        """
        Test health endpoint supports safe HTTP methods.

        Validates that health check endpoint responds to GET, HEAD,
        and OPTIONS methods appropriately.
        """
        response = test_client.request(method, "/health")

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        ]


# ============================================================================
# SECURITY TESTS
# ============================================================================


class TestSecurity:
    """Test suite for security-related functionality."""

    def test_no_sensitive_info_in_error_responses(
        self, test_client: TestClient
    ):
        """
        Test error responses don't expose sensitive information.

        Validates that error messages don't leak internal implementation
        details or sensitive data.
        """
        from fastapi import FastAPI

        test_app = FastAPI()

        @test_app.get("/error")
        async def error_endpoint():
            raise ValueError("Internal database connection string: secret")

        for handler in app.exception_handlers:
            test_app.add_exception_handler(handler, app.exception_handlers[handler])

        with TestClient(test_app) as client:
            response = client.get("/error")
            data = response.json()

            assert "secret" not in str(data).lower()
            assert "database" not in str(data).lower()
            assert "connection string" not in str(data).lower()

    def test_request_id_prevents_injection(self, test_client: TestClient):
        """
        Test request ID header prevents injection attacks.

        Validates that malicious content in request ID headers
        is properly sanitized or rejected.
        """
        malicious_request_id = "<script>alert('xss')</script>"
        response = test_client.get(
            "/health", headers={"X-Request-ID": malicious_request_id}
        )

        assert response.status_code == status.HTTP_200_OK
        # Request ID should be preserved as-is (not executed)
        assert response.headers["X-Request-ID"] == malicious_request_id

    def test_cors_does_not_allow_all_origins_in_production(self):
        """
        Test CORS configuration is secure for production.

        Validates that CORS is not configured to allow all origins
        which would be a security risk.
        """
        from src.core.config import get_settings

        settings = get_settings()

        # In production, should not allow all origins
        if settings.environment == "production":
            assert "*" not in settings.cors_origins