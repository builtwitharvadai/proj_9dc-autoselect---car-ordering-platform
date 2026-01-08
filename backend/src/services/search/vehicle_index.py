"""
Vehicle search index management and mapping definition.

This module defines Elasticsearch mapping for vehicle documents with proper field types
for search, filtering, and aggregations. Includes methods for index creation, deletion,
and document management with comprehensive error handling and logging.
"""

import logging
from typing import Any, Optional

from elasticsearch.exceptions import ApiError, NotFoundError

from src.core.logging import get_logger
from src.services.search.elasticsearch_client import (
    ElasticsearchClient,
    ElasticsearchIndexError,
)

logger = get_logger(__name__)


class VehicleIndexError(Exception):
    """Base exception for vehicle index operations."""

    def __init__(self, message: str, code: str = "INDEX_ERROR", **context):
        super().__init__(message)
        self.code = code
        self.context = context


class VehicleIndex:
    """
    Vehicle search index management with Elasticsearch mapping.

    Provides index lifecycle management including creation, deletion, and document
    operations with optimized mapping for vehicle search, filtering, and aggregations.
    """

    INDEX_NAME = "vehicles"
    INDEX_VERSION = "v1"

    # Elasticsearch mapping for vehicle documents
    MAPPING = {
        "properties": {
            # Vehicle identification
            "id": {
                "type": "keyword",
            },
            "vin": {
                "type": "keyword",
            },
            # Basic vehicle information with text search
            "make": {
                "type": "text",
                "fields": {
                    "keyword": {"type": "keyword"},
                    "suggest": {
                        "type": "completion",
                        "analyzer": "simple",
                    },
                },
                "analyzer": "standard",
            },
            "model": {
                "type": "text",
                "fields": {
                    "keyword": {"type": "keyword"},
                    "suggest": {
                        "type": "completion",
                        "analyzer": "simple",
                    },
                },
                "analyzer": "standard",
            },
            "year": {
                "type": "integer",
            },
            "trim": {
                "type": "text",
                "fields": {
                    "keyword": {"type": "keyword"},
                },
                "analyzer": "standard",
            },
            # Physical characteristics for filtering
            "body_style": {
                "type": "keyword",
            },
            "exterior_color": {
                "type": "keyword",
            },
            "interior_color": {
                "type": "keyword",
            },
            # Powertrain specifications
            "fuel_type": {
                "type": "keyword",
            },
            "transmission": {
                "type": "keyword",
            },
            "drivetrain": {
                "type": "keyword",
            },
            "engine": {
                "type": "text",
                "fields": {
                    "keyword": {"type": "keyword"},
                },
            },
            "horsepower": {
                "type": "integer",
            },
            "torque": {
                "type": "integer",
            },
            # Fuel economy
            "mpg_city": {
                "type": "integer",
            },
            "mpg_highway": {
                "type": "integer",
            },
            "mpg_combined": {
                "type": "integer",
            },
            # Capacity specifications
            "seating_capacity": {
                "type": "integer",
            },
            "cargo_capacity": {
                "type": "float",
            },
            "towing_capacity": {
                "type": "integer",
            },
            # Pricing for range queries
            "base_price": {
                "type": "float",
            },
            "msrp": {
                "type": "float",
            },
            "total_price": {
                "type": "float",
            },
            # Full-text search fields
            "full_name": {
                "type": "text",
                "analyzer": "standard",
            },
            "display_name": {
                "type": "text",
                "analyzer": "standard",
            },
            # Specifications as nested object for flexible search
            "specifications": {
                "type": "object",
                "enabled": True,
            },
            # Availability status
            "is_available": {
                "type": "boolean",
            },
            # Timestamps
            "created_at": {
                "type": "date",
                "format": "strict_date_optional_time||epoch_millis",
            },
            "updated_at": {
                "type": "date",
                "format": "strict_date_optional_time||epoch_millis",
            },
        }
    }

    # Index settings for performance optimization
    SETTINGS = {
        "number_of_shards": 1,
        "number_of_replicas": 1,
        "refresh_interval": "1s",
        "analysis": {
            "analyzer": {
                "vehicle_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "asciifolding", "vehicle_synonym"],
                },
            },
            "filter": {
                "vehicle_synonym": {
                    "type": "synonym",
                    "synonyms": [
                        "suv, sport utility vehicle",
                        "mpv, minivan",
                        "4wd, four wheel drive, awd, all wheel drive",
                        "fwd, front wheel drive",
                        "rwd, rear wheel drive",
                    ],
                },
            },
        },
    }

    def __init__(self, client: ElasticsearchClient):
        """
        Initialize vehicle index manager.

        Args:
            client: Elasticsearch client instance
        """
        self._client = client
        self._index_name = f"{self.INDEX_NAME}_{self.INDEX_VERSION}"

        logger.info(
            "Vehicle index manager initialized",
            index_name=self._index_name,
        )

    @property
    def index_name(self) -> str:
        """Get full index name with version."""
        return self._index_name

    async def create_index(self, delete_if_exists: bool = False) -> None:
        """
        Create vehicle search index with mapping and settings.

        Args:
            delete_if_exists: Whether to delete existing index before creation

        Raises:
            VehicleIndexError: If index creation fails
        """
        try:
            # Check if index exists
            exists = await self._client.index_exists(self._index_name)

            if exists:
                if delete_if_exists:
                    logger.warning(
                        "Deleting existing index",
                        index=self._index_name,
                    )
                    await self.delete_index()
                else:
                    logger.info(
                        "Index already exists",
                        index=self._index_name,
                    )
                    return

            # Create index with mapping and settings
            await self._client.create_index(
                index_name=self._index_name,
                mappings=self.MAPPING,
                settings=self.SETTINGS,
            )

            logger.info(
                "Vehicle index created successfully",
                index=self._index_name,
                properties_count=len(self.MAPPING["properties"]),
            )

        except ElasticsearchIndexError as e:
            logger.error(
                "Failed to create vehicle index",
                index=self._index_name,
                error=str(e),
                code=e.code,
            )
            raise VehicleIndexError(
                "Failed to create vehicle index",
                code="CREATE_INDEX_FAILED",
                index=self._index_name,
                error=str(e),
            ) from e

        except Exception as e:
            logger.error(
                "Unexpected error creating vehicle index",
                index=self._index_name,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise VehicleIndexError(
                "Unexpected error creating vehicle index",
                code="CREATE_INDEX_ERROR",
                index=self._index_name,
                error=str(e),
                error_type=type(e).__name__,
            ) from e

    async def delete_index(self) -> None:
        """
        Delete vehicle search index.

        Raises:
            VehicleIndexError: If index deletion fails
        """
        try:
            await self._client.delete_index(self._index_name)

            logger.info(
                "Vehicle index deleted successfully",
                index=self._index_name,
            )

        except ElasticsearchIndexError as e:
            logger.error(
                "Failed to delete vehicle index",
                index=self._index_name,
                error=str(e),
                code=e.code,
            )
            raise VehicleIndexError(
                "Failed to delete vehicle index",
                code="DELETE_INDEX_FAILED",
                index=self._index_name,
                error=str(e),
            ) from e

        except Exception as e:
            logger.error(
                "Unexpected error deleting vehicle index",
                index=self._index_name,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise VehicleIndexError(
                "Unexpected error deleting vehicle index",
                code="DELETE_INDEX_ERROR",
                index=self._index_name,
                error=str(e),
                error_type=type(e).__name__,
            ) from e

    async def index_exists(self) -> bool:
        """
        Check if vehicle index exists.

        Returns:
            True if index exists, False otherwise

        Raises:
            VehicleIndexError: If existence check fails
        """
        try:
            exists = await self._client.index_exists(self._index_name)

            logger.debug(
                "Vehicle index existence check",
                index=self._index_name,
                exists=exists,
            )

            return exists

        except Exception as e:
            logger.error(
                "Failed to check vehicle index existence",
                index=self._index_name,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise VehicleIndexError(
                "Failed to check vehicle index existence",
                code="INDEX_EXISTS_ERROR",
                index=self._index_name,
                error=str(e),
                error_type=type(e).__name__,
            ) from e

    async def index_document(
        self, document_id: str, document: dict[str, Any]
    ) -> None:
        """
        Index a vehicle document.

        Args:
            document_id: Unique document identifier
            document: Vehicle document data

        Raises:
            VehicleIndexError: If document indexing fails
        """
        try:
            await self._client.client.index(
                index=self._index_name,
                id=document_id,
                document=document,
            )

            logger.debug(
                "Vehicle document indexed",
                index=self._index_name,
                document_id=document_id,
            )

        except ApiError as e:
            logger.error(
                "Failed to index vehicle document",
                index=self._index_name,
                document_id=document_id,
                error=str(e),
                status_code=e.status_code,
            )
            raise VehicleIndexError(
                "Failed to index vehicle document",
                code="INDEX_DOCUMENT_FAILED",
                index=self._index_name,
                document_id=document_id,
                error=str(e),
                status_code=e.status_code,
            ) from e

        except Exception as e:
            logger.error(
                "Unexpected error indexing vehicle document",
                index=self._index_name,
                document_id=document_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise VehicleIndexError(
                "Unexpected error indexing vehicle document",
                code="INDEX_DOCUMENT_ERROR",
                index=self._index_name,
                document_id=document_id,
                error=str(e),
                error_type=type(e).__name__,
            ) from e

    async def update_document(
        self, document_id: str, partial_document: dict[str, Any]
    ) -> None:
        """
        Update a vehicle document with partial data.

        Args:
            document_id: Unique document identifier
            partial_document: Partial vehicle document data to update

        Raises:
            VehicleIndexError: If document update fails
        """
        try:
            await self._client.client.update(
                index=self._index_name,
                id=document_id,
                doc=partial_document,
            )

            logger.debug(
                "Vehicle document updated",
                index=self._index_name,
                document_id=document_id,
                fields_updated=len(partial_document),
            )

        except NotFoundError as e:
            logger.warning(
                "Vehicle document not found for update",
                index=self._index_name,
                document_id=document_id,
            )
            raise VehicleIndexError(
                "Vehicle document not found",
                code="DOCUMENT_NOT_FOUND",
                index=self._index_name,
                document_id=document_id,
            ) from e

        except ApiError as e:
            logger.error(
                "Failed to update vehicle document",
                index=self._index_name,
                document_id=document_id,
                error=str(e),
                status_code=e.status_code,
            )
            raise VehicleIndexError(
                "Failed to update vehicle document",
                code="UPDATE_DOCUMENT_FAILED",
                index=self._index_name,
                document_id=document_id,
                error=str(e),
                status_code=e.status_code,
            ) from e

        except Exception as e:
            logger.error(
                "Unexpected error updating vehicle document",
                index=self._index_name,
                document_id=document_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise VehicleIndexError(
                "Unexpected error updating vehicle document",
                code="UPDATE_DOCUMENT_ERROR",
                index=self._index_name,
                document_id=document_id,
                error=str(e),
                error_type=type(e).__name__,
            ) from e

    async def delete_document(self, document_id: str) -> None:
        """
        Delete a vehicle document from index.

        Args:
            document_id: Unique document identifier

        Raises:
            VehicleIndexError: If document deletion fails
        """
        try:
            await self._client.client.delete(
                index=self._index_name,
                id=document_id,
            )

            logger.debug(
                "Vehicle document deleted",
                index=self._index_name,
                document_id=document_id,
            )

        except NotFoundError:
            logger.warning(
                "Vehicle document not found for deletion",
                index=self._index_name,
                document_id=document_id,
            )

        except ApiError as e:
            logger.error(
                "Failed to delete vehicle document",
                index=self._index_name,
                document_id=document_id,
                error=str(e),
                status_code=e.status_code,
            )
            raise VehicleIndexError(
                "Failed to delete vehicle document",
                code="DELETE_DOCUMENT_FAILED",
                index=self._index_name,
                document_id=document_id,
                error=str(e),
                status_code=e.status_code,
            ) from e

        except Exception as e:
            logger.error(
                "Unexpected error deleting vehicle document",
                index=self._index_name,
                document_id=document_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise VehicleIndexError(
                "Unexpected error deleting vehicle document",
                code="DELETE_DOCUMENT_ERROR",
                index=self._index_name,
                document_id=document_id,
                error=str(e),
                error_type=type(e).__name__,
            ) from e

    async def bulk_index_documents(
        self, documents: list[tuple[str, dict[str, Any]]]
    ) -> dict[str, Any]:
        """
        Bulk index multiple vehicle documents.

        Args:
            documents: List of (document_id, document) tuples

        Returns:
            Dictionary with bulk operation results

        Raises:
            VehicleIndexError: If bulk indexing fails
        """
        try:
            actions = [
                {
                    "_index": self._index_name,
                    "_id": doc_id,
                    "_source": document,
                }
                for doc_id, document in documents
            ]

            from elasticsearch.helpers import async_bulk

            success, failed = await async_bulk(
                self._client.client,
                actions,
                raise_on_error=False,
            )

            logger.info(
                "Bulk index operation completed",
                index=self._index_name,
                total=len(documents),
                success=success,
                failed=len(failed) if failed else 0,
            )

            return {
                "total": len(documents),
                "success": success,
                "failed": len(failed) if failed else 0,
                "errors": failed if failed else [],
            }

        except Exception as e:
            logger.error(
                "Bulk index operation failed",
                index=self._index_name,
                total_documents=len(documents),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise VehicleIndexError(
                "Bulk index operation failed",
                code="BULK_INDEX_ERROR",
                index=self._index_name,
                total_documents=len(documents),
                error=str(e),
                error_type=type(e).__name__,
            ) from e

    async def refresh_index(self) -> None:
        """
        Refresh vehicle index to make recent changes searchable.

        Raises:
            VehicleIndexError: If refresh fails
        """
        try:
            await self._client.refresh_index(self._index_name)

            logger.debug(
                "Vehicle index refreshed",
                index=self._index_name,
            )

        except ElasticsearchIndexError as e:
            logger.error(
                "Failed to refresh vehicle index",
                index=self._index_name,
                error=str(e),
                code=e.code,
            )
            raise VehicleIndexError(
                "Failed to refresh vehicle index",
                code="REFRESH_INDEX_FAILED",
                index=self._index_name,
                error=str(e),
            ) from e

        except Exception as e:
            logger.error(
                "Unexpected error refreshing vehicle index",
                index=self._index_name,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise VehicleIndexError(
                "Unexpected error refreshing vehicle index",
                code="REFRESH_INDEX_ERROR",
                index=self._index_name,
                error=str(e),
                error_type=type(e).__name__,
            ) from e

    async def get_document(self, document_id: str) -> Optional[dict[str, Any]]:
        """
        Retrieve a vehicle document by ID.

        Args:
            document_id: Unique document identifier

        Returns:
            Vehicle document or None if not found

        Raises:
            VehicleIndexError: If document retrieval fails
        """
        try:
            response = await self._client.client.get(
                index=self._index_name,
                id=document_id,
            )

            logger.debug(
                "Vehicle document retrieved",
                index=self._index_name,
                document_id=document_id,
            )

            return response["_source"]

        except NotFoundError:
            logger.debug(
                "Vehicle document not found",
                index=self._index_name,
                document_id=document_id,
            )
            return None

        except ApiError as e:
            logger.error(
                "Failed to retrieve vehicle document",
                index=self._index_name,
                document_id=document_id,
                error=str(e),
                status_code=e.status_code,
            )
            raise VehicleIndexError(
                "Failed to retrieve vehicle document",
                code="GET_DOCUMENT_FAILED",
                index=self._index_name,
                document_id=document_id,
                error=str(e),
                status_code=e.status_code,
            ) from e

        except Exception as e:
            logger.error(
                "Unexpected error retrieving vehicle document",
                index=self._index_name,
                document_id=document_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise VehicleIndexError(
                "Unexpected error retrieving vehicle document",
                code="GET_DOCUMENT_ERROR",
                index=self._index_name,
                document_id=document_id,
                error=str(e),
                error_type=type(e).__name__,
            ) from e