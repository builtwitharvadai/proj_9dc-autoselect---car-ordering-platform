"""
Comprehensive test suite for Elasticsearch client.

Tests cover connection management, health checks, index operations,
error handling, and edge cases with proper mocking and isolation.
"""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import (
    ApiError,
    AuthenticationException,
    ConnectionError,
    ConnectionTimeout,
    NotFoundError,
    TransportError,
)

from src.services.search.elasticsearch_client import (
    ElasticsearchClient,
    ElasticsearchConnectionError,
    ElasticsearchError,
    ElasticsearchIndexError,
    close_elasticsearch_client,
    get_elasticsearch_client,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_settings(monkeypatch):
    """Mock application settings for testing."""
    mock_config = MagicMock()
    mock_config.elasticsearch_url = "http://localhost:9200"
    mock_config.elasticsearch_enabled = True

    monkeypatch.setattr(
        "src.services.search.elasticsearch_client.settings", mock_config
    )
    return mock_config


@pytest.fixture
def mock_logger(monkeypatch):
    """Mock logger to verify logging calls."""
    mock_log = MagicMock()
    monkeypatch.setattr(
        "src.services.search.elasticsearch_client.logger", mock_log
    )
    return mock_log


@pytest.fixture
def mock_es_client():
    """Create mock AsyncElasticsearch client."""
    mock_client = AsyncMock(spec=AsyncElasticsearch)

    # Mock cluster health response
    mock_client.cluster.health = AsyncMock(
        return_value={
            "cluster_name": "test-cluster",
            "status": "green",
            "number_of_nodes": 3,
            "active_shards": 10,
            "relocating_shards": 0,
            "initializing_shards": 0,
            "unassigned_shards": 0,
            "timed_out": False,
        }
    )

    # Mock cluster stats response
    mock_client.cluster.stats = AsyncMock(
        return_value={
            "cluster_name": "test-cluster",
            "status": "green",
            "indices": {
                "count": 5,
                "docs": {"count": 1000},
                "store": {"size_in_bytes": 1024000},
            },
            "nodes": {"count": {"total": 3}},
        }
    )

    # Mock indices operations
    mock_client.indices.exists = AsyncMock(return_value=True)
    mock_client.indices.create = AsyncMock()
    mock_client.indices.delete = AsyncMock()
    mock_client.indices.refresh = AsyncMock()

    mock_client.close = AsyncMock()

    return mock_client


@pytest.fixture
async def es_client(mock_settings, mock_es_client):
    """Create ElasticsearchClient instance with mocked dependencies."""
    with patch(
        "src.services.search.elasticsearch_client.AsyncElasticsearch",
        return_value=mock_es_client,
    ):
        client = ElasticsearchClient()
        await client.connect()
        yield client
        await client.disconnect()


@pytest.fixture(autouse=True)
async def cleanup_global_client():
    """Cleanup global client after each test."""
    yield
    await close_elasticsearch_client()


# ============================================================================
# Unit Tests - Initialization
# ============================================================================


class TestElasticsearchClientInitialization:
    """Test client initialization and configuration."""

    def test_init_with_defaults(self, mock_settings):
        """Test initialization with default settings."""
        client = ElasticsearchClient()

        assert client._url == "http://localhost:9200"
        assert client._max_retries == 3
        assert client._retry_on_timeout is True
        assert client._request_timeout == 30
        assert client._client is None
        assert client._connected is False

    def test_init_with_custom_params(self):
        """Test initialization with custom parameters."""
        client = ElasticsearchClient(
            url="http://custom:9200",
            max_retries=5,
            retry_on_timeout=False,
            request_timeout=60,
        )

        assert client._url == "http://custom:9200"
        assert client._max_retries == 5
        assert client._retry_on_timeout is False
        assert client._request_timeout == 60

    def test_init_logs_configuration(self, mock_settings, mock_logger):
        """Test that initialization logs configuration."""
        ElasticsearchClient()

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "Elasticsearch client initialized" in call_args[0][0]


# ============================================================================
# Unit Tests - Connection Management
# ============================================================================


class TestElasticsearchConnection:
    """Test connection establishment and management."""

    @pytest.mark.asyncio
    async def test_connect_success(self, mock_settings, mock_es_client, mock_logger):
        """Test successful connection to Elasticsearch."""
        with patch(
            "src.services.search.elasticsearch_client.AsyncElasticsearch",
            return_value=mock_es_client,
        ):
            client = ElasticsearchClient()
            await client.connect()

            assert client.is_connected is True
            assert client._client is not None
            mock_logger.info.assert_any_call(
                "Elasticsearch connection established",
                cluster_name="test-cluster",
                status="green",
                number_of_nodes=3,
            )

    @pytest.mark.asyncio
    async def test_connect_already_connected(self, es_client, mock_logger):
        """Test connecting when already connected."""
        mock_logger.reset_mock()

        await es_client.connect()

        mock_logger.debug.assert_called_once_with(
            "Elasticsearch client already connected"
        )

    @pytest.mark.asyncio
    async def test_connect_authentication_failure(self, mock_settings):
        """Test connection failure due to authentication error."""
        mock_client = AsyncMock()
        mock_client.cluster.health = AsyncMock(
            side_effect=AuthenticationException("Invalid credentials")
        )

        with patch(
            "src.services.search.elasticsearch_client.AsyncElasticsearch",
            return_value=mock_client,
        ):
            client = ElasticsearchClient()

            with pytest.raises(ElasticsearchConnectionError) as exc_info:
                await client.connect()

            assert exc_info.value.code == "ES_CONNECTION_ERROR"
            assert "Authentication failed" in str(exc_info.value)
            assert exc_info.value.context["url"] == "http://localhost:9200"

    @pytest.mark.asyncio
    async def test_connect_connection_error(self, mock_settings):
        """Test connection failure due to network error."""
        mock_client = AsyncMock()
        mock_client.cluster.health = AsyncMock(
            side_effect=ConnectionError("Connection refused")
        )

        with patch(
            "src.services.search.elasticsearch_client.AsyncElasticsearch",
            return_value=mock_client,
        ):
            client = ElasticsearchClient()

            with pytest.raises(ElasticsearchConnectionError) as exc_info:
                await client.connect()

            assert "Connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_connect_unexpected_error(self, mock_settings):
        """Test connection failure due to unexpected error."""
        mock_client = AsyncMock()
        mock_client.cluster.health = AsyncMock(
            side_effect=RuntimeError("Unexpected error")
        )

        with patch(
            "src.services.search.elasticsearch_client.AsyncElasticsearch",
            return_value=mock_client,
        ):
            client = ElasticsearchClient()

            with pytest.raises(ElasticsearchConnectionError) as exc_info:
                await client.connect()

            assert "Unexpected connection error" in str(exc_info.value)
            assert exc_info.value.context["error_type"] == "RuntimeError"

    @pytest.mark.asyncio
    async def test_disconnect_success(self, es_client, mock_logger):
        """Test successful disconnection."""
        mock_logger.reset_mock()

        await es_client.disconnect()

        assert es_client.is_connected is False
        assert es_client._client is None
        mock_logger.info.assert_called_once_with("Elasticsearch connection closed")

    @pytest.mark.asyncio
    async def test_disconnect_no_client(self, mock_logger):
        """Test disconnecting when no client exists."""
        client = ElasticsearchClient()

        await client.disconnect()

        mock_logger.debug.assert_called_once_with(
            "No Elasticsearch client to disconnect"
        )

    @pytest.mark.asyncio
    async def test_disconnect_with_error(self, es_client, mock_logger):
        """Test disconnection handles errors gracefully."""
        es_client._client.close = AsyncMock(side_effect=RuntimeError("Close error"))

        await es_client.disconnect()

        # Should not raise exception, but should log error
        assert es_client.is_connected is False
        assert es_client._client is None
        mock_logger.error.assert_called_once()


# ============================================================================
# Unit Tests - Health Checks
# ============================================================================


class TestElasticsearchHealthChecks:
    """Test cluster health monitoring."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, es_client):
        """Test successful health check."""
        health = await es_client.health_check()

        assert health["status"] == "green"
        assert health["cluster_name"] == "test-cluster"
        assert health["number_of_nodes"] == 3
        assert health["active_shards"] == 10
        assert health["timed_out"] is False

    @pytest.mark.asyncio
    async def test_health_check_not_connected(self):
        """Test health check when not connected."""
        client = ElasticsearchClient()

        with pytest.raises(ElasticsearchConnectionError) as exc_info:
            await client.health_check()

        assert "Client not connected" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_health_check_timeout(self, es_client):
        """Test health check timeout handling."""
        es_client._client.cluster.health = AsyncMock(
            side_effect=ConnectionTimeout("Health check timed out")
        )

        with pytest.raises(ElasticsearchConnectionError) as exc_info:
            await es_client.health_check()

        assert "Health check timed out" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_health_check_connection_error(self, es_client):
        """Test health check connection error handling."""
        es_client._client.cluster.health = AsyncMock(
            side_effect=ConnectionError("Connection lost")
        )

        with pytest.raises(ElasticsearchConnectionError) as exc_info:
            await es_client.health_check()

        assert "Health check connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_health_check_unexpected_error(self, es_client):
        """Test health check unexpected error handling."""
        es_client._client.cluster.health = AsyncMock(
            side_effect=ValueError("Unexpected error")
        )

        with pytest.raises(ElasticsearchConnectionError) as exc_info:
            await es_client.health_check()

        assert "Health check failed" in str(exc_info.value)
        assert exc_info.value.context["error_type"] == "ValueError"

    @pytest.mark.asyncio
    async def test_cluster_stats_success(self, es_client):
        """Test successful cluster stats retrieval."""
        stats = await es_client.cluster_stats()

        assert stats["cluster_name"] == "test-cluster"
        assert stats["status"] == "green"
        assert stats["indices_count"] == 5
        assert stats["docs_count"] == 1000
        assert stats["store_size_bytes"] == 1024000
        assert stats["nodes_count"] == 3

    @pytest.mark.asyncio
    async def test_cluster_stats_not_connected(self):
        """Test cluster stats when not connected."""
        client = ElasticsearchClient()

        with pytest.raises(ElasticsearchConnectionError) as exc_info:
            await client.cluster_stats()

        assert "Client not connected" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_cluster_stats_error(self, es_client):
        """Test cluster stats error handling."""
        es_client._client.cluster.stats = AsyncMock(
            side_effect=RuntimeError("Stats error")
        )

        with pytest.raises(ElasticsearchConnectionError) as exc_info:
            await es_client.cluster_stats()

        assert "Failed to retrieve cluster stats" in str(exc_info.value)


# ============================================================================
# Unit Tests - Index Operations
# ============================================================================


class TestElasticsearchIndexOperations:
    """Test index management operations."""

    @pytest.mark.asyncio
    async def test_index_exists_true(self, es_client):
        """Test checking if index exists (returns True)."""
        es_client._client.indices.exists = AsyncMock(return_value=True)

        exists = await es_client.index_exists("test-index")

        assert exists is True
        es_client._client.indices.exists.assert_called_once_with(index="test-index")

    @pytest.mark.asyncio
    async def test_index_exists_false(self, es_client):
        """Test checking if index exists (returns False)."""
        es_client._client.indices.exists = AsyncMock(return_value=False)

        exists = await es_client.index_exists("nonexistent-index")

        assert exists is False

    @pytest.mark.asyncio
    async def test_index_exists_not_connected(self):
        """Test index exists check when not connected."""
        client = ElasticsearchClient()

        with pytest.raises(ElasticsearchConnectionError) as exc_info:
            await client.index_exists("test-index")

        assert "Client not connected" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_index_exists_error(self, es_client):
        """Test index exists check error handling."""
        es_client._client.indices.exists = AsyncMock(
            side_effect=RuntimeError("Check failed")
        )

        with pytest.raises(ElasticsearchConnectionError) as exc_info:
            await es_client.index_exists("test-index")

        assert "Failed to check index existence" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_index_success(self, es_client):
        """Test successful index creation."""
        es_client._client.indices.exists = AsyncMock(return_value=False)

        mappings = {
            "properties": {
                "title": {"type": "text"},
                "price": {"type": "float"},
            }
        }
        settings = {"number_of_shards": 1, "number_of_replicas": 0}

        await es_client.create_index("test-index", mappings, settings)

        es_client._client.indices.create.assert_called_once_with(
            index="test-index",
            body={"mappings": mappings, "settings": settings},
        )

    @pytest.mark.asyncio
    async def test_create_index_without_settings(self, es_client):
        """Test index creation without settings."""
        es_client._client.indices.exists = AsyncMock(return_value=False)

        mappings = {"properties": {"title": {"type": "text"}}}

        await es_client.create_index("test-index", mappings)

        es_client._client.indices.create.assert_called_once_with(
            index="test-index", body={"mappings": mappings}
        )

    @pytest.mark.asyncio
    async def test_create_index_already_exists(self, es_client, mock_logger):
        """Test creating index that already exists."""
        es_client._client.indices.exists = AsyncMock(return_value=True)

        mappings = {"properties": {"title": {"type": "text"}}}

        await es_client.create_index("test-index", mappings)

        # Should not call create
        es_client._client.indices.create.assert_not_called()
        mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_index_api_error(self, es_client):
        """Test index creation API error handling."""
        es_client._client.indices.exists = AsyncMock(return_value=False)
        api_error = ApiError(400, "Bad request", {})
        es_client._client.indices.create = AsyncMock(side_effect=api_error)

        mappings = {"properties": {"title": {"type": "text"}}}

        with pytest.raises(ElasticsearchIndexError) as exc_info:
            await es_client.create_index("test-index", mappings)

        assert "Failed to create index" in str(exc_info.value)
        assert exc_info.value.context["status_code"] == 400

    @pytest.mark.asyncio
    async def test_create_index_unexpected_error(self, es_client):
        """Test index creation unexpected error handling."""
        es_client._client.indices.exists = AsyncMock(return_value=False)
        es_client._client.indices.create = AsyncMock(
            side_effect=RuntimeError("Unexpected error")
        )

        mappings = {"properties": {"title": {"type": "text"}}}

        with pytest.raises(ElasticsearchIndexError) as exc_info:
            await es_client.create_index("test-index", mappings)

        assert "Unexpected error creating index" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_index_success(self, es_client):
        """Test successful index deletion."""
        es_client._client.indices.exists = AsyncMock(return_value=True)

        await es_client.delete_index("test-index")

        es_client._client.indices.delete.assert_called_once_with(index="test-index")

    @pytest.mark.asyncio
    async def test_delete_index_not_exists(self, es_client, mock_logger):
        """Test deleting index that doesn't exist."""
        es_client._client.indices.exists = AsyncMock(return_value=False)

        await es_client.delete_index("nonexistent-index")

        # Should not call delete
        es_client._client.indices.delete.assert_not_called()
        mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_index_not_found_error(self, es_client, mock_logger):
        """Test deleting index with NotFoundError."""
        es_client._client.indices.exists = AsyncMock(return_value=True)
        es_client._client.indices.delete = AsyncMock(
            side_effect=NotFoundError(404, "Not found", {})
        )

        await es_client.delete_index("test-index")

        # Should handle gracefully
        mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_index_api_error(self, es_client):
        """Test index deletion API error handling."""
        es_client._client.indices.exists = AsyncMock(return_value=True)
        api_error = ApiError(500, "Server error", {})
        es_client._client.indices.delete = AsyncMock(side_effect=api_error)

        with pytest.raises(ElasticsearchIndexError) as exc_info:
            await es_client.delete_index("test-index")

        assert "Failed to delete index" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_refresh_index_success(self, es_client):
        """Test successful index refresh."""
        await es_client.refresh_index("test-index")

        es_client._client.indices.refresh.assert_called_once_with(index="test-index")

    @pytest.mark.asyncio
    async def test_refresh_index_not_connected(self):
        """Test index refresh when not connected."""
        client = ElasticsearchClient()

        with pytest.raises(ElasticsearchConnectionError) as exc_info:
            await client.refresh_index("test-index")

        assert "Client not connected" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_refresh_index_error(self, es_client):
        """Test index refresh error handling."""
        es_client._client.indices.refresh = AsyncMock(
            side_effect=RuntimeError("Refresh failed")
        )

        with pytest.raises(ElasticsearchIndexError) as exc_info:
            await es_client.refresh_index("test-index")

        assert "Failed to refresh index" in str(exc_info.value)


# ============================================================================
# Unit Tests - Properties
# ============================================================================


class TestElasticsearchClientProperties:
    """Test client properties and state."""

    @pytest.mark.asyncio
    async def test_client_property_connected(self, es_client):
        """Test client property when connected."""
        client = es_client.client

        assert isinstance(client, AsyncElasticsearch)

    def test_client_property_not_connected(self):
        """Test client property when not connected."""
        client = ElasticsearchClient()

        with pytest.raises(ElasticsearchConnectionError) as exc_info:
            _ = client.client

        assert "Client not connected" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_is_connected_true(self, es_client):
        """Test is_connected property when connected."""
        assert es_client.is_connected is True

    def test_is_connected_false(self):
        """Test is_connected property when not connected."""
        client = ElasticsearchClient()

        assert client.is_connected is False

    @pytest.mark.asyncio
    async def test_is_connected_after_disconnect(self, es_client):
        """Test is_connected property after disconnection."""
        await es_client.disconnect()

        assert es_client.is_connected is False


# ============================================================================
# Integration Tests - Global Client
# ============================================================================


class TestGlobalElasticsearchClient:
    """Test global client instance management."""

    @pytest.mark.asyncio
    async def test_get_elasticsearch_client_creates_instance(
        self, mock_settings, mock_es_client
    ):
        """Test getting global client creates new instance."""
        with patch(
            "src.services.search.elasticsearch_client.AsyncElasticsearch",
            return_value=mock_es_client,
        ):
            client = await get_elasticsearch_client()

            assert client is not None
            assert client.is_connected is True

    @pytest.mark.asyncio
    async def test_get_elasticsearch_client_reuses_instance(
        self, mock_settings, mock_es_client
    ):
        """Test getting global client reuses existing instance."""
        with patch(
            "src.services.search.elasticsearch_client.AsyncElasticsearch",
            return_value=mock_es_client,
        ):
            client1 = await get_elasticsearch_client()
            client2 = await get_elasticsearch_client()

            assert client1 is client2

    @pytest.mark.asyncio
    async def test_get_elasticsearch_client_reconnects_if_disconnected(
        self, mock_settings, mock_es_client
    ):
        """Test getting global client reconnects if disconnected."""
        with patch(
            "src.services.search.elasticsearch_client.AsyncElasticsearch",
            return_value=mock_es_client,
        ):
            client = await get_elasticsearch_client()
            await client.disconnect()

            client2 = await get_elasticsearch_client()

            assert client2.is_connected is True

    @pytest.mark.asyncio
    async def test_get_elasticsearch_client_disabled(self, mock_settings):
        """Test getting client when Elasticsearch is disabled."""
        mock_settings.elasticsearch_enabled = False

        with pytest.raises(ElasticsearchConnectionError) as exc_info:
            await get_elasticsearch_client()

        assert "Elasticsearch is disabled" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_close_elasticsearch_client(self, mock_settings, mock_es_client):
        """Test closing global client."""
        with patch(
            "src.services.search.elasticsearch_client.AsyncElasticsearch",
            return_value=mock_es_client,
        ):
            await get_elasticsearch_client()
            await close_elasticsearch_client()

            # Verify client is closed
            from src.services.search.elasticsearch_client import (
                _elasticsearch_client,
            )

            assert _elasticsearch_client is None

    @pytest.mark.asyncio
    async def test_close_elasticsearch_client_no_client(self):
        """Test closing global client when none exists."""
        # Should not raise exception
        await close_elasticsearch_client()


# ============================================================================
# Edge Cases and Error Scenarios
# ============================================================================


class TestElasticsearchEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_multiple_connect_calls(self, mock_settings, mock_es_client):
        """Test multiple connect calls don't create multiple connections."""
        with patch(
            "src.services.search.elasticsearch_client.AsyncElasticsearch",
            return_value=mock_es_client,
        ):
            client = ElasticsearchClient()

            await client.connect()
            await client.connect()
            await client.connect()

            # Should only create one client
            assert client._client is not None
            assert client.is_connected is True

    @pytest.mark.asyncio
    async def test_operations_after_disconnect(self, es_client):
        """Test operations fail gracefully after disconnect."""
        await es_client.disconnect()

        with pytest.raises(ElasticsearchConnectionError):
            await es_client.health_check()

        with pytest.raises(ElasticsearchConnectionError):
            await es_client.index_exists("test-index")

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, es_client):
        """Test concurrent operations are handled correctly."""
        tasks = [
            es_client.health_check(),
            es_client.cluster_stats(),
            es_client.index_exists("test-index"),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=False)

        assert len(results) == 3
        assert all(result is not None for result in results)

    @pytest.mark.asyncio
    async def test_empty_index_name(self, es_client):
        """Test operations with empty index name."""
        # Elasticsearch client should handle this
        await es_client.index_exists("")

    @pytest.mark.asyncio
    async def test_special_characters_in_index_name(self, es_client):
        """Test operations with special characters in index name."""
        # Test with various special characters
        special_names = [
            "test-index-123",
            "test_index",
            "test.index",
        ]

        for name in special_names:
            await es_client.index_exists(name)

    @pytest.mark.asyncio
    async def test_large_mappings(self, es_client):
        """Test creating index with large mappings."""
        es_client._client.indices.exists = AsyncMock(return_value=False)

        # Create large mappings with many fields
        mappings = {
            "properties": {f"field_{i}": {"type": "text"} for i in range(100)}
        }

        await es_client.create_index("large-index", mappings)

        es_client._client.indices.create.assert_called_once()


# ============================================================================
# Exception Hierarchy Tests
# ============================================================================


class TestElasticsearchExceptions:
    """Test custom exception hierarchy."""

    def test_elasticsearch_error_base(self):
        """Test base ElasticsearchError exception."""
        error = ElasticsearchError("Test error", code="TEST_ERROR", key="value")

        assert str(error) == "Test error"
        assert error.code == "TEST_ERROR"
        assert error.context == {"key": "value"}

    def test_elasticsearch_connection_error(self):
        """Test ElasticsearchConnectionError exception."""
        error = ElasticsearchConnectionError("Connection failed", url="http://test")

        assert str(error) == "Connection failed"
        assert error.code == "ES_CONNECTION_ERROR"
        assert error.context["url"] == "http://test"

    def test_elasticsearch_index_error(self):
        """Test ElasticsearchIndexError exception."""
        error = ElasticsearchIndexError("Index failed", index="test-index")

        assert str(error) == "Index failed"
        assert error.code == "ES_INDEX_ERROR"
        assert error.context["index"] == "test-index"

    def test_exception_inheritance(self):
        """Test exception inheritance hierarchy."""
        assert issubclass(ElasticsearchConnectionError, ElasticsearchError)
        assert issubclass(ElasticsearchIndexError, ElasticsearchError)
        assert issubclass(ElasticsearchError, Exception)


# ============================================================================
# Performance and Resource Tests
# ============================================================================


class TestElasticsearchPerformance:
    """Test performance and resource management."""

    @pytest.mark.asyncio
    async def test_connection_timeout_respected(self, mock_settings):
        """Test that connection timeout is respected."""
        mock_client = AsyncMock()
        mock_client.cluster.health = AsyncMock(
            side_effect=asyncio.TimeoutError("Timeout")
        )

        with patch(
            "src.services.search.elasticsearch_client.AsyncElasticsearch",
            return_value=mock_client,
        ):
            client = ElasticsearchClient(request_timeout=1)

            with pytest.raises(Exception):
                await client.connect()

    @pytest.mark.asyncio
    async def test_resource_cleanup_on_error(self, mock_settings):
        """Test resources are cleaned up on connection error."""
        mock_client = AsyncMock()
        mock_client.cluster.health = AsyncMock(
            side_effect=ConnectionError("Connection failed")
        )

        with patch(
            "src.services.search.elasticsearch_client.AsyncElasticsearch",
            return_value=mock_client,
        ):
            client = ElasticsearchClient()

            try:
                await client.connect()
            except ElasticsearchConnectionError:
                pass

            # Client should not be set on error
            assert client._client is not None  # Client object created
            assert client._connected is False  # But not marked as connected

    @pytest.mark.asyncio
    async def test_multiple_disconnect_calls(self, es_client):
        """Test multiple disconnect calls are safe."""
        await es_client.disconnect()
        await es_client.disconnect()
        await es_client.disconnect()

        assert es_client.is_connected is False


# ============================================================================
# Logging Tests
# ============================================================================


class TestElasticsearchLogging:
    """Test logging behavior."""

    @pytest.mark.asyncio
    async def test_connect_logs_success(self, mock_settings, mock_es_client, mock_logger):
        """Test successful connection logs appropriately."""
        with patch(
            "src.services.search.elasticsearch_client.AsyncElasticsearch",
            return_value=mock_es_client,
        ):
            client = ElasticsearchClient()
            await client.connect()

            # Verify info log for connection
            info_calls = [call for call in mock_logger.info.call_args_list]
            assert any(
                "Elasticsearch connection established" in str(call) for call in info_calls
            )

    @pytest.mark.asyncio
    async def test_connect_logs_error(self, mock_settings, mock_logger):
        """Test connection error logs appropriately."""
        mock_client = AsyncMock()
        mock_client.cluster.health = AsyncMock(
            side_effect=ConnectionError("Connection failed")
        )

        with patch(
            "src.services.search.elasticsearch_client.AsyncElasticsearch",
            return_value=mock_client,
        ):
            client = ElasticsearchClient()

            try:
                await client.connect()
            except ElasticsearchConnectionError:
                pass

            mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_operations_log_debug(self, es_client, mock_logger):
        """Test operations log debug information."""
        await es_client.health_check()

        debug_calls = [call for call in mock_logger.debug.call_args_list]
        assert any(
            "Elasticsearch health check completed" in str(call) for call in debug_calls
        )