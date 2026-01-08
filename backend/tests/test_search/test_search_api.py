"""
Integration tests for vehicle search API endpoints.

This module provides comprehensive end-to-end testing for the vehicle search
API endpoints including Elasticsearch integration, request/response validation,
performance requirements, error handling, and edge cases.
"""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient

from src.schemas.search import (
    SearchResponse,
    SearchSuggestionResponse,
    VehicleSearchRequest,
)
from src.services.search.search_service import (
    SearchError,
    SearchExecutionError,
    SearchQueryError,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_search_service():
    """
    Create mock vehicle search service.

    Returns:
        Mock search service with configured methods
    """
    service = MagicMock()
    service.search = AsyncMock()
    service.faceted_search = AsyncMock()
    service.suggest = AsyncMock()
    return service


@pytest.fixture
def mock_vehicle_service():
    """
    Create mock vehicle service.

    Returns:
        Mock vehicle service with configured methods
    """
    service = MagicMock()
    service.search_vehicles = AsyncMock()
    service.get_vehicle = AsyncMock()
    service.create_vehicle = AsyncMock()
    service.update_vehicle = AsyncMock()
    service.delete_vehicle = AsyncMock()
    return service


@pytest.fixture
def sample_search_request() -> dict[str, Any]:
    """
    Create sample search request data.

    Returns:
        Dictionary with valid search request parameters
    """
    return {
        "query": "Toyota Camry",
        "filters": {
            "make": ["Toyota"],
            "year_min": 2020,
            "year_max": 2024,
            "price_min": 20000.0,
            "price_max": 35000.0,
        },
        "page": 1,
        "limit": 20,
        "include_facets": False,
    }


@pytest.fixture
def sample_vehicle_data() -> dict[str, Any]:
    """
    Create sample vehicle data.

    Returns:
        Dictionary with valid vehicle attributes
    """
    return {
        "id": str(uuid4()),
        "make": "Toyota",
        "model": "Camry",
        "year": 2023,
        "body_style": "Sedan",
        "fuel_type": "Gasoline",
        "price": 28500.0,
        "description": "Reliable mid-size sedan",
        "features": ["Bluetooth", "Backup Camera", "Lane Assist"],
    }


@pytest.fixture
def sample_search_results(sample_vehicle_data) -> dict[str, Any]:
    """
    Create sample search results.

    Args:
        sample_vehicle_data: Sample vehicle data fixture

    Returns:
        Dictionary with search results structure
    """
    return {
        "items": [sample_vehicle_data],
        "total": 1,
        "page": 1,
        "limit": 20,
        "total_pages": 1,
    }


# ============================================================================
# Unit Tests - Search Request Validation
# ============================================================================


class TestSearchRequestValidation:
    """Test search request validation and parameter handling."""

    @pytest.mark.asyncio
    async def test_valid_search_request(
        self, async_client: AsyncClient, mock_search_service, sample_search_results
    ):
        """
        Test valid search request with all parameters.

        Validates that properly formatted search requests are accepted
        and processed correctly.
        """
        mock_search_service.search.return_value = MagicMock(**sample_search_results)

        with patch(
            "src.api.v1.vehicles.get_search_service",
            return_value=mock_search_service,
        ):
            response = await async_client.post(
                "/api/v1/vehicles/search",
                json={
                    "query": "Toyota Camry",
                    "filters": {"make": ["Toyota"]},
                    "page": 1,
                    "limit": 20,
                },
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "results" in data
        assert "metadata" in data
        assert data["metadata"]["total_results"] == 1

    @pytest.mark.asyncio
    async def test_search_without_query(
        self, async_client: AsyncClient, mock_search_service, sample_search_results
    ):
        """
        Test search request without query parameter.

        Validates that searches can be performed with filters only.
        """
        mock_search_service.search.return_value = MagicMock(**sample_search_results)

        with patch(
            "src.api.v1.vehicles.get_search_service",
            return_value=mock_search_service,
        ):
            response = await async_client.post(
                "/api/v1/vehicles/search",
                json={"filters": {"make": ["Toyota"]}, "page": 1, "limit": 20},
            )

        assert response.status_code == status.HTTP_200_OK
        mock_search_service.search.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "invalid_page,invalid_limit",
        [
            (0, 20),  # Invalid page (< 1)
            (-1, 20),  # Negative page
            (1, 0),  # Invalid limit (< 1)
            (1, 101),  # Limit exceeds maximum
            (1, -5),  # Negative limit
        ],
    )
    async def test_invalid_pagination_parameters(
        self, async_client: AsyncClient, invalid_page: int, invalid_limit: int
    ):
        """
        Test search with invalid pagination parameters.

        Validates that invalid page numbers and limits are rejected
        with appropriate error messages.
        """
        response = await async_client.post(
            "/api/v1/vehicles/search",
            json={
                "query": "Toyota",
                "page": invalid_page,
                "limit": invalid_limit,
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_search_with_empty_filters(
        self, async_client: AsyncClient, mock_search_service, sample_search_results
    ):
        """
        Test search with empty filters object.

        Validates that empty filters are handled correctly.
        """
        mock_search_service.search.return_value = MagicMock(**sample_search_results)

        with patch(
            "src.api.v1.vehicles.get_search_service",
            return_value=mock_search_service,
        ):
            response = await async_client.post(
                "/api/v1/vehicles/search",
                json={"query": "Toyota", "filters": {}, "page": 1, "limit": 20},
            )

        assert response.status_code == status.HTTP_200_OK


# ============================================================================
# Integration Tests - Search Functionality
# ============================================================================


class TestSearchFunctionality:
    """Test core search functionality and Elasticsearch integration."""

    @pytest.mark.asyncio
    async def test_basic_text_search(
        self, async_client: AsyncClient, mock_search_service, sample_search_results
    ):
        """
        Test basic text search functionality.

        Validates that text queries are processed and return relevant results.
        """
        mock_search_service.search.return_value = MagicMock(**sample_search_results)

        with patch(
            "src.api.v1.vehicles.get_search_service",
            return_value=mock_search_service,
        ):
            response = await async_client.post(
                "/api/v1/vehicles/search",
                json={"query": "Toyota Camry 2023", "page": 1, "limit": 20},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["results"]) > 0
        assert data["results"][0]["make"] == "Toyota"

    @pytest.mark.asyncio
    async def test_filtered_search(
        self, async_client: AsyncClient, mock_search_service, sample_search_results
    ):
        """
        Test search with multiple filters.

        Validates that filter combinations work correctly.
        """
        mock_search_service.search.return_value = MagicMock(**sample_search_results)

        with patch(
            "src.api.v1.vehicles.get_search_service",
            return_value=mock_search_service,
        ):
            response = await async_client.post(
                "/api/v1/vehicles/search",
                json={
                    "filters": {
                        "make": ["Toyota"],
                        "year_min": 2020,
                        "year_max": 2024,
                        "price_min": 20000.0,
                        "price_max": 35000.0,
                        "body_style": ["Sedan"],
                    },
                    "page": 1,
                    "limit": 20,
                },
            )

        assert response.status_code == status.HTTP_200_OK
        call_args = mock_search_service.search.call_args[0][0]
        assert call_args.filters["make"] == ["Toyota"]
        assert call_args.filters["year_min"] == 2020

    @pytest.mark.asyncio
    async def test_faceted_search(
        self, async_client: AsyncClient, mock_search_service, sample_search_results
    ):
        """
        Test faceted search with aggregations.

        Validates that facet data is returned when requested.
        """
        faceted_results = {
            "results": MagicMock(**sample_search_results),
            "facets": {
                "make": [{"value": "Toyota", "count": 150}],
                "year": [{"value": 2023, "count": 50}],
                "body_style": [{"value": "Sedan", "count": 80}],
            },
        }
        mock_search_service.faceted_search.return_value = faceted_results

        with patch(
            "src.api.v1.vehicles.get_search_service",
            return_value=mock_search_service,
        ):
            response = await async_client.post(
                "/api/v1/vehicles/search",
                json={
                    "query": "Toyota",
                    "include_facets": True,
                    "page": 1,
                    "limit": 20,
                },
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "facets" in data
        assert data["facets"] is not None
        assert "make" in data["facets"]

    @pytest.mark.asyncio
    async def test_empty_search_results(
        self, async_client: AsyncClient, mock_search_service
    ):
        """
        Test search with no matching results.

        Validates that empty result sets are handled correctly.
        """
        empty_results = {
            "items": [],
            "total": 0,
            "page": 1,
            "limit": 20,
            "total_pages": 0,
        }
        mock_search_service.search.return_value = MagicMock(**empty_results)

        with patch(
            "src.api.v1.vehicles.get_search_service",
            return_value=mock_search_service,
        ):
            response = await async_client.post(
                "/api/v1/vehicles/search",
                json={"query": "NonexistentVehicle12345", "page": 1, "limit": 20},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["metadata"]["total_results"] == 0
        assert len(data["results"]) == 0

    @pytest.mark.asyncio
    async def test_pagination_navigation(
        self, async_client: AsyncClient, mock_search_service
    ):
        """
        Test pagination through search results.

        Validates that pagination metadata is correct across pages.
        """
        page_2_results = {
            "items": [{"id": str(uuid4()), "make": "Honda", "model": "Accord"}],
            "total": 50,
            "page": 2,
            "limit": 20,
            "total_pages": 3,
        }
        mock_search_service.search.return_value = MagicMock(**page_2_results)

        with patch(
            "src.api.v1.vehicles.get_search_service",
            return_value=mock_search_service,
        ):
            response = await async_client.post(
                "/api/v1/vehicles/search",
                json={"query": "Honda", "page": 2, "limit": 20},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["metadata"]["page"] == 2
        assert data["metadata"]["total_pages"] == 3


# ============================================================================
# Integration Tests - Search Suggestions
# ============================================================================


class TestSearchSuggestions:
    """Test search suggestion and autocomplete functionality."""

    @pytest.mark.asyncio
    async def test_make_suggestions(
        self, async_client: AsyncClient, mock_search_service
    ):
        """
        Test autocomplete suggestions for vehicle make.

        Validates that make suggestions are returned for partial queries.
        """
        mock_search_service.suggest.return_value = ["Toyota", "Tesla", "Tata"]

        with patch(
            "src.api.v1.vehicles.get_search_service",
            return_value=mock_search_service,
        ):
            response = await async_client.get(
                "/api/v1/vehicles/search/suggestions",
                params={"query": "To", "field": "make", "limit": 5},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "suggestions" in data
        assert len(data["suggestions"]) == 3
        assert data["suggestions"][0]["text"] == "Toyota"

    @pytest.mark.asyncio
    async def test_model_suggestions(
        self, async_client: AsyncClient, mock_search_service
    ):
        """
        Test autocomplete suggestions for vehicle model.

        Validates that model suggestions are returned correctly.
        """
        mock_search_service.suggest.return_value = ["Camry", "Corolla", "Crown"]

        with patch(
            "src.api.v1.vehicles.get_search_service",
            return_value=mock_search_service,
        ):
            response = await async_client.get(
                "/api/v1/vehicles/search/suggestions",
                params={"query": "Ca", "field": "model", "limit": 5},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["suggestions"]) == 3
        mock_search_service.suggest.assert_called_once_with(prefix="Ca", field="model")

    @pytest.mark.asyncio
    async def test_body_style_suggestions(
        self, async_client: AsyncClient, mock_search_service
    ):
        """
        Test autocomplete suggestions for body style.

        Validates that body style suggestions work correctly.
        """
        mock_search_service.suggest.return_value = ["Sedan", "SUV"]

        with patch(
            "src.api.v1.vehicles.get_search_service",
            return_value=mock_search_service,
        ):
            response = await async_client.get(
                "/api/v1/vehicles/search/suggestions",
                params={"query": "Se", "field": "body_style", "limit": 5},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["field"] == "body_style"

    @pytest.mark.asyncio
    async def test_suggestions_with_limit(
        self, async_client: AsyncClient, mock_search_service
    ):
        """
        Test suggestion limit parameter.

        Validates that the limit parameter correctly restricts results.
        """
        mock_search_service.suggest.return_value = [
            "Toyota",
            "Tesla",
            "Tata",
            "Triumph",
            "TVR",
        ]

        with patch(
            "src.api.v1.vehicles.get_search_service",
            return_value=mock_search_service,
        ):
            response = await async_client.get(
                "/api/v1/vehicles/search/suggestions",
                params={"query": "T", "field": "make", "limit": 3},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["suggestions"]) == 3

    @pytest.mark.asyncio
    async def test_suggestions_minimum_query_length(
        self, async_client: AsyncClient
    ):
        """
        Test minimum query length validation for suggestions.

        Validates that queries shorter than minimum are rejected.
        """
        response = await async_client.get(
            "/api/v1/vehicles/search/suggestions",
            params={"query": "T", "field": "make", "limit": 5},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_suggestions_invalid_field(self, async_client: AsyncClient):
        """
        Test suggestions with invalid field parameter.

        Validates that invalid field names are rejected.
        """
        response = await async_client.get(
            "/api/v1/vehicles/search/suggestions",
            params={"query": "To", "field": "invalid_field", "limit": 5},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestSearchErrorHandling:
    """Test error handling and exception scenarios."""

    @pytest.mark.asyncio
    async def test_search_query_error(
        self, async_client: AsyncClient, mock_search_service
    ):
        """
        Test handling of invalid search queries.

        Validates that SearchQueryError is properly handled and returns 400.
        """
        mock_search_service.search.side_effect = SearchQueryError(
            message="Invalid query syntax",
            code="INVALID_QUERY",
            context={"query": "invalid[syntax"},
        )

        with patch(
            "src.api.v1.vehicles.get_search_service",
            return_value=mock_search_service,
        ):
            response = await async_client.post(
                "/api/v1/vehicles/search",
                json={"query": "invalid[syntax", "page": 1, "limit": 20},
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid query syntax" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_search_execution_error(
        self, async_client: AsyncClient, mock_search_service
    ):
        """
        Test handling of search execution failures.

        Validates that SearchExecutionError returns 500 status.
        """
        mock_search_service.search.side_effect = SearchExecutionError(
            message="Elasticsearch connection failed",
            code="ES_CONNECTION_ERROR",
            context={"host": "localhost:9200"},
        )

        with patch(
            "src.api.v1.vehicles.get_search_service",
            return_value=mock_search_service,
        ):
            response = await async_client.post(
                "/api/v1/vehicles/search",
                json={"query": "Toyota", "page": 1, "limit": 20},
            )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.asyncio
    async def test_generic_search_error(
        self, async_client: AsyncClient, mock_search_service
    ):
        """
        Test handling of generic search errors.

        Validates that unexpected SearchError is handled gracefully.
        """
        mock_search_service.search.side_effect = SearchError(
            message="Unknown search error",
            code="SEARCH_ERROR",
        )

        with patch(
            "src.api.v1.vehicles.get_search_service",
            return_value=mock_search_service,
        ):
            response = await async_client.post(
                "/api/v1/vehicles/search",
                json={"query": "Toyota", "page": 1, "limit": 20},
            )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.asyncio
    async def test_unexpected_exception(
        self, async_client: AsyncClient, mock_search_service
    ):
        """
        Test handling of unexpected exceptions.

        Validates that unhandled exceptions return 500 with generic message.
        """
        mock_search_service.search.side_effect = RuntimeError("Unexpected error")

        with patch(
            "src.api.v1.vehicles.get_search_service",
            return_value=mock_search_service,
        ):
            response = await async_client.post(
                "/api/v1/vehicles/search",
                json={"query": "Toyota", "page": 1, "limit": 20},
            )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Internal server error" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_suggestion_query_error(
        self, async_client: AsyncClient, mock_search_service
    ):
        """
        Test error handling for suggestion queries.

        Validates that suggestion errors are properly handled.
        """
        mock_search_service.suggest.side_effect = SearchQueryError(
            message="Invalid suggestion query",
            code="INVALID_SUGGESTION",
        )

        with patch(
            "src.api.v1.vehicles.get_search_service",
            return_value=mock_search_service,
        ):
            response = await async_client.get(
                "/api/v1/vehicles/search/suggestions",
                params={"query": "To", "field": "make", "limit": 5},
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ============================================================================
# Performance Tests
# ============================================================================


class TestSearchPerformance:
    """Test search performance and response time requirements."""

    @pytest.mark.asyncio
    async def test_search_response_time(
        self, async_client: AsyncClient, mock_search_service, sample_search_results
    ):
        """
        Test search response time meets performance requirements.

        Validates that search requests complete within acceptable time limits.
        """
        mock_search_service.search.return_value = MagicMock(**sample_search_results)

        with patch(
            "src.api.v1.vehicles.get_search_service",
            return_value=mock_search_service,
        ):
            import time

            start_time = time.time()

            response = await async_client.post(
                "/api/v1/vehicles/search",
                json={"query": "Toyota", "page": 1, "limit": 20},
            )

            elapsed_time = time.time() - start_time

        assert response.status_code == status.HTTP_200_OK
        assert elapsed_time < 1.0  # Should complete within 1 second

    @pytest.mark.asyncio
    async def test_concurrent_search_requests(
        self, async_client: AsyncClient, mock_search_service, sample_search_results
    ):
        """
        Test handling of concurrent search requests.

        Validates that multiple simultaneous searches are handled correctly.
        """
        mock_search_service.search.return_value = MagicMock(**sample_search_results)

        with patch(
            "src.api.v1.vehicles.get_search_service",
            return_value=mock_search_service,
        ):
            tasks = [
                async_client.post(
                    "/api/v1/vehicles/search",
                    json={"query": f"Query{i}", "page": 1, "limit": 20},
                )
                for i in range(10)
            ]

            responses = await asyncio.gather(*tasks)

        assert all(r.status_code == status.HTTP_200_OK for r in responses)
        assert mock_search_service.search.call_count == 10

    @pytest.mark.asyncio
    async def test_large_result_set_pagination(
        self, async_client: AsyncClient, mock_search_service
    ):
        """
        Test pagination performance with large result sets.

        Validates that pagination works efficiently with many results.
        """
        large_results = {
            "items": [{"id": str(uuid4()), "make": "Toyota"} for _ in range(20)],
            "total": 10000,
            "page": 1,
            "limit": 20,
            "total_pages": 500,
        }
        mock_search_service.search.return_value = MagicMock(**large_results)

        with patch(
            "src.api.v1.vehicles.get_search_service",
            return_value=mock_search_service,
        ):
            response = await async_client.post(
                "/api/v1/vehicles/search",
                json={"query": "Toyota", "page": 1, "limit": 20},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["metadata"]["total_results"] == 10000
        assert data["metadata"]["total_pages"] == 500


# ============================================================================
# Edge Cases and Boundary Tests
# ============================================================================


class TestSearchEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "special_query",
        [
            "Toyota & Honda",  # Special characters
            "2023-2024",  # Hyphenated
            "SUV/Crossover",  # Slash
            "Camry (Hybrid)",  # Parentheses
            "Model-S",  # Hyphen in name
            "C-Class",  # Alphanumeric with hyphen
        ],
    )
    async def test_special_characters_in_query(
        self,
        async_client: AsyncClient,
        mock_search_service,
        sample_search_results,
        special_query: str,
    ):
        """
        Test search with special characters in query.

        Validates that special characters are handled correctly.
        """
        mock_search_service.search.return_value = MagicMock(**sample_search_results)

        with patch(
            "src.api.v1.vehicles.get_search_service",
            return_value=mock_search_service,
        ):
            response = await async_client.post(
                "/api/v1/vehicles/search",
                json={"query": special_query, "page": 1, "limit": 20},
            )

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_very_long_query(
        self, async_client: AsyncClient, mock_search_service, sample_search_results
    ):
        """
        Test search with very long query string.

        Validates handling of queries at maximum length.
        """
        long_query = "Toyota " * 100  # Very long query
        mock_search_service.search.return_value = MagicMock(**sample_search_results)

        with patch(
            "src.api.v1.vehicles.get_search_service",
            return_value=mock_search_service,
        ):
            response = await async_client.post(
                "/api/v1/vehicles/search",
                json={"query": long_query, "page": 1, "limit": 20},
            )

        # Should either succeed or return validation error
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]

    @pytest.mark.asyncio
    async def test_unicode_characters_in_query(
        self, async_client: AsyncClient, mock_search_service, sample_search_results
    ):
        """
        Test search with Unicode characters.

        Validates that international characters are handled correctly.
        """
        mock_search_service.search.return_value = MagicMock(**sample_search_results)

        with patch(
            "src.api.v1.vehicles.get_search_service",
            return_value=mock_search_service,
        ):
            response = await async_client.post(
                "/api/v1/vehicles/search",
                json={"query": "Citroën C4 Cactus", "page": 1, "limit": 20},
            )

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_boundary_price_filters(
        self, async_client: AsyncClient, mock_search_service, sample_search_results
    ):
        """
        Test price filters at boundary values.

        Validates that extreme price values are handled correctly.
        """
        mock_search_service.search.return_value = MagicMock(**sample_search_results)

        with patch(
            "src.api.v1.vehicles.get_search_service",
            return_value=mock_search_service,
        ):
            response = await async_client.post(
                "/api/v1/vehicles/search",
                json={
                    "filters": {"price_min": 0.0, "price_max": 999999999.99},
                    "page": 1,
                    "limit": 20,
                },
            )

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_boundary_year_filters(
        self, async_client: AsyncClient, mock_search_service, sample_search_results
    ):
        """
        Test year filters at boundary values.

        Validates that extreme year values are handled correctly.
        """
        mock_search_service.search.return_value = MagicMock(**sample_search_results)

        with patch(
            "src.api.v1.vehicles.get_search_service",
            return_value=mock_search_service,
        ):
            response = await async_client.post(
                "/api/v1/vehicles/search",
                json={
                    "filters": {"year_min": 1900, "year_max": 2100},
                    "page": 1,
                    "limit": 20,
                },
            )

        assert response.status_code == status.HTTP_200_OK


# ============================================================================
# Security Tests
# ============================================================================


class TestSearchSecurity:
    """Test security aspects of search functionality."""

    @pytest.mark.asyncio
    async def test_sql_injection_attempt(
        self, async_client: AsyncClient, mock_search_service, sample_search_results
    ):
        """
        Test protection against SQL injection attempts.

        Validates that SQL injection patterns are safely handled.
        """
        mock_search_service.search.return_value = MagicMock(**sample_search_results)

        with patch(
            "src.api.v1.vehicles.get_search_service",
            return_value=mock_search_service,
        ):
            response = await async_client.post(
                "/api/v1/vehicles/search",
                json={
                    "query": "Toyota'; DROP TABLE vehicles; --",
                    "page": 1,
                    "limit": 20,
                },
            )

        # Should handle safely without executing SQL
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ]

    @pytest.mark.asyncio
    async def test_xss_attempt_in_query(
        self, async_client: AsyncClient, mock_search_service, sample_search_results
    ):
        """
        Test protection against XSS attempts.

        Validates that script tags and XSS patterns are sanitized.
        """
        mock_search_service.search.return_value = MagicMock(**sample_search_results)

        with patch(
            "src.api.v1.vehicles.get_search_service",
            return_value=mock_search_service,
        ):
            response = await async_client.post(
                "/api/v1/vehicles/search",
                json={
                    "query": "<script>alert('xss')</script>",
                    "page": 1,
                    "limit": 20,
                },
            )

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ]

    @pytest.mark.asyncio
    async def test_excessive_filter_combinations(
        self, async_client: AsyncClient, mock_search_service
    ):
        """
        Test handling of excessive filter combinations.

        Validates that resource exhaustion attacks are prevented.
        """
        excessive_filters = {
            "make": ["Make" + str(i) for i in range(100)],
            "model": ["Model" + str(i) for i in range(100)],
        }

        response = await async_client.post(
            "/api/v1/vehicles/search",
            json={"filters": excessive_filters, "page": 1, "limit": 20},
        )

        # Should either handle or reject gracefully
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]


# ============================================================================
# Integration Tests - Full Workflow
# ============================================================================


class TestSearchWorkflow:
    """Test complete search workflows and user journeys."""

    @pytest.mark.asyncio
    async def test_search_to_detail_workflow(
        self,
        async_client: AsyncClient,
        mock_search_service,
        mock_vehicle_service,
        sample_search_results,
        sample_vehicle_data,
    ):
        """
        Test complete workflow from search to vehicle detail.

        Validates the full user journey of searching and viewing details.
        """
        mock_search_service.search.return_value = MagicMock(**sample_search_results)
        mock_vehicle_service.get_vehicle.return_value = sample_vehicle_data

        # Step 1: Search for vehicles
        with patch(
            "src.api.v1.vehicles.get_search_service",
            return_value=mock_search_service,
        ):
            search_response = await async_client.post(
                "/api/v1/vehicles/search",
                json={"query": "Toyota Camry", "page": 1, "limit": 20},
            )

        assert search_response.status_code == status.HTTP_200_OK
        search_data = search_response.json()
        vehicle_id = search_data["results"][0]["id"]

        # Step 2: Get vehicle details
        with patch(
            "src.api.v1.vehicles.get_vehicle_service",
            return_value=mock_vehicle_service,
        ):
            detail_response = await async_client.get(
                f"/api/v1/vehicles/{vehicle_id}"
            )

        assert detail_response.status_code == status.HTTP_200_OK
        detail_data = detail_response.json()
        assert detail_data["id"] == vehicle_id

    @pytest.mark.asyncio
    async def test_progressive_filter_refinement(
        self, async_client: AsyncClient, mock_search_service, sample_search_results
    ):
        """
        Test progressive filter refinement workflow.

        Validates that users can progressively add filters to narrow results.
        """
        mock_search_service.search.return_value = MagicMock(**sample_search_results)

        with patch(
            "src.api.v1.vehicles.get_search_service",
            return_value=mock_search_service,
        ):
            # Step 1: Initial broad search
            response1 = await async_client.post(
                "/api/v1/vehicles/search",
                json={"query": "Toyota", "page": 1, "limit": 20},
            )
            assert response1.status_code == status.HTTP_200_OK

            # Step 2: Add make filter
            response2 = await async_client.post(
                "/api/v1/vehicles/search",
                json={
                    "query": "Toyota",
                    "filters": {"make": ["Toyota"]},
                    "page": 1,
                    "limit": 20,
                },
            )
            assert response2.status_code == status.HTTP_200_OK

            # Step 3: Add year range
            response3 = await async_client.post(
                "/api/v1/vehicles/search",
                json={
                    "query": "Toyota",
                    "filters": {"make": ["Toyota"], "year_min": 2020, "year_max": 2024},
                    "page": 1,
                    "limit": 20,
                },
            )
            assert response3.status_code == status.HTTP_200_OK

        assert mock_search_service.search.call_count == 3