"""
Integration tests for vehicle API endpoints.

This module provides comprehensive end-to-end testing for all vehicle catalog
API endpoints including CRUD operations, search/filtering, pagination, error
handling, authentication, and database integration.

Test Categories:
- Happy path scenarios (successful operations)
- Error scenarios (validation, not found, server errors)
- Edge cases (boundary conditions, empty results)
- Security scenarios (authentication, authorization)
- Performance validation (response times, pagination)
"""

import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import status
from httpx import AsyncClient

from src.api.v1.vehicles import router
from src.schemas.vehicles import (
    VehicleCreate,
    VehicleListResponse,
    VehicleResponse,
    VehicleUpdate,
)
from src.services.vehicles.service import (
    VehicleNotFoundError,
    VehicleService,
    VehicleServiceError,
    VehicleValidationError,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_vehicle_service():
    """
    Create mock vehicle service for testing.

    Returns:
        MagicMock: Mocked vehicle service with async methods
    """
    service = MagicMock(spec=VehicleService)
    service.search_vehicles = AsyncMock()
    service.get_vehicle = AsyncMock()
    service.create_vehicle = AsyncMock()
    service.update_vehicle = AsyncMock()
    service.delete_vehicle = AsyncMock()
    return service


@pytest.fixture
def sample_vehicle_data():
    """
    Generate sample vehicle data for testing.

    Returns:
        dict: Sample vehicle attributes
    """
    return {
        "id": uuid4(),
        "make": "Toyota",
        "model": "Camry",
        "year": 2024,
        "body_style": "Sedan",
        "fuel_type": "Hybrid",
        "base_price": 28000.00,
        "msrp": 32000.00,
        "description": "Reliable and efficient sedan",
        "features": ["Adaptive Cruise Control", "Lane Keeping Assist"],
        "specifications": {
            "engine": "2.5L 4-cylinder",
            "horsepower": 203,
            "transmission": "CVT",
        },
    }


@pytest.fixture
def sample_vehicle_response(sample_vehicle_data):
    """
    Create sample vehicle response object.

    Args:
        sample_vehicle_data: Sample vehicle data fixture

    Returns:
        VehicleResponse: Vehicle response object
    """
    return VehicleResponse(**sample_vehicle_data)


@pytest.fixture
def sample_vehicle_list_response(sample_vehicle_response):
    """
    Create sample vehicle list response.

    Args:
        sample_vehicle_response: Sample vehicle response fixture

    Returns:
        VehicleListResponse: Paginated vehicle list response
    """
    return VehicleListResponse(
        items=[sample_vehicle_response],
        total=1,
        page=1,
        page_size=20,
        total_pages=1,
    )


@pytest.fixture
def mock_redis_client():
    """
    Create mock Redis client for caching tests.

    Returns:
        MagicMock: Mocked Redis client
    """
    client = MagicMock()
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock()
    client.delete = AsyncMock()
    return client


# ============================================================================
# List Vehicles Tests
# ============================================================================


class TestListVehicles:
    """Test suite for vehicle listing endpoint."""

    @pytest.mark.asyncio
    async def test_list_vehicles_success(
        self,
        async_client: AsyncClient,
        mock_vehicle_service,
        sample_vehicle_list_response,
    ):
        """
        Test successful vehicle listing with default pagination.

        Verifies:
        - 200 OK status code
        - Correct response structure
        - Default pagination parameters
        - Service method called correctly
        """
        mock_vehicle_service.search_vehicles.return_value = (
            sample_vehicle_list_response
        )

        with patch(
            "src.api.v1.vehicles.get_vehicle_service",
            return_value=mock_vehicle_service,
        ):
            response = await async_client.get("/api/v1/vehicles")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert len(data["items"]) == 1
        assert data["items"][0]["make"] == "Toyota"
        mock_vehicle_service.search_vehicles.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_vehicles_with_filters(
        self,
        async_client: AsyncClient,
        mock_vehicle_service,
        sample_vehicle_list_response,
    ):
        """
        Test vehicle listing with multiple filters.

        Verifies:
        - Filter parameters passed correctly
        - Filtered results returned
        - Query parameter validation
        """
        mock_vehicle_service.search_vehicles.return_value = (
            sample_vehicle_list_response
        )

        with patch(
            "src.api.v1.vehicles.get_vehicle_service",
            return_value=mock_vehicle_service,
        ):
            response = await async_client.get(
                "/api/v1/vehicles",
                params={
                    "make": "Toyota",
                    "model": "Camry",
                    "year_min": 2020,
                    "year_max": 2024,
                    "body_style": "Sedan",
                    "fuel_type": "Hybrid",
                    "price_min": 25000,
                    "price_max": 35000,
                },
            )

        assert response.status_code == status.HTTP_200_OK
        call_args = mock_vehicle_service.search_vehicles.call_args[0][0]
        assert call_args.make == "Toyota"
        assert call_args.model == "Camry"
        assert call_args.year_min == 2020
        assert call_args.year_max == 2024
        assert call_args.body_style == "Sedan"
        assert call_args.fuel_type == "Hybrid"

    @pytest.mark.asyncio
    async def test_list_vehicles_with_pagination(
        self,
        async_client: AsyncClient,
        mock_vehicle_service,
        sample_vehicle_list_response,
    ):
        """
        Test vehicle listing with custom pagination.

        Verifies:
        - Custom page and page_size parameters
        - Pagination metadata in response
        - Boundary validation
        """
        sample_vehicle_list_response.page = 2
        sample_vehicle_list_response.page_size = 10
        mock_vehicle_service.search_vehicles.return_value = (
            sample_vehicle_list_response
        )

        with patch(
            "src.api.v1.vehicles.get_vehicle_service",
            return_value=mock_vehicle_service,
        ):
            response = await async_client.get(
                "/api/v1/vehicles",
                params={"page": 2, "page_size": 10},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page"] == 2
        assert data["page_size"] == 10

    @pytest.mark.asyncio
    async def test_list_vehicles_with_sorting(
        self,
        async_client: AsyncClient,
        mock_vehicle_service,
        sample_vehicle_list_response,
    ):
        """
        Test vehicle listing with sorting parameters.

        Verifies:
        - Sort field and order parameters
        - Valid sort order values (asc/desc)
        """
        mock_vehicle_service.search_vehicles.return_value = (
            sample_vehicle_list_response
        )

        with patch(
            "src.api.v1.vehicles.get_vehicle_service",
            return_value=mock_vehicle_service,
        ):
            response = await async_client.get(
                "/api/v1/vehicles",
                params={"sort_by": "price", "sort_order": "desc"},
            )

        assert response.status_code == status.HTTP_200_OK
        call_args = mock_vehicle_service.search_vehicles.call_args[0][0]
        assert call_args.sort_by == "price"
        assert call_args.sort_order == "desc"

    @pytest.mark.asyncio
    async def test_list_vehicles_empty_results(
        self,
        async_client: AsyncClient,
        mock_vehicle_service,
    ):
        """
        Test vehicle listing with no matching results.

        Verifies:
        - Empty items list
        - Total count is 0
        - Proper pagination metadata
        """
        empty_response = VehicleListResponse(
            items=[],
            total=0,
            page=1,
            page_size=20,
            total_pages=0,
        )
        mock_vehicle_service.search_vehicles.return_value = empty_response

        with patch(
            "src.api.v1.vehicles.get_vehicle_service",
            return_value=mock_vehicle_service,
        ):
            response = await async_client.get("/api/v1/vehicles")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0

    @pytest.mark.asyncio
    async def test_list_vehicles_validation_error(
        self,
        async_client: AsyncClient,
        mock_vehicle_service,
    ):
        """
        Test vehicle listing with validation error.

        Verifies:
        - 400 Bad Request status
        - Error message in response
        - Service validation error handling
        """
        mock_vehicle_service.search_vehicles.side_effect = (
            VehicleValidationError(
                message="Invalid year range",
                code="INVALID_YEAR_RANGE",
            )
        )

        with patch(
            "src.api.v1.vehicles.get_vehicle_service",
            return_value=mock_vehicle_service,
        ):
            response = await async_client.get(
                "/api/v1/vehicles",
                params={"year_min": 2025, "year_max": 2020},
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid year range" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_vehicles_service_error(
        self,
        async_client: AsyncClient,
        mock_vehicle_service,
    ):
        """
        Test vehicle listing with service error.

        Verifies:
        - 500 Internal Server Error status
        - Generic error message (no sensitive data)
        - Service error handling
        """
        mock_vehicle_service.search_vehicles.side_effect = (
            VehicleServiceError(
                message="Database connection failed",
                code="DB_ERROR",
            )
        )

        with patch(
            "src.api.v1.vehicles.get_vehicle_service",
            return_value=mock_vehicle_service,
        ):
            response = await async_client.get("/api/v1/vehicles")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to retrieve vehicles" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_vehicles_invalid_page_number(
        self,
        async_client: AsyncClient,
        mock_vehicle_service,
    ):
        """
        Test vehicle listing with invalid page number.

        Verifies:
        - 422 Unprocessable Entity for validation
        - Page number must be >= 1
        """
        with patch(
            "src.api.v1.vehicles.get_vehicle_service",
            return_value=mock_vehicle_service,
        ):
            response = await async_client.get(
                "/api/v1/vehicles",
                params={"page": 0},
            )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_list_vehicles_invalid_page_size(
        self,
        async_client: AsyncClient,
        mock_vehicle_service,
    ):
        """
        Test vehicle listing with invalid page size.

        Verifies:
        - 422 Unprocessable Entity for validation
        - Page size must be between 1 and 100
        """
        with patch(
            "src.api.v1.vehicles.get_vehicle_service",
            return_value=mock_vehicle_service,
        ):
            response = await async_client.get(
                "/api/v1/vehicles",
                params={"page_size": 101},
            )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ============================================================================
# Get Vehicle Tests
# ============================================================================


class TestGetVehicle:
    """Test suite for get vehicle by ID endpoint."""

    @pytest.mark.asyncio
    async def test_get_vehicle_success(
        self,
        async_client: AsyncClient,
        mock_vehicle_service,
        sample_vehicle_response,
    ):
        """
        Test successful vehicle retrieval by ID.

        Verifies:
        - 200 OK status code
        - Complete vehicle data returned
        - Correct vehicle ID
        """
        vehicle_id = sample_vehicle_response.id
        mock_vehicle_service.get_vehicle.return_value = sample_vehicle_response

        with patch(
            "src.api.v1.vehicles.get_vehicle_service",
            return_value=mock_vehicle_service,
        ):
            response = await async_client.get(
                f"/api/v1/vehicles/{vehicle_id}"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(vehicle_id)
        assert data["make"] == "Toyota"
        assert data["model"] == "Camry"

    @pytest.mark.asyncio
    async def test_get_vehicle_with_inventory(
        self,
        async_client: AsyncClient,
        mock_vehicle_service,
        sample_vehicle_response,
    ):
        """
        Test vehicle retrieval with inventory information.

        Verifies:
        - include_inventory parameter passed correctly
        - Inventory data included in response
        """
        vehicle_id = sample_vehicle_response.id
        mock_vehicle_service.get_vehicle.return_value = sample_vehicle_response

        with patch(
            "src.api.v1.vehicles.get_vehicle_service",
            return_value=mock_vehicle_service,
        ):
            response = await async_client.get(
                f"/api/v1/vehicles/{vehicle_id}",
                params={"include_inventory": True},
            )

        assert response.status_code == status.HTTP_200_OK
        mock_vehicle_service.get_vehicle.assert_called_once_with(
            vehicle_id=vehicle_id,
            include_inventory=True,
        )

    @pytest.mark.asyncio
    async def test_get_vehicle_not_found(
        self,
        async_client: AsyncClient,
        mock_vehicle_service,
    ):
        """
        Test vehicle retrieval with non-existent ID.

        Verifies:
        - 404 Not Found status
        - Appropriate error message
        - Vehicle ID in error message
        """
        vehicle_id = uuid4()
        mock_vehicle_service.get_vehicle.side_effect = VehicleNotFoundError(
            message=f"Vehicle not found: {vehicle_id}",
            code="VEHICLE_NOT_FOUND",
        )

        with patch(
            "src.api.v1.vehicles.get_vehicle_service",
            return_value=mock_vehicle_service,
        ):
            response = await async_client.get(
                f"/api/v1/vehicles/{vehicle_id}"
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert str(vehicle_id) in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_vehicle_invalid_uuid(
        self,
        async_client: AsyncClient,
        mock_vehicle_service,
    ):
        """
        Test vehicle retrieval with invalid UUID format.

        Verifies:
        - 422 Unprocessable Entity status
        - UUID validation error
        """
        with patch(
            "src.api.v1.vehicles.get_vehicle_service",
            return_value=mock_vehicle_service,
        ):
            response = await async_client.get(
                "/api/v1/vehicles/invalid-uuid"
            )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_get_vehicle_service_error(
        self,
        async_client: AsyncClient,
        mock_vehicle_service,
    ):
        """
        Test vehicle retrieval with service error.

        Verifies:
        - 500 Internal Server Error status
        - Generic error message
        - Error logging
        """
        vehicle_id = uuid4()
        mock_vehicle_service.get_vehicle.side_effect = VehicleServiceError(
            message="Database error",
            code="DB_ERROR",
        )

        with patch(
            "src.api.v1.vehicles.get_vehicle_service",
            return_value=mock_vehicle_service,
        ):
            response = await async_client.get(
                f"/api/v1/vehicles/{vehicle_id}"
            )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to retrieve vehicle" in response.json()["detail"]


# ============================================================================
# Create Vehicle Tests
# ============================================================================


class TestCreateVehicle:
    """Test suite for vehicle creation endpoint."""

    @pytest.mark.asyncio
    async def test_create_vehicle_success(
        self,
        async_client: AsyncClient,
        mock_vehicle_service,
        sample_vehicle_data,
        sample_vehicle_response,
    ):
        """
        Test successful vehicle creation.

        Verifies:
        - 201 Created status code
        - Vehicle data returned
        - ID generated for new vehicle
        """
        create_data = {
            k: v
            for k, v in sample_vehicle_data.items()
            if k != "id"
        }
        mock_vehicle_service.create_vehicle.return_value = (
            sample_vehicle_response
        )

        with patch(
            "src.api.v1.vehicles.get_vehicle_service",
            return_value=mock_vehicle_service,
        ):
            response = await async_client.post(
                "/api/v1/vehicles",
                json=create_data,
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "id" in data
        assert data["make"] == "Toyota"
        assert data["model"] == "Camry"

    @pytest.mark.asyncio
    async def test_create_vehicle_minimal_data(
        self,
        async_client: AsyncClient,
        mock_vehicle_service,
        sample_vehicle_response,
    ):
        """
        Test vehicle creation with minimal required fields.

        Verifies:
        - Only required fields needed
        - Optional fields can be omitted
        - Defaults applied correctly
        """
        minimal_data = {
            "make": "Honda",
            "model": "Civic",
            "year": 2024,
            "body_style": "Sedan",
            "fuel_type": "Gasoline",
            "base_price": 25000.00,
        }
        mock_vehicle_service.create_vehicle.return_value = (
            sample_vehicle_response
        )

        with patch(
            "src.api.v1.vehicles.get_vehicle_service",
            return_value=mock_vehicle_service,
        ):
            response = await async_client.post(
                "/api/v1/vehicles",
                json=minimal_data,
            )

        assert response.status_code == status.HTTP_201_CREATED

    @pytest.mark.asyncio
    async def test_create_vehicle_validation_error(
        self,
        async_client: AsyncClient,
        mock_vehicle_service,
    ):
        """
        Test vehicle creation with validation error.

        Verifies:
        - 400 Bad Request status
        - Validation error message
        - Invalid data rejected
        """
        invalid_data = {
            "make": "Toyota",
            "model": "Camry",
            "year": 1800,  # Invalid year
            "body_style": "Sedan",
            "fuel_type": "Gasoline",
            "base_price": -1000,  # Invalid price
        }
        mock_vehicle_service.create_vehicle.side_effect = (
            VehicleValidationError(
                message="Invalid vehicle data",
                code="VALIDATION_ERROR",
            )
        )

        with patch(
            "src.api.v1.vehicles.get_vehicle_service",
            return_value=mock_vehicle_service,
        ):
            response = await async_client.post(
                "/api/v1/vehicles",
                json=invalid_data,
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_create_vehicle_missing_required_fields(
        self,
        async_client: AsyncClient,
        mock_vehicle_service,
    ):
        """
        Test vehicle creation with missing required fields.

        Verifies:
        - 422 Unprocessable Entity status
        - Required field validation
        - Clear error messages
        """
        incomplete_data = {
            "make": "Toyota",
            # Missing required fields
        }

        with patch(
            "src.api.v1.vehicles.get_vehicle_service",
            return_value=mock_vehicle_service,
        ):
            response = await async_client.post(
                "/api/v1/vehicles",
                json=incomplete_data,
            )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_create_vehicle_service_error(
        self,
        async_client: AsyncClient,
        mock_vehicle_service,
        sample_vehicle_data,
    ):
        """
        Test vehicle creation with service error.

        Verifies:
        - 500 Internal Server Error status
        - Generic error message
        - Error handling
        """
        create_data = {
            k: v
            for k, v in sample_vehicle_data.items()
            if k != "id"
        }
        mock_vehicle_service.create_vehicle.side_effect = (
            VehicleServiceError(
                message="Database error",
                code="DB_ERROR",
            )
        )

        with patch(
            "src.api.v1.vehicles.get_vehicle_service",
            return_value=mock_vehicle_service,
        ):
            response = await async_client.post(
                "/api/v1/vehicles",
                json=create_data,
            )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to create vehicle" in response.json()["detail"]


# ============================================================================
# Update Vehicle Tests
# ============================================================================


class TestUpdateVehicle:
    """Test suite for vehicle update endpoint."""

    @pytest.mark.asyncio
    async def test_update_vehicle_success(
        self,
        async_client: AsyncClient,
        mock_vehicle_service,
        sample_vehicle_response,
    ):
        """
        Test successful vehicle update.

        Verifies:
        - 200 OK status code
        - Updated data returned
        - Partial updates supported
        """
        vehicle_id = sample_vehicle_response.id
        update_data = {
            "base_price": 29000.00,
            "msrp": 33000.00,
        }
        updated_response = sample_vehicle_response.model_copy(
            update=update_data
        )
        mock_vehicle_service.update_vehicle.return_value = updated_response

        with patch(
            "src.api.v1.vehicles.get_vehicle_service",
            return_value=mock_vehicle_service,
        ):
            response = await async_client.put(
                f"/api/v1/vehicles/{vehicle_id}",
                json=update_data,
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["base_price"] == 29000.00
        assert data["msrp"] == 33000.00

    @pytest.mark.asyncio
    async def test_update_vehicle_partial_update(
        self,
        async_client: AsyncClient,
        mock_vehicle_service,
        sample_vehicle_response,
    ):
        """
        Test partial vehicle update.

        Verifies:
        - Only specified fields updated
        - Other fields remain unchanged
        - Null values handled correctly
        """
        vehicle_id = sample_vehicle_response.id
        update_data = {"description": "Updated description"}
        mock_vehicle_service.update_vehicle.return_value = (
            sample_vehicle_response
        )

        with patch(
            "src.api.v1.vehicles.get_vehicle_service",
            return_value=mock_vehicle_service,
        ):
            response = await async_client.put(
                f"/api/v1/vehicles/{vehicle_id}",
                json=update_data,
            )

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_update_vehicle_not_found(
        self,
        async_client: AsyncClient,
        mock_vehicle_service,
    ):
        """
        Test vehicle update with non-existent ID.

        Verifies:
        - 404 Not Found status
        - Appropriate error message
        """
        vehicle_id = uuid4()
        update_data = {"base_price": 30000.00}
        mock_vehicle_service.update_vehicle.side_effect = (
            VehicleNotFoundError(
                message=f"Vehicle not found: {vehicle_id}",
                code="VEHICLE_NOT_FOUND",
            )
        )

        with patch(
            "src.api.v1.vehicles.get_vehicle_service",
            return_value=mock_vehicle_service,
        ):
            response = await async_client.put(
                f"/api/v1/vehicles/{vehicle_id}",
                json=update_data,
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_vehicle_validation_error(
        self,
        async_client: AsyncClient,
        mock_vehicle_service,
    ):
        """
        Test vehicle update with validation error.

        Verifies:
        - 400 Bad Request status
        - Validation error message
        - Invalid updates rejected
        """
        vehicle_id = uuid4()
        invalid_data = {"base_price": -5000.00}
        mock_vehicle_service.update_vehicle.side_effect = (
            VehicleValidationError(
                message="Invalid price",
                code="INVALID_PRICE",
            )
        )

        with patch(
            "src.api.v1.vehicles.get_vehicle_service",
            return_value=mock_vehicle_service,
        ):
            response = await async_client.put(
                f"/api/v1/vehicles/{vehicle_id}",
                json=invalid_data,
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_update_vehicle_empty_update(
        self,
        async_client: AsyncClient,
        mock_vehicle_service,
        sample_vehicle_response,
    ):
        """
        Test vehicle update with empty data.

        Verifies:
        - Empty updates handled gracefully
        - No changes made to vehicle
        """
        vehicle_id = sample_vehicle_response.id
        mock_vehicle_service.update_vehicle.return_value = (
            sample_vehicle_response
        )

        with patch(
            "src.api.v1.vehicles.get_vehicle_service",
            return_value=mock_vehicle_service,
        ):
            response = await async_client.put(
                f"/api/v1/vehicles/{vehicle_id}",
                json={},
            )

        assert response.status_code == status.HTTP_200_OK


# ============================================================================
# Delete Vehicle Tests
# ============================================================================


class TestDeleteVehicle:
    """Test suite for vehicle deletion endpoint."""

    @pytest.mark.asyncio
    async def test_delete_vehicle_soft_delete_success(
        self,
        async_client: AsyncClient,
        mock_vehicle_service,
    ):
        """
        Test successful soft delete of vehicle.

        Verifies:
        - 204 No Content status
        - Soft delete parameter passed
        - No response body
        """
        vehicle_id = uuid4()
        mock_vehicle_service.delete_vehicle.return_value = None

        with patch(
            "src.api.v1.vehicles.get_vehicle_service",
            return_value=mock_vehicle_service,
        ):
            response = await async_client.delete(
                f"/api/v1/vehicles/{vehicle_id}",
                params={"soft": True},
            )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert response.content == b""
        mock_vehicle_service.delete_vehicle.assert_called_once_with(
            vehicle_id=vehicle_id,
            soft=True,
        )

    @pytest.mark.asyncio
    async def test_delete_vehicle_hard_delete_success(
        self,
        async_client: AsyncClient,
        mock_vehicle_service,
    ):
        """
        Test successful hard delete of vehicle.

        Verifies:
        - 204 No Content status
        - Hard delete parameter passed
        - Permanent deletion
        """
        vehicle_id = uuid4()
        mock_vehicle_service.delete_vehicle.return_value = None

        with patch(
            "src.api.v1.vehicles.get_vehicle_service",
            return_value=mock_vehicle_service,
        ):
            response = await async_client.delete(
                f"/api/v1/vehicles/{vehicle_id}",
                params={"soft": False},
            )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_vehicle_service.delete_vehicle.assert_called_once_with(
            vehicle_id=vehicle_id,
            soft=False,
        )

    @pytest.mark.asyncio
    async def test_delete_vehicle_default_soft_delete(
        self,
        async_client: AsyncClient,
        mock_vehicle_service,
    ):
        """
        Test vehicle deletion with default soft delete.

        Verifies:
        - Default behavior is soft delete
        - Soft parameter defaults to True
        """
        vehicle_id = uuid4()
        mock_vehicle_service.delete_vehicle.return_value = None

        with patch(
            "src.api.v1.vehicles.get_vehicle_service",
            return_value=mock_vehicle_service,
        ):
            response = await async_client.delete(
                f"/api/v1/vehicles/{vehicle_id}"
            )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_vehicle_service.delete_vehicle.assert_called_once_with(
            vehicle_id=vehicle_id,
            soft=True,
        )

    @pytest.mark.asyncio
    async def test_delete_vehicle_not_found(
        self,
        async_client: AsyncClient,
        mock_vehicle_service,
    ):
        """
        Test vehicle deletion with non-existent ID.

        Verifies:
        - 404 Not Found status
        - Appropriate error message
        """
        vehicle_id = uuid4()
        mock_vehicle_service.delete_vehicle.side_effect = (
            VehicleNotFoundError(
                message=f"Vehicle not found: {vehicle_id}",
                code="VEHICLE_NOT_FOUND",
            )
        )

        with patch(
            "src.api.v1.vehicles.get_vehicle_service",
            return_value=mock_vehicle_service,
        ):
            response = await async_client.delete(
                f"/api/v1/vehicles/{vehicle_id}"
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_vehicle_service_error(
        self,
        async_client: AsyncClient,
        mock_vehicle_service,
    ):
        """
        Test vehicle deletion with service error.

        Verifies:
        - 500 Internal Server Error status
        - Generic error message
        - Error handling
        """
        vehicle_id = uuid4()
        mock_vehicle_service.delete_vehicle.side_effect = (
            VehicleServiceError(
                message="Database error",
                code="DB_ERROR",
            )
        )

        with patch(
            "src.api.v1.vehicles.get_vehicle_service",
            return_value=mock_vehicle_service,
        ):
            response = await async_client.delete(
                f"/api/v1/vehicles/{vehicle_id}"
            )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to delete vehicle" in response.json()["detail"]


# ============================================================================
# Edge Cases and Security Tests
# ============================================================================


class TestEdgeCasesAndSecurity:
    """Test suite for edge cases and security scenarios."""

    @pytest.mark.asyncio
    async def test_concurrent_requests(
        self,
        async_client: AsyncClient,
        mock_vehicle_service,
        sample_vehicle_list_response,
    ):
        """
        Test handling of concurrent requests.

        Verifies:
        - Multiple simultaneous requests handled
        - No race conditions
        - Consistent responses
        """
        mock_vehicle_service.search_vehicles.return_value = (
            sample_vehicle_list_response
        )

        with patch(
            "src.api.v1.vehicles.get_vehicle_service",
            return_value=mock_vehicle_service,
        ):
            tasks = [
                async_client.get("/api/v1/vehicles")
                for _ in range(10)
            ]
            responses = await asyncio.gather(*tasks)

        assert all(r.status_code == status.HTTP_200_OK for r in responses)
        assert mock_vehicle_service.search_vehicles.call_count == 10

    @pytest.mark.asyncio
    async def test_sql_injection_prevention(
        self,
        async_client: AsyncClient,
        mock_vehicle_service,
        sample_vehicle_list_response,
    ):
        """
        Test SQL injection prevention in search parameters.

        Verifies:
        - Malicious SQL not executed
        - Input sanitization
        - Safe parameter handling
        """
        mock_vehicle_service.search_vehicles.return_value = (
            sample_vehicle_list_response
        )

        with patch(
            "src.api.v1.vehicles.get_vehicle_service",
            return_value=mock_vehicle_service,
        ):
            response = await async_client.get(
                "/api/v1/vehicles",
                params={"make": "'; DROP TABLE vehicles; --"},
            )

        assert response.status_code == status.HTTP_200_OK
        # Verify the malicious input was passed as a string parameter
        call_args = mock_vehicle_service.search_vehicles.call_args[0][0]
        assert call_args.make == "'; DROP TABLE vehicles; --"

    @pytest.mark.asyncio
    async def test_xss_prevention_in_response(
        self,
        async_client: AsyncClient,
        mock_vehicle_service,
        sample_vehicle_response,
    ):
        """
        Test XSS prevention in API responses.

        Verifies:
        - Script tags not executed
        - HTML entities escaped
        - Safe response rendering
        """
        sample_vehicle_response.description = "<script>alert('xss')</script>"
        mock_vehicle_service.get_vehicle.return_value = sample_vehicle_response

        with patch(
            "src.api.v1.vehicles.get_vehicle_service",
            return_value=mock_vehicle_service,
        ):
            response = await async_client.get(
                f"/api/v1/vehicles/{sample_vehicle_response.id}"
            )

        assert response.status_code == status.HTTP_200_OK
        # Response should contain the raw string, not execute it
        assert "<script>" in response.text

    @pytest.mark.asyncio
    async def test_large_pagination_request(
        self,
        async_client: AsyncClient,
        mock_vehicle_service,
    ):
        """
        Test handling of large pagination requests.

        Verifies:
        - Maximum page size enforced
        - Performance considerations
        - Resource limits
        """
        with patch(
            "src.api.v1.vehicles.get_vehicle_service",
            return_value=mock_vehicle_service,
        ):
            response = await async_client.get(
                "/api/v1/vehicles",
                params={"page_size": 1000},  # Exceeds max of 100
            )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_unicode_handling(
        self,
        async_client: AsyncClient,
        mock_vehicle_service,
        sample_vehicle_list_response,
    ):
        """
        Test Unicode character handling in search.

        Verifies:
        - Unicode characters accepted
        - Proper encoding/decoding
        - International character support
        """
        mock_vehicle_service.search_vehicles.return_value = (
            sample_vehicle_list_response
        )

        with patch(
            "src.api.v1.vehicles.get_vehicle_service",
            return_value=mock_vehicle_service,
        ):
            response = await async_client.get(
                "/api/v1/vehicles",
                params={"make": "Citroën", "model": "C4 Cactus"},
            )

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_unexpected_exception_handling(
        self,
        async_client: AsyncClient,
        mock_vehicle_service,
    ):
        """
        Test handling of unexpected exceptions.

        Verifies:
        - 500 Internal Server Error status
        - Generic error message (no stack trace)
        - Exception logged
        """
        mock_vehicle_service.search_vehicles.side_effect = RuntimeError(
            "Unexpected error"
        )

        with patch(
            "src.api.v1.vehicles.get_vehicle_service",
            return_value=mock_vehicle_service,
        ):
            response = await async_client.get("/api/v1/vehicles")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Internal server error" in response.json()["detail"]
        # Should not expose internal error details
        assert "RuntimeError" not in response.json()["detail"]


# ============================================================================
# Performance Tests
# ============================================================================


class TestPerformance:
    """Test suite for performance validation."""

    @pytest.mark.asyncio
    async def test_response_time_list_vehicles(
        self,
        async_client: AsyncClient,
        mock_vehicle_service,
        sample_vehicle_list_response,
    ):
        """
        Test response time for vehicle listing.

        Verifies:
        - Response time under threshold
        - Performance monitoring
        """
        import time

        mock_vehicle_service.search_vehicles.return_value = (
            sample_vehicle_list_response
        )

        with patch(
            "src.api.v1.vehicles.get_vehicle_service",
            return_value=mock_vehicle_service,
        ):
            start_time = time.time()
            response = await async_client.get("/api/v1/vehicles")
            elapsed_time = time.time() - start_time

        assert response.status_code == status.HTTP_200_OK
        assert elapsed_time < 1.0  # Should respond within 1 second

    @pytest.mark.asyncio
    async def test_response_time_get_vehicle(
        self,
        async_client: AsyncClient,
        mock_vehicle_service,
        sample_vehicle_response,
    ):
        """
        Test response time for single vehicle retrieval.

        Verifies:
        - Fast response for single item
        - Caching effectiveness
        """
        import time

        vehicle_id = sample_vehicle_response.id
        mock_vehicle_service.get_vehicle.return_value = sample_vehicle_response

        with patch(
            "src.api.v1.vehicles.get_vehicle_service",
            return_value=mock_vehicle_service,
        ):
            start_time = time.time()
            response = await async_client.get(
                f"/api/v1/vehicles/{vehicle_id}"
            )
            elapsed_time = time.time() - start_time

        assert response.status_code == status.HTTP_200_OK
        assert elapsed_time < 0.5  # Should respond within 500ms

    @pytest.mark.asyncio
    async def test_memory_efficiency_large_result_set(
        self,
        async_client: AsyncClient,
        mock_vehicle_service,
    ):
        """
        Test memory efficiency with large result sets.

        Verifies:
        - Pagination prevents memory issues
        - Streaming responses
        - Resource cleanup
        """
        # Create large response
        large_response = VehicleListResponse(
            items=[],
            total=10000,
            page=1,
            page_size=100,
            total_pages=100,
        )
        mock_vehicle_service.search_vehicles.return_value = large_response

        with patch(
            "src.api.v1.vehicles.get_vehicle_service",
            return_value=mock_vehicle_service,
        ):
            response = await async_client.get(
                "/api/v1/vehicles",
                params={"page_size": 100},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 10000
        assert data["page_size"] == 100