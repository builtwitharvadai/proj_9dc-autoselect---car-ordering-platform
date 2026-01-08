"""
Elasticsearch client for vehicle search functionality.

This module provides async Elasticsearch client with connection pooling,
health checks, and comprehensive error handling for vehicle search operations.
"""

import asyncio
import logging
from typing import Any, Optional

from elasticsearch import AsyncElasticsearch, ConnectionError, TransportError
from elasticsearch.exceptions import (
    ApiError,
    AuthenticationException,
    ConnectionTimeout,
    NotFoundError,
)

from src.core.config import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class ElasticsearchError(Exception):
    """Base exception for Elasticsearch operations."""

    def __init__(self, message: str, code: str = "ES_ERROR", **context):
        super().__init__(message)
        self.code = code
        self.context = context


class ElasticsearchConnectionError(ElasticsearchError):
    """Exception raised when Elasticsearch connection fails."""

    def __init__(self, message: str, **context):
        super().__init__(message, code="ES_CONNECTION_ERROR", **context)


class ElasticsearchIndexError(ElasticsearchError):
    """Exception raised for index operation failures."""

    def __init__(self, message: str, **context):
        super().__init__(message, code="ES_INDEX_ERROR", **context)


class ElasticsearchClient:
    """
    Async Elasticsearch client with connection management and health checks.

    Provides high-level interface for Elasticsearch operations with proper
    error handling, connection pooling, and cluster health monitoring.
    """

    def __init__(
        self,
        url: Optional[str] = None,
        max_retries: int = 3,
        retry_on_timeout: bool = True,
        request_timeout: int = 30,
    ):
        """
        Initialize Elasticsearch client.

        Args:
            url: Elasticsearch connection URL (defaults to settings)
            max_retries: Maximum number of retry attempts
            retry_on_timeout: Whether to retry on timeout errors
            request_timeout: Request timeout in seconds
        """
        self._url = url or settings.elasticsearch_url
        self._max_retries = max_retries
        self._retry_on_timeout = retry_on_timeout
        self._request_timeout = request_timeout
        self._client: Optional[AsyncElasticsearch] = None
        self._connected = False

        logger.info(
            "Elasticsearch client initialized",
            url=self._url,
            max_retries=max_retries,
            request_timeout=request_timeout,
        )

    async def connect(self) -> None:
        """
        Establish connection to Elasticsearch cluster.

        Raises:
            ElasticsearchConnectionError: If connection fails
        """
        if self._connected and self._client:
            logger.debug("Elasticsearch client already connected")
            return

        try:
            self._client = AsyncElasticsearch(
                hosts=[self._url],
                max_retries=self._max_retries,
                retry_on_timeout=self._retry_on_timeout,
                request_timeout=self._request_timeout,
            )

            # Verify connection with cluster health check
            health = await self._client.cluster.health()

            self._connected = True

            logger.info(
                "Elasticsearch connection established",
                cluster_name=health.get("cluster_name"),
                status=health.get("status"),
                number_of_nodes=health.get("number_of_nodes"),
            )

        except AuthenticationException as e:
            logger.error(
                "Elasticsearch authentication failed",
                url=self._url,
                error=str(e),
            )
            raise ElasticsearchConnectionError(
                "Authentication failed", url=self._url, error=str(e)
            ) from e

        except ConnectionError as e:
            logger.error(
                "Failed to connect to Elasticsearch",
                url=self._url,
                error=str(e),
            )
            raise ElasticsearchConnectionError(
                "Connection failed", url=self._url, error=str(e)
            ) from e

        except Exception as e:
            logger.error(
                "Unexpected error connecting to Elasticsearch",
                url=self._url,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ElasticsearchConnectionError(
                "Unexpected connection error",
                url=self._url,
                error=str(e),
                error_type=type(e).__name__,
            ) from e

    async def disconnect(self) -> None:
        """Close Elasticsearch connection and cleanup resources."""
        if not self._client:
            logger.debug("No Elasticsearch client to disconnect")
            return

        try:
            await self._client.close()
            self._connected = False
            self._client = None

            logger.info("Elasticsearch connection closed")

        except Exception as e:
            logger.error(
                "Error closing Elasticsearch connection",
                error=str(e),
                error_type=type(e).__name__,
            )
            # Don't raise exception on disconnect
            self._connected = False
            self._client = None

    async def health_check(self) -> dict[str, Any]:
        """
        Check Elasticsearch cluster health.

        Returns:
            Dictionary containing cluster health information

        Raises:
            ElasticsearchConnectionError: If health check fails
        """
        if not self._client:
            raise ElasticsearchConnectionError("Client not connected")

        try:
            health = await self._client.cluster.health()

            logger.debug(
                "Elasticsearch health check completed",
                status=health.get("status"),
                active_shards=health.get("active_shards"),
            )

            return {
                "status": health.get("status"),
                "cluster_name": health.get("cluster_name"),
                "number_of_nodes": health.get("number_of_nodes"),
                "active_shards": health.get("active_shards"),
                "relocating_shards": health.get("relocating_shards"),
                "initializing_shards": health.get("initializing_shards"),
                "unassigned_shards": health.get("unassigned_shards"),
                "timed_out": health.get("timed_out", False),
            }

        except ConnectionTimeout as e:
            logger.error("Elasticsearch health check timed out", error=str(e))
            raise ElasticsearchConnectionError(
                "Health check timed out", error=str(e)
            ) from e

        except ConnectionError as e:
            logger.error("Elasticsearch health check connection failed", error=str(e))
            raise ElasticsearchConnectionError(
                "Health check connection failed", error=str(e)
            ) from e

        except Exception as e:
            logger.error(
                "Elasticsearch health check failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ElasticsearchConnectionError(
                "Health check failed",
                error=str(e),
                error_type=type(e).__name__,
            ) from e

    async def cluster_stats(self) -> dict[str, Any]:
        """
        Get Elasticsearch cluster statistics.

        Returns:
            Dictionary containing cluster statistics

        Raises:
            ElasticsearchConnectionError: If stats retrieval fails
        """
        if not self._client:
            raise ElasticsearchConnectionError("Client not connected")

        try:
            stats = await self._client.cluster.stats()

            logger.debug(
                "Elasticsearch cluster stats retrieved",
                indices_count=stats.get("indices", {}).get("count"),
                docs_count=stats.get("indices", {}).get("docs", {}).get("count"),
            )

            return {
                "cluster_name": stats.get("cluster_name"),
                "status": stats.get("status"),
                "indices_count": stats.get("indices", {}).get("count"),
                "docs_count": stats.get("indices", {}).get("docs", {}).get("count"),
                "store_size_bytes": stats.get("indices", {})
                .get("store", {})
                .get("size_in_bytes"),
                "nodes_count": stats.get("nodes", {}).get("count", {}).get("total"),
            }

        except Exception as e:
            logger.error(
                "Failed to retrieve cluster stats",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ElasticsearchConnectionError(
                "Failed to retrieve cluster stats",
                error=str(e),
                error_type=type(e).__name__,
            ) from e

    async def index_exists(self, index_name: str) -> bool:
        """
        Check if index exists.

        Args:
            index_name: Name of the index to check

        Returns:
            True if index exists, False otherwise

        Raises:
            ElasticsearchConnectionError: If check fails
        """
        if not self._client:
            raise ElasticsearchConnectionError("Client not connected")

        try:
            exists = await self._client.indices.exists(index=index_name)

            logger.debug("Index existence check", index=index_name, exists=exists)

            return exists

        except Exception as e:
            logger.error(
                "Failed to check index existence",
                index=index_name,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ElasticsearchConnectionError(
                "Failed to check index existence",
                index=index_name,
                error=str(e),
                error_type=type(e).__name__,
            ) from e

    async def create_index(
        self, index_name: str, mappings: dict[str, Any], settings: Optional[dict[str, Any]] = None
    ) -> None:
        """
        Create index with mappings and settings.

        Args:
            index_name: Name of the index to create
            mappings: Index mappings configuration
            settings: Optional index settings

        Raises:
            ElasticsearchIndexError: If index creation fails
        """
        if not self._client:
            raise ElasticsearchConnectionError("Client not connected")

        try:
            # Check if index already exists
            if await self.index_exists(index_name):
                logger.warning("Index already exists", index=index_name)
                return

            body: dict[str, Any] = {"mappings": mappings}
            if settings:
                body["settings"] = settings

            await self._client.indices.create(index=index_name, body=body)

            logger.info(
                "Index created successfully",
                index=index_name,
                mappings_properties_count=len(mappings.get("properties", {})),
            )

        except ApiError as e:
            logger.error(
                "Failed to create index",
                index=index_name,
                error=str(e),
                status_code=e.status_code,
            )
            raise ElasticsearchIndexError(
                "Failed to create index",
                index=index_name,
                error=str(e),
                status_code=e.status_code,
            ) from e

        except Exception as e:
            logger.error(
                "Unexpected error creating index",
                index=index_name,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ElasticsearchIndexError(
                "Unexpected error creating index",
                index=index_name,
                error=str(e),
                error_type=type(e).__name__,
            ) from e

    async def delete_index(self, index_name: str) -> None:
        """
        Delete index.

        Args:
            index_name: Name of the index to delete

        Raises:
            ElasticsearchIndexError: If index deletion fails
        """
        if not self._client:
            raise ElasticsearchConnectionError("Client not connected")

        try:
            # Check if index exists before deleting
            if not await self.index_exists(index_name):
                logger.warning("Index does not exist", index=index_name)
                return

            await self._client.indices.delete(index=index_name)

            logger.info("Index deleted successfully", index=index_name)

        except NotFoundError:
            logger.warning("Index not found during deletion", index=index_name)

        except ApiError as e:
            logger.error(
                "Failed to delete index",
                index=index_name,
                error=str(e),
                status_code=e.status_code,
            )
            raise ElasticsearchIndexError(
                "Failed to delete index",
                index=index_name,
                error=str(e),
                status_code=e.status_code,
            ) from e

        except Exception as e:
            logger.error(
                "Unexpected error deleting index",
                index=index_name,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ElasticsearchIndexError(
                "Unexpected error deleting index",
                index=index_name,
                error=str(e),
                error_type=type(e).__name__,
            ) from e

    async def refresh_index(self, index_name: str) -> None:
        """
        Refresh index to make recent changes searchable.

        Args:
            index_name: Name of the index to refresh

        Raises:
            ElasticsearchIndexError: If refresh fails
        """
        if not self._client:
            raise ElasticsearchConnectionError("Client not connected")

        try:
            await self._client.indices.refresh(index=index_name)

            logger.debug("Index refreshed", index=index_name)

        except Exception as e:
            logger.error(
                "Failed to refresh index",
                index=index_name,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ElasticsearchIndexError(
                "Failed to refresh index",
                index=index_name,
                error=str(e),
                error_type=type(e).__name__,
            ) from e

    @property
    def client(self) -> AsyncElasticsearch:
        """
        Get underlying Elasticsearch client.

        Returns:
            AsyncElasticsearch client instance

        Raises:
            ElasticsearchConnectionError: If client not connected
        """
        if not self._client:
            raise ElasticsearchConnectionError("Client not connected")
        return self._client

    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._connected and self._client is not None


# Global client instance
_elasticsearch_client: Optional[ElasticsearchClient] = None


async def get_elasticsearch_client() -> ElasticsearchClient:
    """
    Get or create global Elasticsearch client instance.

    Returns:
        ElasticsearchClient instance

    Raises:
        ElasticsearchConnectionError: If connection fails
    """
    global _elasticsearch_client

    if not settings.elasticsearch_enabled:
        raise ElasticsearchConnectionError(
            "Elasticsearch is disabled in configuration"
        )

    if _elasticsearch_client is None:
        _elasticsearch_client = ElasticsearchClient()
        await _elasticsearch_client.connect()

    elif not _elasticsearch_client.is_connected:
        await _elasticsearch_client.connect()

    return _elasticsearch_client


async def close_elasticsearch_client() -> None:
    """Close global Elasticsearch client connection."""
    global _elasticsearch_client

    if _elasticsearch_client:
        await _elasticsearch_client.disconnect()
        _elasticsearch_client = None

        logger.info("Global Elasticsearch client closed")