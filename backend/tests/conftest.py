"""
Pytest configuration and shared test fixtures.

This module provides pytest configuration, fixtures, and test utilities
for the FastAPI backend application. It includes test client setup,
async support configuration, and shared fixtures for testing.
"""

import asyncio
from typing import AsyncGenerator, Generator

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.main import app


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Create an event loop for the test session.

    Provides a single event loop for all async tests in the session,
    ensuring proper cleanup after all tests complete.

    Yields:
        asyncio.AbstractEventLoop: Event loop for async test execution
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def test_client() -> Generator[TestClient, None, None]:
    """
    Create a synchronous test client for FastAPI application.

    Provides a TestClient instance for making synchronous HTTP requests
    to the FastAPI application during tests. The client is properly
    cleaned up after each test.

    Yields:
        TestClient: Synchronous test client for FastAPI app

    Example:
        def test_health_endpoint(test_client):
            response = test_client.get("/health")
            assert response.status_code == 200
    """
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="function")
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Create an asynchronous test client for FastAPI application.

    Provides an AsyncClient instance for making asynchronous HTTP requests
    to the FastAPI application during async tests. The client is properly
    cleaned up after each test.

    Yields:
        AsyncClient: Asynchronous test client for FastAPI app

    Example:
        async def test_health_endpoint_async(async_client):
            response = await async_client.get("/health")
            assert response.status_code == 200
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture(scope="function")
def mock_logger(monkeypatch):
    """
    Mock logger for testing log output.

    Provides a mock logger that captures log calls for verification
    in tests without actually writing to log files or console.

    Args:
        monkeypatch: Pytest monkeypatch fixture

    Returns:
        Mock logger instance with captured calls

    Example:
        def test_logging(mock_logger):
            logger.info("test message")
            assert "test message" in mock_logger.messages
    """
    from unittest.mock import MagicMock

    mock = MagicMock()
    monkeypatch.setattr("src.core.logging.logger", mock)
    return mock


@pytest.fixture(scope="function")
def test_config(monkeypatch):
    """
    Override configuration for testing.

    Provides test-specific configuration values, ensuring tests
    run with predictable settings and don't affect production config.

    Args:
        monkeypatch: Pytest monkeypatch fixture

    Returns:
        dict: Test configuration values

    Example:
        def test_with_config(test_config):
            assert test_config["environment"] == "test"
    """
    test_settings = {
        "environment": "test",
        "debug": True,
        "log_level": "DEBUG",
    }

    for key, value in test_settings.items():
        monkeypatch.setenv(key.upper(), str(value))

    return test_settings


@pytest.fixture(autouse=True)
def reset_app_state():
    """
    Reset application state between tests.

    Automatically runs before each test to ensure clean state.
    This prevents test pollution and ensures test isolation.

    Yields:
        None: Control returns to test after setup
    """
    yield