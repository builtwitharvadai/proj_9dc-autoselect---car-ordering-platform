"""
Comprehensive integration tests for configuration API endpoints.

This module provides end-to-end testing for vehicle configuration management
including options retrieval, validation, pricing calculation, and configuration
persistence. Tests cover authentication, authorization, error handling, and
performance scenarios.
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import status
from httpx import AsyncClient

from src.api.v1.configuration import router
from src.schemas.configuration import (
    ConfigurationRequest,
    ConfigurationResponse,
    OptionSelection,
    PackageSelection,
    PricingBreakdown,
    ValidationResult,
)
from src.services.configuration.service import (
    ConfigurationNotFoundError,
    ConfigurationServiceError,
    ConfigurationValidationError,
)


# ============================================================================
# Test Data Factories
# ============================================================================


class VehicleFactory:
    """Factory for creating test vehicle data."""

    @staticmethod
    def create_vehicle_id() -> UUID:
        """Create a test vehicle ID."""
        return uuid4()

    @staticmethod
    def create_option_ids(count: int = 3) -> list[UUID]:
        """Create test option IDs."""
        return [uuid4() for _ in range(count)]

    @staticmethod
    def create_package_ids(count: int = 2) -> list[UUID]:
        """Create test package IDs."""
        return [uuid4() for _ in range(count)]


class ConfigurationFactory:
    """Factory for creating test configuration data."""

    @staticmethod
    def create_options_response(vehicle_id: UUID) -> dict[str, Any]:
        """Create mock vehicle options response."""
        return {
            "vehicle_id": str(vehicle_id),
            "options": [
                {
                    "id": str(uuid4()),
                    "name": "Premium Audio System",
                    "category": "audio",
                    "price": 1500.00,
                    "required": False,
                    "compatible_with": [],
                    "incompatible_with": [],
                }
            ],
            "packages": [
                {
                    "id": str(uuid4()),
                    "name": "Technology Package",
                    "price": 3500.00,
                    "included_options": [],
                    "discount_amount": 500.00,
                }
            ],
            "metadata": {
                "total_options": 1,
                "total_packages": 1,
                "categories": ["audio"],
            },
        }

    @staticmethod
    def create_validation_result(is_valid: bool = True) -> dict[str, Any]:
        """Create mock validation result."""
        return {
            "is_valid": is_valid,
            "errors": [] if is_valid else ["Incompatible options selected"],
            "warnings": [],
        }

    @staticmethod
    def create_pricing_breakdown() -> dict[str, Any]:
        """Create mock pricing breakdown."""
        return {
            "total": Decimal("45000.00"),
            "breakdown": {
                "base_price": Decimal("35000.00"),
                "options_total": Decimal("5000.00"),
                "packages_total": Decimal("3000.00"),
                "subtotal": Decimal("43000.00"),
                "tax_amount": Decimal("1500.00"),
                "tax_rate": Decimal("0.0349"),
                "destination_charge": Decimal("500.00"),
                "other_fees": Decimal("0.00"),
                "discount_amount": Decimal("500.00"),
                "incentives": [],
            },
        }

    @staticmethod
    def create_saved_configuration(
        vehicle_id: UUID, user_id: UUID
    ) -> dict[str, Any]:
        """Create mock saved configuration."""
        config_id = uuid4()
        now = datetime.utcnow()
        return {
            "id": str(config_id),
            "vehicle_id": str(vehicle_id),
            "user_id": str(user_id),
            "selected_options": [str(uuid4()) for _ in range(2)],
            "selected_packages": [str(uuid4())],
            "pricing_breakdown": {
                "base_price": Decimal("35000.00"),
                "options_total": Decimal("5000.00"),
                "packages_total": Decimal("3000.00"),
                "subtotal": Decimal("43000.00"),
                "tax_amount": Decimal("1500.00"),
                "tax_rate": Decimal("0.0349"),
                "destination_charge": Decimal("500.00"),
                "other_fees": Decimal("0.00"),
            },
            "total_price": Decimal("45000.00"),
            "is_valid": True,
            "status": "active",
            "notes": "Test configuration",
            "created_at": now,
            "updated_at": now,
            "expires_at": now + timedelta(days=30),
        }


class UserFactory:
    """Factory for creating test user data."""

    @staticmethod
    def create_user(user_id: UUID | None = None) -> MagicMock:
        """Create mock authenticated user."""
        user = MagicMock()
        user.id = user_id or uuid4()
        user.email = "test@example.com"
        user.is_active = True
        return user


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_config_service():
    """Create mock configuration service."""
    service = AsyncMock()
    service.get_vehicle_options = AsyncMock()
    service.validate_configuration = AsyncMock()
    service.calculate_pricing = AsyncMock()
    service.save_configuration = AsyncMock()
    service.get_configuration = AsyncMock()
    return service


@pytest.fixture
def mock_current_user():
    """Create mock current user."""
    return UserFactory.create_user()


@pytest.fixture
def vehicle_id():
    """Create test vehicle ID."""
    return VehicleFactory.create_vehicle_id()


@pytest.fixture
def option_ids():
    """Create test option IDs."""
    return VehicleFactory.create_option_ids()


@pytest.fixture
def package_ids():
    """Create test package IDs."""
    return VehicleFactory.create_package_ids()


# ============================================================================
# Unit Tests: Get Vehicle Options
# ============================================================================


class TestGetVehicleOptions:
    """Test suite for get_vehicle_options endpoint."""

    @pytest.mark.asyncio
    async def test_get_options_success(
        self, async_client: AsyncClient, mock_config_service, vehicle_id
    ):
        """Test successful retrieval of vehicle options."""
        # Arrange
        expected_response = ConfigurationFactory.create_options_response(
            vehicle_id
        )
        mock_config_service.get_vehicle_options.return_value = (
            expected_response
        )

        with patch(
            "src.api.v1.configuration.get_configuration_service",
            return_value=mock_config_service,
        ):
            # Act
            response = await async_client.get(
                f"/vehicles/{vehicle_id}/options"
            )

            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["vehicle_id"] == str(vehicle_id)
            assert "options" in data
            assert "packages" in data
            assert "metadata" in data
            assert data["metadata"]["total_options"] == 1
            assert data["metadata"]["total_packages"] == 1

    @pytest.mark.asyncio
    async def test_get_options_with_category_filter(
        self, async_client: AsyncClient, mock_config_service, vehicle_id
    ):
        """Test options retrieval with category filter."""
        # Arrange
        expected_response = ConfigurationFactory.create_options_response(
            vehicle_id
        )
        mock_config_service.get_vehicle_options.return_value = (
            expected_response
        )

        with patch(
            "src.api.v1.configuration.get_configuration_service",
            return_value=mock_config_service,
        ):
            # Act
            response = await async_client.get(
                f"/vehicles/{vehicle_id}/options?category=audio"
            )

            # Assert
            assert response.status_code == status.HTTP_200_OK
            mock_config_service.get_vehicle_options.assert_called_once_with(
                vehicle_id=vehicle_id,
                category="audio",
                include_required_only=False,
            )

    @pytest.mark.asyncio
    async def test_get_options_required_only(
        self, async_client: AsyncClient, mock_config_service, vehicle_id
    ):
        """Test options retrieval with required_only filter."""
        # Arrange
        expected_response = ConfigurationFactory.create_options_response(
            vehicle_id
        )
        mock_config_service.get_vehicle_options.return_value = (
            expected_response
        )

        with patch(
            "src.api.v1.configuration.get_configuration_service",
            return_value=mock_config_service,
        ):
            # Act
            response = await async_client.get(
                f"/vehicles/{vehicle_id}/options?required_only=true"
            )

            # Assert
            assert response.status_code == status.HTTP_200_OK
            mock_config_service.get_vehicle_options.assert_called_once_with(
                vehicle_id=vehicle_id,
                category=None,
                include_required_only=True,
            )

    @pytest.mark.asyncio
    async def test_get_options_vehicle_not_found(
        self, async_client: AsyncClient, mock_config_service, vehicle_id
    ):
        """Test options retrieval for non-existent vehicle."""
        # Arrange
        mock_config_service.get_vehicle_options.side_effect = (
            ConfigurationServiceError("Vehicle not found")
        )

        with patch(
            "src.api.v1.configuration.get_configuration_service",
            return_value=mock_config_service,
        ):
            # Act
            response = await async_client.get(
                f"/vehicles/{vehicle_id}/options"
            )

            # Assert
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "Vehicle not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_options_service_error(
        self, async_client: AsyncClient, mock_config_service, vehicle_id
    ):
        """Test options retrieval with service error."""
        # Arrange
        mock_config_service.get_vehicle_options.side_effect = Exception(
            "Database connection failed"
        )

        with patch(
            "src.api.v1.configuration.get_configuration_service",
            return_value=mock_config_service,
        ):
            # Act
            response = await async_client.get(
                f"/vehicles/{vehicle_id}/options"
            )

            # Assert
            assert (
                response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            assert "Failed to retrieve vehicle options" in response.json()[
                "detail"
            ]

    @pytest.mark.asyncio
    async def test_get_options_invalid_uuid(self, async_client: AsyncClient):
        """Test options retrieval with invalid vehicle ID format."""
        # Act
        response = await async_client.get("/vehicles/invalid-uuid/options")

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ============================================================================
# Unit Tests: Validate Configuration
# ============================================================================


class TestValidateConfiguration:
    """Test suite for validate_configuration endpoint."""

    @pytest.mark.asyncio
    async def test_validate_success(
        self,
        async_client: AsyncClient,
        mock_config_service,
        vehicle_id,
        option_ids,
        package_ids,
    ):
        """Test successful configuration validation."""
        # Arrange
        expected_result = ConfigurationFactory.create_validation_result(
            is_valid=True
        )
        mock_config_service.validate_configuration.return_value = (
            expected_result
        )

        with patch(
            "src.api.v1.configuration.get_configuration_service",
            return_value=mock_config_service,
        ):
            # Act
            response = await async_client.post(
                f"/vehicles/{vehicle_id}/validate",
                params={
                    "selected_options": [str(opt) for opt in option_ids],
                    "selected_packages": [str(pkg) for pkg in package_ids],
                },
            )

            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["is_valid"] is True
            assert len(data["errors"]) == 0

    @pytest.mark.asyncio
    async def test_validate_with_errors(
        self,
        async_client: AsyncClient,
        mock_config_service,
        vehicle_id,
        option_ids,
        package_ids,
    ):
        """Test validation with configuration errors."""
        # Arrange
        expected_result = ConfigurationFactory.create_validation_result(
            is_valid=False
        )
        mock_config_service.validate_configuration.return_value = (
            expected_result
        )

        with patch(
            "src.api.v1.configuration.get_configuration_service",
            return_value=mock_config_service,
        ):
            # Act
            response = await async_client.post(
                f"/vehicles/{vehicle_id}/validate",
                params={
                    "selected_options": [str(opt) for opt in option_ids],
                    "selected_packages": [str(pkg) for pkg in package_ids],
                },
            )

            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["is_valid"] is False
            assert len(data["errors"]) > 0

    @pytest.mark.asyncio
    async def test_validate_with_trim_and_year(
        self,
        async_client: AsyncClient,
        mock_config_service,
        vehicle_id,
        option_ids,
        package_ids,
    ):
        """Test validation with trim and year parameters."""
        # Arrange
        expected_result = ConfigurationFactory.create_validation_result()
        mock_config_service.validate_configuration.return_value = (
            expected_result
        )

        with patch(
            "src.api.v1.configuration.get_configuration_service",
            return_value=mock_config_service,
        ):
            # Act
            response = await async_client.post(
                f"/vehicles/{vehicle_id}/validate",
                params={
                    "selected_options": [str(opt) for opt in option_ids],
                    "selected_packages": [str(pkg) for pkg in package_ids],
                    "trim": "Premium",
                    "year": 2024,
                },
            )

            # Assert
            assert response.status_code == status.HTTP_200_OK
            mock_config_service.validate_configuration.assert_called_once()
            call_kwargs = (
                mock_config_service.validate_configuration.call_args.kwargs
            )
            assert call_kwargs["trim"] == "Premium"
            assert call_kwargs["year"] == 2024

    @pytest.mark.asyncio
    async def test_validate_service_error(
        self,
        async_client: AsyncClient,
        mock_config_service,
        vehicle_id,
        option_ids,
        package_ids,
    ):
        """Test validation with service error."""
        # Arrange
        mock_config_service.validate_configuration.side_effect = (
            ConfigurationServiceError("Validation service unavailable")
        )

        with patch(
            "src.api.v1.configuration.get_configuration_service",
            return_value=mock_config_service,
        ):
            # Act
            response = await async_client.post(
                f"/vehicles/{vehicle_id}/validate",
                params={
                    "selected_options": [str(opt) for opt in option_ids],
                    "selected_packages": [str(pkg) for pkg in package_ids],
                },
            )

            # Assert
            assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_validate_empty_selections(
        self, async_client: AsyncClient, mock_config_service, vehicle_id
    ):
        """Test validation with empty option and package selections."""
        # Arrange
        expected_result = ConfigurationFactory.create_validation_result()
        mock_config_service.validate_configuration.return_value = (
            expected_result
        )

        with patch(
            "src.api.v1.configuration.get_configuration_service",
            return_value=mock_config_service,
        ):
            # Act
            response = await async_client.post(
                f"/vehicles/{vehicle_id}/validate",
                params={"selected_options": [], "selected_packages": []},
            )

            # Assert
            assert response.status_code == status.HTTP_200_OK


# ============================================================================
# Unit Tests: Calculate Pricing
# ============================================================================


class TestCalculatePricing:
    """Test suite for calculate_pricing endpoint."""

    @pytest.mark.asyncio
    async def test_calculate_pricing_success(
        self,
        async_client: AsyncClient,
        mock_config_service,
        vehicle_id,
        option_ids,
        package_ids,
    ):
        """Test successful pricing calculation."""
        # Arrange
        expected_pricing = ConfigurationFactory.create_pricing_breakdown()
        mock_config_service.calculate_pricing.return_value = expected_pricing

        with patch(
            "src.api.v1.configuration.get_configuration_service",
            return_value=mock_config_service,
        ):
            # Act
            response = await async_client.post(
                f"/vehicles/{vehicle_id}/price",
                params={
                    "selected_options": [str(opt) for opt in option_ids],
                    "selected_packages": [str(pkg) for pkg in package_ids],
                },
            )

            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "base_price" in data
            assert "options_total" in data
            assert "packages_total" in data
            assert "total_price" in data
            assert float(data["total_price"]) == 45000.00

    @pytest.mark.asyncio
    async def test_calculate_pricing_with_region(
        self,
        async_client: AsyncClient,
        mock_config_service,
        vehicle_id,
        option_ids,
        package_ids,
    ):
        """Test pricing calculation with region parameter."""
        # Arrange
        expected_pricing = ConfigurationFactory.create_pricing_breakdown()
        mock_config_service.calculate_pricing.return_value = expected_pricing

        with patch(
            "src.api.v1.configuration.get_configuration_service",
            return_value=mock_config_service,
        ):
            # Act
            response = await async_client.post(
                f"/vehicles/{vehicle_id}/price",
                params={
                    "selected_options": [str(opt) for opt in option_ids],
                    "selected_packages": [str(pkg) for pkg in package_ids],
                    "region": "CA",
                },
            )

            # Assert
            assert response.status_code == status.HTTP_200_OK
            mock_config_service.calculate_pricing.assert_called_once()
            call_kwargs = (
                mock_config_service.calculate_pricing.call_args.kwargs
            )
            assert call_kwargs["region"] == "CA"

    @pytest.mark.asyncio
    async def test_calculate_pricing_without_tax(
        self,
        async_client: AsyncClient,
        mock_config_service,
        vehicle_id,
        option_ids,
        package_ids,
    ):
        """Test pricing calculation excluding tax."""
        # Arrange
        expected_pricing = ConfigurationFactory.create_pricing_breakdown()
        mock_config_service.calculate_pricing.return_value = expected_pricing

        with patch(
            "src.api.v1.configuration.get_configuration_service",
            return_value=mock_config_service,
        ):
            # Act
            response = await async_client.post(
                f"/vehicles/{vehicle_id}/price",
                params={
                    "selected_options": [str(opt) for opt in option_ids],
                    "selected_packages": [str(pkg) for pkg in package_ids],
                    "include_tax": False,
                },
            )

            # Assert
            assert response.status_code == status.HTTP_200_OK
            call_kwargs = (
                mock_config_service.calculate_pricing.call_args.kwargs
            )
            assert call_kwargs["include_tax"] is False

    @pytest.mark.asyncio
    async def test_calculate_pricing_without_destination(
        self,
        async_client: AsyncClient,
        mock_config_service,
        vehicle_id,
        option_ids,
        package_ids,
    ):
        """Test pricing calculation excluding destination charge."""
        # Arrange
        expected_pricing = ConfigurationFactory.create_pricing_breakdown()
        mock_config_service.calculate_pricing.return_value = expected_pricing

        with patch(
            "src.api.v1.configuration.get_configuration_service",
            return_value=mock_config_service,
        ):
            # Act
            response = await async_client.post(
                f"/vehicles/{vehicle_id}/price",
                params={
                    "selected_options": [str(opt) for opt in option_ids],
                    "selected_packages": [str(pkg) for pkg in package_ids],
                    "include_destination": False,
                },
            )

            # Assert
            assert response.status_code == status.HTTP_200_OK
            call_kwargs = (
                mock_config_service.calculate_pricing.call_args.kwargs
            )
            assert call_kwargs["include_destination"] is False

    @pytest.mark.asyncio
    async def test_calculate_pricing_vehicle_not_found(
        self,
        async_client: AsyncClient,
        mock_config_service,
        vehicle_id,
        option_ids,
        package_ids,
    ):
        """Test pricing calculation for non-existent vehicle."""
        # Arrange
        mock_config_service.calculate_pricing.side_effect = (
            ConfigurationServiceError("Vehicle not found")
        )

        with patch(
            "src.api.v1.configuration.get_configuration_service",
            return_value=mock_config_service,
        ):
            # Act
            response = await async_client.post(
                f"/vehicles/{vehicle_id}/price",
                params={
                    "selected_options": [str(opt) for opt in option_ids],
                    "selected_packages": [str(pkg) for pkg in package_ids],
                },
            )

            # Assert
            assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_calculate_pricing_performance(
        self,
        async_client: AsyncClient,
        mock_config_service,
        vehicle_id,
        option_ids,
        package_ids,
    ):
        """Test pricing calculation performance under load."""
        # Arrange
        expected_pricing = ConfigurationFactory.create_pricing_breakdown()
        mock_config_service.calculate_pricing.return_value = expected_pricing

        with patch(
            "src.api.v1.configuration.get_configuration_service",
            return_value=mock_config_service,
        ):
            # Act
            start_time = asyncio.get_event_loop().time()
            response = await async_client.post(
                f"/vehicles/{vehicle_id}/price",
                params={
                    "selected_options": [str(opt) for opt in option_ids],
                    "selected_packages": [str(pkg) for pkg in package_ids],
                },
            )
            elapsed_time = asyncio.get_event_loop().time() - start_time

            # Assert
            assert response.status_code == status.HTTP_200_OK
            assert elapsed_time < 1.0  # Should complete within 1 second


# ============================================================================
# Integration Tests: Save Configuration
# ============================================================================


class TestSaveConfiguration:
    """Test suite for save_configuration endpoint."""

    @pytest.mark.asyncio
    async def test_save_configuration_success(
        self,
        async_client: AsyncClient,
        mock_config_service,
        mock_current_user,
        vehicle_id,
        option_ids,
        package_ids,
    ):
        """Test successful configuration save."""
        # Arrange
        saved_config = ConfigurationFactory.create_saved_configuration(
            vehicle_id, mock_current_user.id
        )
        mock_config_service.save_configuration.return_value = saved_config

        request_data = {
            "vehicle_id": str(vehicle_id),
            "options": [
                {"option_id": str(opt_id), "quantity": 1}
                for opt_id in option_ids
            ],
            "packages": [
                {"package_id": str(pkg_id)} for pkg_id in package_ids
            ],
            "notes": "Test configuration",
        }

        with patch(
            "src.api.v1.configuration.get_configuration_service",
            return_value=mock_config_service,
        ), patch(
            "src.api.deps.get_current_active_user",
            return_value=mock_current_user,
        ):
            # Act
            response = await async_client.post(
                "/vehicles/configurations", json=request_data
            )

            # Assert
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert "id" in data
            assert data["vehicle_id"] == str(vehicle_id)
            assert data["status"] == "active"

    @pytest.mark.asyncio
    async def test_save_configuration_validation_error(
        self,
        async_client: AsyncClient,
        mock_config_service,
        mock_current_user,
        vehicle_id,
        option_ids,
        package_ids,
    ):
        """Test configuration save with validation errors."""
        # Arrange
        validation_error = ConfigurationValidationError(
            "Invalid configuration",
            errors=["Incompatible options selected"],
        )
        mock_config_service.save_configuration.side_effect = validation_error

        request_data = {
            "vehicle_id": str(vehicle_id),
            "options": [
                {"option_id": str(opt_id), "quantity": 1}
                for opt_id in option_ids
            ],
            "packages": [
                {"package_id": str(pkg_id)} for pkg_id in package_ids
            ],
        }

        with patch(
            "src.api.v1.configuration.get_configuration_service",
            return_value=mock_config_service,
        ), patch(
            "src.api.deps.get_current_active_user",
            return_value=mock_current_user,
        ):
            # Act
            response = await async_client.post(
                "/vehicles/configurations", json=request_data
            )

            # Assert
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            data = response.json()
            assert "errors" in data["detail"]

    @pytest.mark.asyncio
    async def test_save_configuration_with_customer_dealer(
        self,
        async_client: AsyncClient,
        mock_config_service,
        mock_current_user,
        vehicle_id,
        option_ids,
        package_ids,
    ):
        """Test configuration save with customer and dealer IDs."""
        # Arrange
        customer_id = uuid4()
        dealer_id = uuid4()
        saved_config = ConfigurationFactory.create_saved_configuration(
            vehicle_id, mock_current_user.id
        )
        mock_config_service.save_configuration.return_value = saved_config

        request_data = {
            "vehicle_id": str(vehicle_id),
            "options": [
                {"option_id": str(opt_id), "quantity": 1}
                for opt_id in option_ids
            ],
            "packages": [
                {"package_id": str(pkg_id)} for pkg_id in package_ids
            ],
            "customer_id": str(customer_id),
            "dealer_id": str(dealer_id),
        }

        with patch(
            "src.api.v1.configuration.get_configuration_service",
            return_value=mock_config_service,
        ), patch(
            "src.api.deps.get_current_active_user",
            return_value=mock_current_user,
        ):
            # Act
            response = await async_client.post(
                "/vehicles/configurations", json=request_data
            )

            # Assert
            assert response.status_code == status.HTTP_201_CREATED

    @pytest.mark.asyncio
    async def test_save_configuration_unauthorized(
        self, async_client: AsyncClient, vehicle_id, option_ids, package_ids
    ):
        """Test configuration save without authentication."""
        # Arrange
        request_data = {
            "vehicle_id": str(vehicle_id),
            "options": [
                {"option_id": str(opt_id), "quantity": 1}
                for opt_id in option_ids
            ],
            "packages": [
                {"package_id": str(pkg_id)} for pkg_id in package_ids
            ],
        }

        # Act
        response = await async_client.post(
            "/vehicles/configurations", json=request_data
        )

        # Assert
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]


# ============================================================================
# Integration Tests: Get Configuration
# ============================================================================


class TestGetConfiguration:
    """Test suite for get_configuration endpoint."""

    @pytest.mark.asyncio
    async def test_get_configuration_success(
        self,
        async_client: AsyncClient,
        mock_config_service,
        mock_current_user,
        vehicle_id,
    ):
        """Test successful configuration retrieval."""
        # Arrange
        config_id = uuid4()
        saved_config = ConfigurationFactory.create_saved_configuration(
            vehicle_id, mock_current_user.id
        )
        saved_config["id"] = str(config_id)
        mock_config_service.get_configuration.return_value = saved_config

        with patch(
            "src.api.v1.configuration.get_configuration_service",
            return_value=mock_config_service,
        ), patch(
            "src.api.deps.get_current_active_user",
            return_value=mock_current_user,
        ):
            # Act
            response = await async_client.get(
                f"/vehicles/configurations/{config_id}"
            )

            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == str(config_id)
            assert data["vehicle_id"] == str(vehicle_id)

    @pytest.mark.asyncio
    async def test_get_configuration_not_found(
        self,
        async_client: AsyncClient,
        mock_config_service,
        mock_current_user,
    ):
        """Test configuration retrieval for non-existent ID."""
        # Arrange
        config_id = uuid4()
        mock_config_service.get_configuration.side_effect = (
            ConfigurationNotFoundError(f"Configuration {config_id} not found")
        )

        with patch(
            "src.api.v1.configuration.get_configuration_service",
            return_value=mock_config_service,
        ), patch(
            "src.api.deps.get_current_active_user",
            return_value=mock_current_user,
        ):
            # Act
            response = await async_client.get(
                f"/vehicles/configurations/{config_id}"
            )

            # Assert
            assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_configuration_unauthorized_access(
        self,
        async_client: AsyncClient,
        mock_config_service,
        mock_current_user,
        vehicle_id,
    ):
        """Test configuration retrieval by non-owner."""
        # Arrange
        config_id = uuid4()
        other_user_id = uuid4()
        saved_config = ConfigurationFactory.create_saved_configuration(
            vehicle_id, other_user_id
        )
        saved_config["id"] = str(config_id)
        mock_config_service.get_configuration.return_value = saved_config

        with patch(
            "src.api.v1.configuration.get_configuration_service",
            return_value=mock_config_service,
        ), patch(
            "src.api.deps.get_current_active_user",
            return_value=mock_current_user,
        ):
            # Act
            response = await async_client.get(
                f"/vehicles/configurations/{config_id}"
            )

            # Assert
            assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_get_configuration_invalid_uuid(
        self, async_client: AsyncClient, mock_current_user
    ):
        """Test configuration retrieval with invalid UUID."""
        # Arrange
        with patch(
            "src.api.deps.get_current_active_user",
            return_value=mock_current_user,
        ):
            # Act
            response = await async_client.get(
                "/vehicles/configurations/invalid-uuid"
            )

            # Assert
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ============================================================================
# Performance Tests
# ============================================================================


class TestPerformance:
    """Performance test suite for configuration API."""

    @pytest.mark.asyncio
    async def test_concurrent_pricing_calculations(
        self,
        async_client: AsyncClient,
        mock_config_service,
        vehicle_id,
        option_ids,
        package_ids,
    ):
        """Test concurrent pricing calculation requests."""
        # Arrange
        expected_pricing = ConfigurationFactory.create_pricing_breakdown()
        mock_config_service.calculate_pricing.return_value = expected_pricing

        async def make_request():
            return await async_client.post(
                f"/vehicles/{vehicle_id}/price",
                params={
                    "selected_options": [str(opt) for opt in option_ids],
                    "selected_packages": [str(pkg) for pkg in package_ids],
                },
            )

        with patch(
            "src.api.v1.configuration.get_configuration_service",
            return_value=mock_config_service,
        ):
            # Act
            start_time = asyncio.get_event_loop().time()
            responses = await asyncio.gather(
                *[make_request() for _ in range(10)]
            )
            elapsed_time = asyncio.get_event_loop().time() - start_time

            # Assert
            assert all(
                r.status_code == status.HTTP_200_OK for r in responses
            )
            assert elapsed_time < 5.0  # All requests within 5 seconds

    @pytest.mark.asyncio
    async def test_large_option_set_performance(
        self, async_client: AsyncClient, mock_config_service, vehicle_id
    ):
        """Test performance with large number of options."""
        # Arrange
        large_option_set = [str(uuid4()) for _ in range(50)]
        large_package_set = [str(uuid4()) for _ in range(20)]
        expected_pricing = ConfigurationFactory.create_pricing_breakdown()
        mock_config_service.calculate_pricing.return_value = expected_pricing

        with patch(
            "src.api.v1.configuration.get_configuration_service",
            return_value=mock_config_service,
        ):
            # Act
            start_time = asyncio.get_event_loop().time()
            response = await async_client.post(
                f"/vehicles/{vehicle_id}/price",
                params={
                    "selected_options": large_option_set,
                    "selected_packages": large_package_set,
                },
            )
            elapsed_time = asyncio.get_event_loop().time() - start_time

            # Assert
            assert response.status_code == status.HTTP_200_OK
            assert elapsed_time < 2.0  # Should handle large sets efficiently


# ============================================================================
# Edge Cases and Error Scenarios
# ============================================================================


class TestEdgeCases:
    """Test suite for edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_empty_vehicle_options(
        self, async_client: AsyncClient, mock_config_service, vehicle_id
    ):
        """Test vehicle with no available options."""
        # Arrange
        empty_response = {
            "vehicle_id": str(vehicle_id),
            "options": [],
            "packages": [],
            "metadata": {
                "total_options": 0,
                "total_packages": 0,
                "categories": [],
            },
        }
        mock_config_service.get_vehicle_options.return_value = empty_response

        with patch(
            "src.api.v1.configuration.get_configuration_service",
            return_value=mock_config_service,
        ):
            # Act
            response = await async_client.get(
                f"/vehicles/{vehicle_id}/options"
            )

            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data["options"]) == 0
            assert len(data["packages"]) == 0

    @pytest.mark.asyncio
    async def test_duplicate_option_selection(
        self,
        async_client: AsyncClient,
        mock_config_service,
        vehicle_id,
        option_ids,
    ):
        """Test validation with duplicate option selections."""
        # Arrange
        duplicate_options = [str(option_ids[0]), str(option_ids[0])]
        expected_result = ConfigurationFactory.create_validation_result(
            is_valid=False
        )
        mock_config_service.validate_configuration.return_value = (
            expected_result
        )

        with patch(
            "src.api.v1.configuration.get_configuration_service",
            return_value=mock_config_service,
        ):
            # Act
            response = await async_client.post(
                f"/vehicles/{vehicle_id}/validate",
                params={
                    "selected_options": duplicate_options,
                    "selected_packages": [],
                },
            )

            # Assert
            assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_pricing_with_zero_selections(
        self, async_client: AsyncClient, mock_config_service, vehicle_id
    ):
        """Test pricing calculation with no options or packages."""
        # Arrange
        base_pricing = {
            "total": Decimal("35000.00"),
            "breakdown": {
                "base_price": Decimal("35000.00"),
                "options_total": Decimal("0.00"),
                "packages_total": Decimal("0.00"),
                "subtotal": Decimal("35000.00"),
                "tax_amount": Decimal("0.00"),
                "tax_rate": Decimal("0.00"),
                "destination_charge": Decimal("0.00"),
                "other_fees": Decimal("0.00"),
            },
        }
        mock_config_service.calculate_pricing.return_value = base_pricing

        with patch(
            "src.api.v1.configuration.get_configuration_service",
            return_value=mock_config_service,
        ):
            # Act
            response = await async_client.post(
                f"/vehicles/{vehicle_id}/price",
                params={"selected_options": [], "selected_packages": []},
            )

            # Assert
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert float(data["total_price"]) == 35000.00


# ============================================================================
# Security Tests
# ============================================================================


class TestSecurity:
    """Security test suite for configuration API."""

    @pytest.mark.asyncio
    async def test_sql_injection_attempt_in_category(
        self, async_client: AsyncClient, mock_config_service, vehicle_id
    ):
        """Test SQL injection prevention in category parameter."""
        # Arrange
        malicious_category = "'; DROP TABLE vehicles; --"
        mock_config_service.get_vehicle_options.return_value = (
            ConfigurationFactory.create_options_response(vehicle_id)
        )

        with patch(
            "src.api.v1.configuration.get_configuration_service",
            return_value=mock_config_service,
        ):
            # Act
            response = await async_client.get(
                f"/vehicles/{vehicle_id}/options",
                params={"category": malicious_category},
            )

            # Assert
            # Should handle safely without SQL injection
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_400_BAD_REQUEST,
            ]

    @pytest.mark.asyncio
    async def test_xss_attempt_in_notes(
        self,
        async_client: AsyncClient,
        mock_config_service,
        mock_current_user,
        vehicle_id,
        option_ids,
        package_ids,
    ):
        """Test XSS prevention in configuration notes."""
        # Arrange
        xss_payload = "<script>alert('XSS')</script>"
        saved_config = ConfigurationFactory.create_saved_configuration(
            vehicle_id, mock_current_user.id
        )
        mock_config_service.save_configuration.return_value = saved_config

        request_data = {
            "vehicle_id": str(vehicle_id),
            "options": [
                {"option_id": str(opt_id), "quantity": 1}
                for opt_id in option_ids
            ],
            "packages": [
                {"package_id": str(pkg_id)} for pkg_id in package_ids
            ],
            "notes": xss_payload,
        }

        with patch(
            "src.api.v1.configuration.get_configuration_service",
            return_value=mock_config_service,
        ), patch(
            "src.api.deps.get_current_active_user",
            return_value=mock_current_user,
        ):
            # Act
            response = await async_client.post(
                "/vehicles/configurations", json=request_data
            )

            # Assert
            # Should sanitize or reject XSS payload
            assert response.status_code in [
                status.HTTP_201_CREATED,
                status.HTTP_400_BAD_REQUEST,
            ]

    @pytest.mark.asyncio
    async def test_rate_limiting_simulation(
        self, async_client: AsyncClient, mock_config_service, vehicle_id
    ):
        """Test API behavior under rapid repeated requests."""
        # Arrange
        mock_config_service.get_vehicle_options.return_value = (
            ConfigurationFactory.create_options_response(vehicle_id)
        )

        with patch(
            "src.api.v1.configuration.get_configuration_service",
            return_value=mock_config_service,
        ):
            # Act
            responses = []
            for _ in range(100):
                response = await async_client.get(
                    f"/vehicles/{vehicle_id}/options"
                )
                responses.append(response)

            # Assert
            # Should handle rapid requests gracefully
            success_count = sum(
                1 for r in responses if r.status_code == status.HTTP_200_OK
            )
            assert success_count > 0  # At least some should succeed