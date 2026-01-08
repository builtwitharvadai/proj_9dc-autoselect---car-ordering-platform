"""
Vehicle search service with query building and result processing.

This module implements VehicleSearchService with comprehensive search capabilities
including full-text search, filtered search, faceted search, and fuzzy matching.
Provides query builders for different search types with relevance scoring and
result processing with proper error handling and logging.
"""

import logging
from decimal import Decimal
from typing import Any, Optional

from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import ApiError, NotFoundError

from src.core.logging import get_logger
from src.schemas.vehicles import VehicleListResponse, VehicleResponse, VehicleSearchRequest
from src.services.search.elasticsearch_client import (
    ElasticsearchClient,
    ElasticsearchError,
)
from src.services.search.vehicle_index import VehicleIndex

logger = get_logger(__name__)


class SearchError(Exception):
    """Base exception for search operations."""

    def __init__(self, message: str, code: str = "SEARCH_ERROR", **context):
        super().__init__(message)
        self.code = code
        self.context = context


class SearchQueryError(SearchError):
    """Exception raised for invalid search queries."""

    def __init__(self, message: str, **context):
        super().__init__(message, code="INVALID_QUERY", **context)


class SearchExecutionError(SearchError):
    """Exception raised when search execution fails."""

    def __init__(self, message: str, **context):
        super().__init__(message, code="SEARCH_EXECUTION_FAILED", **context)


class VehicleSearchService:
    """
    Vehicle search service with advanced query building and result processing.

    Provides comprehensive search functionality including full-text search,
    filtered search, faceted search, and fuzzy matching with relevance scoring.
    """

    def __init__(self, client: ElasticsearchClient, index: VehicleIndex):
        """
        Initialize vehicle search service.

        Args:
            client: Elasticsearch client instance
            index: Vehicle index manager
        """
        self._client = client
        self._index = index

        logger.info(
            "Vehicle search service initialized",
            index_name=index.index_name,
        )

    async def search(
        self, search_request: VehicleSearchRequest
    ) -> VehicleListResponse:
        """
        Execute vehicle search with filters and pagination.

        Args:
            search_request: Search request with filters and pagination

        Returns:
            Paginated search results with vehicles

        Raises:
            SearchQueryError: If search query is invalid
            SearchExecutionError: If search execution fails
        """
        try:
            # Build search query
            query = self._build_search_query(search_request)

            # Calculate pagination
            from_offset = (search_request.page - 1) * search_request.page_size

            # Build sort configuration
            sort = self._build_sort_config(
                search_request.sort_by, search_request.sort_order
            )

            # Execute search
            response = await self._client.client.search(
                index=self._index.index_name,
                query=query,
                from_=from_offset,
                size=search_request.page_size,
                sort=sort,
                track_total_hits=True,
            )

            # Process results
            total = response["hits"]["total"]["value"]
            hits = response["hits"]["hits"]

            vehicles = [self._process_search_hit(hit) for hit in hits]

            # Calculate pagination metadata
            total_pages = (
                (total + search_request.page_size - 1) // search_request.page_size
                if total > 0
                else 0
            )

            logger.info(
                "Search completed successfully",
                total_results=total,
                page=search_request.page,
                page_size=search_request.page_size,
                query_filters=self._get_active_filters(search_request),
            )

            return VehicleListResponse(
                items=vehicles,
                total=total,
                page=search_request.page,
                page_size=search_request.page_size,
                total_pages=total_pages,
            )

        except ApiError as e:
            logger.error(
                "Search execution failed",
                error=str(e),
                status_code=e.status_code,
                search_request=search_request.model_dump(),
            )
            raise SearchExecutionError(
                "Failed to execute search",
                error=str(e),
                status_code=e.status_code,
            ) from e

        except Exception as e:
            logger.error(
                "Unexpected error during search",
                error=str(e),
                error_type=type(e).__name__,
                search_request=search_request.model_dump(),
            )
            raise SearchExecutionError(
                "Unexpected search error",
                error=str(e),
                error_type=type(e).__name__,
            ) from e

    async def faceted_search(
        self, search_request: VehicleSearchRequest
    ) -> dict[str, Any]:
        """
        Execute faceted search with aggregations for filters.

        Args:
            search_request: Search request with filters

        Returns:
            Dictionary with search results and facet counts

        Raises:
            SearchExecutionError: If faceted search fails
        """
        try:
            # Build search query
            query = self._build_search_query(search_request)

            # Build aggregations for facets
            aggregations = self._build_facet_aggregations()

            # Calculate pagination
            from_offset = (search_request.page - 1) * search_request.page_size

            # Build sort configuration
            sort = self._build_sort_config(
                search_request.sort_by, search_request.sort_order
            )

            # Execute search with aggregations
            response = await self._client.client.search(
                index=self._index.index_name,
                query=query,
                aggs=aggregations,
                from_=from_offset,
                size=search_request.page_size,
                sort=sort,
                track_total_hits=True,
            )

            # Process results
            total = response["hits"]["total"]["value"]
            hits = response["hits"]["hits"]
            aggs = response.get("aggregations", {})

            vehicles = [self._process_search_hit(hit) for hit in hits]

            # Process facets
            facets = self._process_facets(aggs)

            # Calculate pagination metadata
            total_pages = (
                (total + search_request.page_size - 1) // search_request.page_size
                if total > 0
                else 0
            )

            logger.info(
                "Faceted search completed",
                total_results=total,
                facet_counts=len(facets),
                page=search_request.page,
            )

            return {
                "results": VehicleListResponse(
                    items=vehicles,
                    total=total,
                    page=search_request.page,
                    page_size=search_request.page_size,
                    total_pages=total_pages,
                ),
                "facets": facets,
            }

        except Exception as e:
            logger.error(
                "Faceted search failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise SearchExecutionError(
                "Faceted search failed",
                error=str(e),
                error_type=type(e).__name__,
            ) from e

    async def fuzzy_search(
        self, query: str, max_results: int = 10, fuzziness: str = "AUTO"
    ) -> list[VehicleResponse]:
        """
        Execute fuzzy search for make/model with typo tolerance.

        Args:
            query: Search query string
            max_results: Maximum number of results to return
            fuzziness: Fuzziness level (AUTO, 0, 1, 2)

        Returns:
            List of matching vehicles with relevance scores

        Raises:
            SearchQueryError: If query is invalid
            SearchExecutionError: If fuzzy search fails
        """
        if not query or len(query.strip()) < 2:
            raise SearchQueryError(
                "Query must be at least 2 characters",
                query=query,
            )

        try:
            # Build fuzzy query
            fuzzy_query = {
                "bool": {
                    "should": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": ["make^3", "model^2", "full_name"],
                                "fuzziness": fuzziness,
                                "prefix_length": 1,
                                "max_expansions": 50,
                            }
                        },
                        {
                            "match_phrase_prefix": {
                                "full_name": {
                                    "query": query,
                                    "boost": 2,
                                }
                            }
                        },
                    ],
                    "minimum_should_match": 1,
                    "filter": [{"term": {"is_available": True}}],
                }
            }

            # Execute search
            response = await self._client.client.search(
                index=self._index.index_name,
                query=fuzzy_query,
                size=max_results,
                track_total_hits=True,
            )

            # Process results
            hits = response["hits"]["hits"]
            vehicles = [self._process_search_hit(hit) for hit in hits]

            logger.info(
                "Fuzzy search completed",
                query=query,
                results_count=len(vehicles),
                fuzziness=fuzziness,
            )

            return vehicles

        except Exception as e:
            logger.error(
                "Fuzzy search failed",
                query=query,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise SearchExecutionError(
                "Fuzzy search failed",
                query=query,
                error=str(e),
                error_type=type(e).__name__,
            ) from e

    async def suggest(self, prefix: str, field: str = "make") -> list[str]:
        """
        Get search suggestions for autocomplete.

        Args:
            prefix: Prefix to search for
            field: Field to get suggestions from (make or model)

        Returns:
            List of suggestions

        Raises:
            SearchQueryError: If prefix is invalid
            SearchExecutionError: If suggestion search fails
        """
        if not prefix or len(prefix.strip()) < 2:
            raise SearchQueryError(
                "Prefix must be at least 2 characters",
                prefix=prefix,
            )

        if field not in ["make", "model"]:
            raise SearchQueryError(
                "Field must be 'make' or 'model'",
                field=field,
            )

        try:
            # Build suggestion query
            suggest_query = {
                f"{field}_suggest": {
                    "prefix": prefix,
                    "completion": {
                        "field": f"{field}.suggest",
                        "size": 10,
                        "skip_duplicates": True,
                    },
                }
            }

            # Execute suggestion search
            response = await self._client.client.search(
                index=self._index.index_name,
                suggest=suggest_query,
                size=0,
            )

            # Process suggestions
            suggestions = []
            suggest_results = response.get("suggest", {}).get(f"{field}_suggest", [])

            for result in suggest_results:
                for option in result.get("options", []):
                    text = option.get("text")
                    if text and text not in suggestions:
                        suggestions.append(text)

            logger.debug(
                "Suggestions retrieved",
                prefix=prefix,
                field=field,
                count=len(suggestions),
            )

            return suggestions

        except Exception as e:
            logger.error(
                "Suggestion search failed",
                prefix=prefix,
                field=field,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise SearchExecutionError(
                "Suggestion search failed",
                prefix=prefix,
                field=field,
                error=str(e),
                error_type=type(e).__name__,
            ) from e

    def _build_search_query(self, search_request: VehicleSearchRequest) -> dict[str, Any]:
        """
        Build Elasticsearch query from search request.

        Args:
            search_request: Search request with filters

        Returns:
            Elasticsearch query DSL
        """
        must_clauses = []
        filter_clauses = []

        # Full-text search query
        if search_request.search_query:
            must_clauses.append(
                {
                    "multi_match": {
                        "query": search_request.search_query,
                        "fields": [
                            "make^3",
                            "model^2",
                            "full_name^2",
                            "display_name",
                            "trim",
                        ],
                        "type": "best_fields",
                        "fuzziness": "AUTO",
                    }
                }
            )

        # Exact match filters
        if search_request.make:
            filter_clauses.append(
                {"term": {"make.keyword": search_request.make}}
            )

        if search_request.model:
            filter_clauses.append(
                {"term": {"model.keyword": search_request.model}}
            )

        if search_request.body_style:
            filter_clauses.append(
                {"term": {"body_style": search_request.body_style}}
            )

        if search_request.fuel_type:
            filter_clauses.append(
                {"term": {"fuel_type": search_request.fuel_type}}
            )

        if search_request.drivetrain:
            filter_clauses.append(
                {"term": {"drivetrain": search_request.drivetrain}}
            )

        if search_request.transmission:
            filter_clauses.append(
                {"term": {"transmission": search_request.transmission}}
            )

        # Range filters
        if search_request.year_min is not None or search_request.year_max is not None:
            year_range = {}
            if search_request.year_min is not None:
                year_range["gte"] = search_request.year_min
            if search_request.year_max is not None:
                year_range["lte"] = search_request.year_max
            filter_clauses.append({"range": {"year": year_range}})

        if search_request.price_min is not None or search_request.price_max is not None:
            price_range = {}
            if search_request.price_min is not None:
                price_range["gte"] = float(search_request.price_min)
            if search_request.price_max is not None:
                price_range["lte"] = float(search_request.price_max)
            filter_clauses.append({"range": {"base_price": price_range}})

        if (
            search_request.seating_capacity_min is not None
            or search_request.seating_capacity_max is not None
        ):
            seating_range = {}
            if search_request.seating_capacity_min is not None:
                seating_range["gte"] = search_request.seating_capacity_min
            if search_request.seating_capacity_max is not None:
                seating_range["lte"] = search_request.seating_capacity_max
            filter_clauses.append({"range": {"seating_capacity": seating_range}})

        # Availability filter
        if search_request.is_active is not None:
            filter_clauses.append(
                {"term": {"is_available": search_request.is_active}}
            )

        # Custom attributes filters
        if search_request.custom_attributes:
            for key, value in search_request.custom_attributes.items():
                filter_clauses.append(
                    {"term": {f"specifications.{key}": value}}
                )

        # Build final query
        if must_clauses or filter_clauses:
            query = {"bool": {}}
            if must_clauses:
                query["bool"]["must"] = must_clauses
            if filter_clauses:
                query["bool"]["filter"] = filter_clauses
            return query

        # Match all if no filters
        return {"match_all": {}}

    def _build_sort_config(
        self, sort_by: Optional[str], sort_order: str
    ) -> list[dict[str, Any]]:
        """
        Build sort configuration for search query.

        Args:
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)

        Returns:
            Elasticsearch sort configuration
        """
        if not sort_by:
            return [{"_score": {"order": "desc"}}]

        # Map sort fields to Elasticsearch fields
        sort_field_mapping = {
            "make": "make.keyword",
            "model": "model.keyword",
            "year": "year",
            "price": "base_price",
            "created_at": "created_at",
        }

        es_field = sort_field_mapping.get(sort_by, sort_by)

        return [
            {es_field: {"order": sort_order}},
            {"_score": {"order": "desc"}},
        ]

    def _build_facet_aggregations(self) -> dict[str, Any]:
        """
        Build aggregations for faceted search.

        Returns:
            Elasticsearch aggregations configuration
        """
        return {
            "makes": {
                "terms": {
                    "field": "make.keyword",
                    "size": 50,
                }
            },
            "models": {
                "terms": {
                    "field": "model.keyword",
                    "size": 100,
                }
            },
            "body_styles": {
                "terms": {
                    "field": "body_style",
                    "size": 20,
                }
            },
            "fuel_types": {
                "terms": {
                    "field": "fuel_type",
                    "size": 10,
                }
            },
            "drivetrains": {
                "terms": {
                    "field": "drivetrain",
                    "size": 10,
                }
            },
            "year_range": {
                "stats": {
                    "field": "year",
                }
            },
            "price_range": {
                "stats": {
                    "field": "base_price",
                }
            },
            "price_histogram": {
                "histogram": {
                    "field": "base_price",
                    "interval": 5000,
                }
            },
        }

    def _process_facets(self, aggregations: dict[str, Any]) -> dict[str, Any]:
        """
        Process aggregation results into facet structure.

        Args:
            aggregations: Raw aggregation results from Elasticsearch

        Returns:
            Processed facets with counts and ranges
        """
        facets = {}

        # Process term aggregations
        for facet_name in ["makes", "models", "body_styles", "fuel_types", "drivetrains"]:
            if facet_name in aggregations:
                buckets = aggregations[facet_name].get("buckets", [])
                facets[facet_name] = [
                    {"value": bucket["key"], "count": bucket["doc_count"]}
                    for bucket in buckets
                ]

        # Process stats aggregations
        for range_name in ["year_range", "price_range"]:
            if range_name in aggregations:
                stats = aggregations[range_name]
                facets[range_name] = {
                    "min": stats.get("min"),
                    "max": stats.get("max"),
                    "avg": stats.get("avg"),
                    "count": stats.get("count"),
                }

        # Process histogram
        if "price_histogram" in aggregations:
            buckets = aggregations["price_histogram"].get("buckets", [])
            facets["price_histogram"] = [
                {"range": bucket["key"], "count": bucket["doc_count"]}
                for bucket in buckets
                if bucket["doc_count"] > 0
            ]

        return facets

    def _process_search_hit(self, hit: dict[str, Any]) -> VehicleResponse:
        """
        Process Elasticsearch hit into VehicleResponse.

        Args:
            hit: Elasticsearch search hit

        Returns:
            VehicleResponse object
        """
        source = hit["_source"]
        score = hit.get("_score")

        # Add relevance score to response
        if score is not None:
            source["_relevance_score"] = score

        return VehicleResponse(**source)

    def _get_active_filters(self, search_request: VehicleSearchRequest) -> dict[str, Any]:
        """
        Get active filters from search request for logging.

        Args:
            search_request: Search request

        Returns:
            Dictionary of active filters
        """
        filters = {}

        if search_request.search_query:
            filters["search_query"] = search_request.search_query
        if search_request.make:
            filters["make"] = search_request.make
        if search_request.model:
            filters["model"] = search_request.model
        if search_request.year_min or search_request.year_max:
            filters["year_range"] = {
                "min": search_request.year_min,
                "max": search_request.year_max,
            }
        if search_request.price_min or search_request.price_max:
            filters["price_range"] = {
                "min": search_request.price_min,
                "max": search_request.price_max,
            }
        if search_request.body_style:
            filters["body_style"] = search_request.body_style
        if search_request.fuel_type:
            filters["fuel_type"] = search_request.fuel_type

        return filters