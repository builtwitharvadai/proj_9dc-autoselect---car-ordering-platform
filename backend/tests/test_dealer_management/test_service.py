"""
Comprehensive test suite for dealer management service.

This module provides extensive test coverage for the DealerManagementService,
including configuration management, bulk operations, validation, error handling,
and edge cases with proper mocking and isolation.
"""

import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.dealer_configuration import (
    DealerOptionConfig,
    DealerPackageConfig,
)
from src.database.models.package import Package
from src.database.models.vehicle_option import VehicleOption
from src.services.dealer_management.service import (
    DealerConfigurationNotFoundError,
    DealerManagementError,
    DealerManagementService,
    DealerValidationError,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """
    Create mock database session.

    Returns:
        AsyncMock: Mocked async database session
    """
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.rollback = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def dealer_service(mock_db_session: AsyncMock) -> DealerManagementService:
    """
    Create dealer management service instance.

    Args:
        mock_db_session: Mocked database session

    Returns:
        DealerManagementService: Service instance for testing
    """
    return DealerManagementService(db=mock_db_session)


@pytest.fixture
def sample_dealer_id() -> uuid.UUID:
    """Generate sample dealer ID."""
    return uuid.uuid4()


@pytest.fixture
def sample_option_id() -> uuid.UUID:
    """Generate sample option ID."""
    return uuid.uuid4()


@pytest.fixture
def sample_package_id() -> uuid.UUID:
    """Generate sample package ID."""
    return uuid.uuid4()


@pytest.fixture
def sample_config_id() -> uuid.UUID:
    """Generate sample configuration ID."""
    return uuid.uuid4()


@pytest.fixture
def mock_vehicle_option(sample_option_id: uuid.UUID) -> VehicleOption:
    """
    Create mock vehicle option.

    Args:
        sample_option_id: Option identifier

    Returns:
        VehicleOption: Mock vehicle option instance
    """
    option = MagicMock(spec=VehicleOption)
    option.id = sample_option_id
    option.name = "Premium Sound System"
    option.base_price = Decimal("1500.00")
    return option


@pytest.fixture
def mock_package(sample_package_id: uuid.UUID) -> Package:
    """
    Create mock package.

    Args:
        sample_package_id: Package identifier

    Returns:
        Package: Mock package instance
    """
    package = MagicMock(spec=Package)
    package.id = sample_package_id
    package.name = "Technology Package"
    package.base_price = Decimal("3500.00")
    return package


@pytest.fixture
def mock_option_config(
    sample_config_id: uuid.UUID,
    sample_dealer_id: uuid.UUID,
    sample_option_id: uuid.UUID,
) -> DealerOptionConfig:
    """
    Create mock dealer option configuration.

    Args:
        sample_config_id: Configuration identifier
        sample_dealer_id: Dealer identifier
        sample_option_id: Option identifier

    Returns:
        DealerOptionConfig: Mock configuration instance
    """
    config = MagicMock(spec=DealerOptionConfig)
    config.id = sample_config_id
    config.dealer_id = sample_dealer_id
    config.option_id = sample_option_id
    config.is_available = True
    config.custom_price = None
    config.effective_from = datetime.utcnow()
    config.effective_to = None
    config.region = None
    config.update_availability = MagicMock()
    config.update_custom_price = MagicMock()
    return config


@pytest.fixture
def mock_package_config(
    sample_config_id: uuid.UUID,
    sample_dealer_id: uuid.UUID,
    sample_package_id: uuid.UUID,
) -> DealerPackageConfig:
    """
    Create mock dealer package configuration.

    Args:
        sample_config_id: Configuration identifier
        sample_dealer_id: Dealer identifier
        sample_package_id: Package identifier

    Returns:
        DealerPackageConfig: Mock configuration instance
    """
    config = MagicMock(spec=DealerPackageConfig)
    config.id = sample_config_id
    config.dealer_id = sample_dealer_id
    config.package_id = sample_package_id
    config.is_available = True
    config.custom_price = None
    config.effective_from = datetime.utcnow()
    config.effective_to = None
    config.region = None
    config.update_availability = MagicMock()
    config.update_custom_price = MagicMock()
    return config


# ============================================================================
# Unit Tests - Service Initialization
# ============================================================================


class TestServiceInitialization:
    """Test suite for service initialization."""

    def test_service_initialization_success(
        self, mock_db_session: AsyncMock
    ) -> None:
        """Test successful service initialization."""
        service = DealerManagementService(db=mock_db_session)

        assert service.db is mock_db_session
        assert isinstance(service, DealerManagementService)

    def test_service_initialization_with_none_session(self) -> None:
        """Test service initialization with None session."""
        service = DealerManagementService(db=None)

        assert service.db is None


# ============================================================================
# Unit Tests - Create Option Configuration
# ============================================================================


class TestCreateOptionConfig:
    """Test suite for creating dealer option configurations."""

    @pytest.mark.asyncio
    async def test_create_option_config_success(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_dealer_id: uuid.UUID,
        sample_option_id: uuid.UUID,
        mock_vehicle_option: VehicleOption,
    ) -> None:
        """Test successful option configuration creation."""
        # Arrange
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_vehicle_option
        mock_db_session.execute.return_value = mock_result

        # Act
        config = await dealer_service.create_option_config(
            dealer_id=sample_dealer_id,
            option_id=sample_option_id,
            is_available=True,
        )

        # Assert
        assert config is not None
        assert config.dealer_id == sample_dealer_id
        assert config.option_id == sample_option_id
        assert config.is_available is True
        mock_db_session.add.assert_called_once()
        mock_db_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_option_config_with_custom_price(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_dealer_id: uuid.UUID,
        sample_option_id: uuid.UUID,
        mock_vehicle_option: VehicleOption,
    ) -> None:
        """Test option configuration creation with custom price."""
        # Arrange
        custom_price = Decimal("2000.00")
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_vehicle_option
        mock_db_session.execute.return_value = mock_result

        # Act
        config = await dealer_service.create_option_config(
            dealer_id=sample_dealer_id,
            option_id=sample_option_id,
            custom_price=custom_price,
        )

        # Assert
        assert config.custom_price == custom_price

    @pytest.mark.asyncio
    async def test_create_option_config_with_date_range(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_dealer_id: uuid.UUID,
        sample_option_id: uuid.UUID,
        mock_vehicle_option: VehicleOption,
    ) -> None:
        """Test option configuration creation with date range."""
        # Arrange
        effective_from = datetime.utcnow()
        effective_to = effective_from + timedelta(days=30)
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_vehicle_option
        mock_db_session.execute.return_value = mock_result

        # Act
        config = await dealer_service.create_option_config(
            dealer_id=sample_dealer_id,
            option_id=sample_option_id,
            effective_from=effective_from,
            effective_to=effective_to,
        )

        # Assert
        assert config.effective_from == effective_from
        assert config.effective_to == effective_to

    @pytest.mark.asyncio
    async def test_create_option_config_with_region(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_dealer_id: uuid.UUID,
        sample_option_id: uuid.UUID,
        mock_vehicle_option: VehicleOption,
    ) -> None:
        """Test option configuration creation with region."""
        # Arrange
        region = "US-WEST"
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_vehicle_option
        mock_db_session.execute.return_value = mock_result

        # Act
        config = await dealer_service.create_option_config(
            dealer_id=sample_dealer_id,
            option_id=sample_option_id,
            region=region,
        )

        # Assert
        assert config.region == region

    @pytest.mark.asyncio
    async def test_create_option_config_option_not_found(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_dealer_id: uuid.UUID,
        sample_option_id: uuid.UUID,
    ) -> None:
        """Test option configuration creation with non-existent option."""
        # Arrange
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(DealerValidationError) as exc_info:
            await dealer_service.create_option_config(
                dealer_id=sample_dealer_id,
                option_id=sample_option_id,
            )

        assert "Vehicle option not found" in str(exc_info.value)
        assert exc_info.value.code == "VALIDATION_ERROR"
        mock_db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_option_config_invalid_date_range(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_dealer_id: uuid.UUID,
        sample_option_id: uuid.UUID,
        mock_vehicle_option: VehicleOption,
    ) -> None:
        """Test option configuration creation with invalid date range."""
        # Arrange
        effective_from = datetime.utcnow()
        effective_to = effective_from - timedelta(days=1)
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_vehicle_option
        mock_db_session.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(DealerValidationError) as exc_info:
            await dealer_service.create_option_config(
                dealer_id=sample_dealer_id,
                option_id=sample_option_id,
                effective_from=effective_from,
                effective_to=effective_to,
            )

        assert "End date must be after start date" in str(exc_info.value)
        mock_db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "invalid_price,error_message",
        [
            (Decimal("-100.00"), "Custom price cannot be negative"),
            (Decimal("150000.00"), "Custom price exceeds maximum allowed value"),
        ],
    )
    async def test_create_option_config_invalid_price(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_dealer_id: uuid.UUID,
        sample_option_id: uuid.UUID,
        mock_vehicle_option: VehicleOption,
        invalid_price: Decimal,
        error_message: str,
    ) -> None:
        """Test option configuration creation with invalid price."""
        # Arrange
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_vehicle_option
        mock_db_session.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(DealerValidationError) as exc_info:
            await dealer_service.create_option_config(
                dealer_id=sample_dealer_id,
                option_id=sample_option_id,
                custom_price=invalid_price,
            )

        assert error_message in str(exc_info.value)
        mock_db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_option_config_integrity_error(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_dealer_id: uuid.UUID,
        sample_option_id: uuid.UUID,
        mock_vehicle_option: VehicleOption,
    ) -> None:
        """Test option configuration creation with integrity error."""
        # Arrange
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_vehicle_option
        mock_db_session.execute.return_value = mock_result
        mock_db_session.flush.side_effect = IntegrityError("", "", "")

        # Act & Assert
        with pytest.raises(DealerManagementError) as exc_info:
            await dealer_service.create_option_config(
                dealer_id=sample_dealer_id,
                option_id=sample_option_id,
            )

        assert exc_info.value.code == "INTEGRITY_ERROR"
        assert "Configuration already exists" in str(exc_info.value)
        mock_db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_option_config_generic_error(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_dealer_id: uuid.UUID,
        sample_option_id: uuid.UUID,
        mock_vehicle_option: VehicleOption,
    ) -> None:
        """Test option configuration creation with generic error."""
        # Arrange
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_vehicle_option
        mock_db_session.execute.return_value = mock_result
        mock_db_session.flush.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(DealerManagementError) as exc_info:
            await dealer_service.create_option_config(
                dealer_id=sample_dealer_id,
                option_id=sample_option_id,
            )

        assert exc_info.value.code == "CREATE_ERROR"
        mock_db_session.rollback.assert_called_once()


# ============================================================================
# Unit Tests - Create Package Configuration
# ============================================================================


class TestCreatePackageConfig:
    """Test suite for creating dealer package configurations."""

    @pytest.mark.asyncio
    async def test_create_package_config_success(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_dealer_id: uuid.UUID,
        sample_package_id: uuid.UUID,
        mock_package: Package,
    ) -> None:
        """Test successful package configuration creation."""
        # Arrange
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_package
        mock_db_session.execute.return_value = mock_result

        # Act
        config = await dealer_service.create_package_config(
            dealer_id=sample_dealer_id,
            package_id=sample_package_id,
            is_available=True,
        )

        # Assert
        assert config is not None
        assert config.dealer_id == sample_dealer_id
        assert config.package_id == sample_package_id
        assert config.is_available is True
        mock_db_session.add.assert_called_once()
        mock_db_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_package_config_with_all_parameters(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_dealer_id: uuid.UUID,
        sample_package_id: uuid.UUID,
        mock_package: Package,
    ) -> None:
        """Test package configuration creation with all parameters."""
        # Arrange
        custom_price = Decimal("4000.00")
        effective_from = datetime.utcnow()
        effective_to = effective_from + timedelta(days=60)
        region = "EU-CENTRAL"
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_package
        mock_db_session.execute.return_value = mock_result

        # Act
        config = await dealer_service.create_package_config(
            dealer_id=sample_dealer_id,
            package_id=sample_package_id,
            is_available=False,
            custom_price=custom_price,
            effective_from=effective_from,
            effective_to=effective_to,
            region=region,
        )

        # Assert
        assert config.is_available is False
        assert config.custom_price == custom_price
        assert config.effective_from == effective_from
        assert config.effective_to == effective_to
        assert config.region == region

    @pytest.mark.asyncio
    async def test_create_package_config_package_not_found(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_dealer_id: uuid.UUID,
        sample_package_id: uuid.UUID,
    ) -> None:
        """Test package configuration creation with non-existent package."""
        # Arrange
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(DealerValidationError) as exc_info:
            await dealer_service.create_package_config(
                dealer_id=sample_dealer_id,
                package_id=sample_package_id,
            )

        assert "Vehicle package not found" in str(exc_info.value)
        mock_db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_package_config_integrity_error(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_dealer_id: uuid.UUID,
        sample_package_id: uuid.UUID,
        mock_package: Package,
    ) -> None:
        """Test package configuration creation with integrity error."""
        # Arrange
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_package
        mock_db_session.execute.return_value = mock_result
        mock_db_session.flush.side_effect = IntegrityError("", "", "")

        # Act & Assert
        with pytest.raises(DealerManagementError) as exc_info:
            await dealer_service.create_package_config(
                dealer_id=sample_dealer_id,
                package_id=sample_package_id,
            )

        assert exc_info.value.code == "INTEGRITY_ERROR"
        mock_db_session.rollback.assert_called_once()


# ============================================================================
# Unit Tests - Update Option Availability
# ============================================================================


class TestUpdateOptionAvailability:
    """Test suite for updating option availability."""

    @pytest.mark.asyncio
    async def test_update_option_availability_success(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_config_id: uuid.UUID,
        mock_option_config: DealerOptionConfig,
    ) -> None:
        """Test successful option availability update."""
        # Arrange
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_option_config
        mock_db_session.execute.return_value = mock_result

        # Act
        config = await dealer_service.update_option_availability(
            config_id=sample_config_id,
            is_available=False,
        )

        # Assert
        assert config is not None
        mock_option_config.update_availability.assert_called_once_with(False)
        mock_db_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_option_availability_not_found(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_config_id: uuid.UUID,
    ) -> None:
        """Test option availability update with non-existent config."""
        # Arrange
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(DealerConfigurationNotFoundError) as exc_info:
            await dealer_service.update_option_availability(
                config_id=sample_config_id,
                is_available=False,
            )

        assert str(sample_config_id) in str(exc_info.value)
        mock_db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_option_availability_generic_error(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_config_id: uuid.UUID,
        mock_option_config: DealerOptionConfig,
    ) -> None:
        """Test option availability update with generic error."""
        # Arrange
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_option_config
        mock_db_session.execute.return_value = mock_result
        mock_db_session.flush.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(DealerManagementError) as exc_info:
            await dealer_service.update_option_availability(
                config_id=sample_config_id,
                is_available=False,
            )

        assert exc_info.value.code == "UPDATE_ERROR"
        mock_db_session.rollback.assert_called_once()


# ============================================================================
# Unit Tests - Update Package Availability
# ============================================================================


class TestUpdatePackageAvailability:
    """Test suite for updating package availability."""

    @pytest.mark.asyncio
    async def test_update_package_availability_success(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_config_id: uuid.UUID,
        mock_package_config: DealerPackageConfig,
    ) -> None:
        """Test successful package availability update."""
        # Arrange
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_package_config
        mock_db_session.execute.return_value = mock_result

        # Act
        config = await dealer_service.update_package_availability(
            config_id=sample_config_id,
            is_available=True,
        )

        # Assert
        assert config is not None
        mock_package_config.update_availability.assert_called_once_with(True)
        mock_db_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_package_availability_not_found(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_config_id: uuid.UUID,
    ) -> None:
        """Test package availability update with non-existent config."""
        # Arrange
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(DealerConfigurationNotFoundError):
            await dealer_service.update_package_availability(
                config_id=sample_config_id,
                is_available=True,
            )

        mock_db_session.rollback.assert_called_once()


# ============================================================================
# Unit Tests - Update Option Pricing
# ============================================================================


class TestUpdateOptionPricing:
    """Test suite for updating option pricing."""

    @pytest.mark.asyncio
    async def test_update_option_pricing_success(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_config_id: uuid.UUID,
        mock_option_config: DealerOptionConfig,
    ) -> None:
        """Test successful option pricing update."""
        # Arrange
        new_price = Decimal("2500.00")
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_option_config
        mock_db_session.execute.return_value = mock_result

        # Act
        config = await dealer_service.update_option_pricing(
            config_id=sample_config_id,
            custom_price=new_price,
        )

        # Assert
        assert config is not None
        mock_option_config.update_custom_price.assert_called_once_with(new_price)
        mock_db_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_option_pricing_remove_override(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_config_id: uuid.UUID,
        mock_option_config: DealerOptionConfig,
    ) -> None:
        """Test removing option price override."""
        # Arrange
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_option_config
        mock_db_session.execute.return_value = mock_result

        # Act
        config = await dealer_service.update_option_pricing(
            config_id=sample_config_id,
            custom_price=None,
        )

        # Assert
        assert config is not None
        mock_option_config.update_custom_price.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_update_option_pricing_validation_error(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_config_id: uuid.UUID,
        mock_option_config: DealerOptionConfig,
    ) -> None:
        """Test option pricing update with validation error."""
        # Arrange
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_option_config
        mock_db_session.execute.return_value = mock_result
        mock_option_config.update_custom_price.side_effect = ValueError(
            "Invalid price"
        )

        # Act & Assert
        with pytest.raises(DealerValidationError) as exc_info:
            await dealer_service.update_option_pricing(
                config_id=sample_config_id,
                custom_price=Decimal("-100.00"),
            )

        assert "Invalid price" in str(exc_info.value)
        mock_db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_option_pricing_not_found(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_config_id: uuid.UUID,
    ) -> None:
        """Test option pricing update with non-existent config."""
        # Arrange
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(DealerConfigurationNotFoundError):
            await dealer_service.update_option_pricing(
                config_id=sample_config_id,
                custom_price=Decimal("1000.00"),
            )

        mock_db_session.rollback.assert_called_once()


# ============================================================================
# Unit Tests - Update Package Pricing
# ============================================================================


class TestUpdatePackagePricing:
    """Test suite for updating package pricing."""

    @pytest.mark.asyncio
    async def test_update_package_pricing_success(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_config_id: uuid.UUID,
        mock_package_config: DealerPackageConfig,
    ) -> None:
        """Test successful package pricing update."""
        # Arrange
        new_price = Decimal("5000.00")
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_package_config
        mock_db_session.execute.return_value = mock_result

        # Act
        config = await dealer_service.update_package_pricing(
            config_id=sample_config_id,
            custom_price=new_price,
        )

        # Assert
        assert config is not None
        mock_package_config.update_custom_price.assert_called_once_with(new_price)
        mock_db_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_package_pricing_validation_error(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_config_id: uuid.UUID,
        mock_package_config: DealerPackageConfig,
    ) -> None:
        """Test package pricing update with validation error."""
        # Arrange
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_package_config
        mock_db_session.execute.return_value = mock_result
        mock_package_config.update_custom_price.side_effect = ValueError(
            "Price too high"
        )

        # Act & Assert
        with pytest.raises(DealerValidationError):
            await dealer_service.update_package_pricing(
                config_id=sample_config_id,
                custom_price=Decimal("200000.00"),
            )

        mock_db_session.rollback.assert_called_once()


# ============================================================================
# Unit Tests - Get Dealer Configurations
# ============================================================================


class TestGetDealerConfigurations:
    """Test suite for retrieving dealer configurations."""

    @pytest.mark.asyncio
    async def test_get_dealer_option_configs_success(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_dealer_id: uuid.UUID,
        mock_option_config: DealerOptionConfig,
    ) -> None:
        """Test successful retrieval of dealer option configurations."""
        # Arrange
        mock_result = AsyncMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_option_config]
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute.return_value = mock_result

        # Act
        configs = await dealer_service.get_dealer_option_configs(
            dealer_id=sample_dealer_id,
            active_only=True,
        )

        # Assert
        assert len(configs) == 1
        assert configs[0] == mock_option_config
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_dealer_option_configs_with_region(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_dealer_id: uuid.UUID,
        mock_option_config: DealerOptionConfig,
    ) -> None:
        """Test retrieval of dealer option configurations with region filter."""
        # Arrange
        region = "US-EAST"
        mock_result = AsyncMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_option_config]
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute.return_value = mock_result

        # Act
        configs = await dealer_service.get_dealer_option_configs(
            dealer_id=sample_dealer_id,
            active_only=True,
            region=region,
        )

        # Assert
        assert len(configs) == 1
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_dealer_option_configs_all_inactive(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_dealer_id: uuid.UUID,
        mock_option_config: DealerOptionConfig,
    ) -> None:
        """Test retrieval including inactive configurations."""
        # Arrange
        mock_result = AsyncMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_option_config]
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute.return_value = mock_result

        # Act
        configs = await dealer_service.get_dealer_option_configs(
            dealer_id=sample_dealer_id,
            active_only=False,
        )

        # Assert
        assert len(configs) == 1
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_dealer_option_configs_empty_result(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_dealer_id: uuid.UUID,
    ) -> None:
        """Test retrieval with no configurations found."""
        # Arrange
        mock_result = AsyncMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute.return_value = mock_result

        # Act
        configs = await dealer_service.get_dealer_option_configs(
            dealer_id=sample_dealer_id,
        )

        # Assert
        assert len(configs) == 0

    @pytest.mark.asyncio
    async def test_get_dealer_option_configs_error(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_dealer_id: uuid.UUID,
    ) -> None:
        """Test retrieval with database error."""
        # Arrange
        mock_db_session.execute.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(DealerManagementError) as exc_info:
            await dealer_service.get_dealer_option_configs(
                dealer_id=sample_dealer_id,
            )

        assert exc_info.value.code == "RETRIEVAL_ERROR"

    @pytest.mark.asyncio
    async def test_get_dealer_package_configs_success(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_dealer_id: uuid.UUID,
        mock_package_config: DealerPackageConfig,
    ) -> None:
        """Test successful retrieval of dealer package configurations."""
        # Arrange
        mock_result = AsyncMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_package_config]
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute.return_value = mock_result

        # Act
        configs = await dealer_service.get_dealer_package_configs(
            dealer_id=sample_dealer_id,
        )

        # Assert
        assert len(configs) == 1
        assert configs[0] == mock_package_config

    @pytest.mark.asyncio
    async def test_get_dealer_package_configs_error(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_dealer_id: uuid.UUID,
    ) -> None:
        """Test package configuration retrieval with error."""
        # Arrange
        mock_db_session.execute.side_effect = SQLAlchemyError("DB error")

        # Act & Assert
        with pytest.raises(DealerManagementError) as exc_info:
            await dealer_service.get_dealer_package_configs(
                dealer_id=sample_dealer_id,
            )

        assert exc_info.value.code == "RETRIEVAL_ERROR"


# ============================================================================
# Unit Tests - Bulk Operations
# ============================================================================


class TestBulkOperations:
    """Test suite for bulk update operations."""

    @pytest.mark.asyncio
    async def test_bulk_update_option_availability_success(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_dealer_id: uuid.UUID,
    ) -> None:
        """Test successful bulk option availability update."""
        # Arrange
        option_ids = [uuid.uuid4() for _ in range(5)]
        mock_result = AsyncMock()
        mock_result.rowcount = 5
        mock_db_session.execute.return_value = mock_result

        # Act
        updated_count = await dealer_service.bulk_update_option_availability(
            dealer_id=sample_dealer_id,
            option_ids=option_ids,
            is_available=False,
        )

        # Assert
        assert updated_count == 5
        mock_db_session.execute.assert_called_once()
        mock_db_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_update_option_availability_partial(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_dealer_id: uuid.UUID,
    ) -> None:
        """Test bulk option availability update with partial success."""
        # Arrange
        option_ids = [uuid.uuid4() for _ in range(10)]
        mock_result = AsyncMock()
        mock_result.rowcount = 7
        mock_db_session.execute.return_value = mock_result

        # Act
        updated_count = await dealer_service.bulk_update_option_availability(
            dealer_id=sample_dealer_id,
            option_ids=option_ids,
            is_available=True,
        )

        # Assert
        assert updated_count == 7

    @pytest.mark.asyncio
    async def test_bulk_update_option_availability_empty_list(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_dealer_id: uuid.UUID,
    ) -> None:
        """Test bulk option availability update with empty list."""
        # Arrange
        mock_result = AsyncMock()
        mock_result.rowcount = 0
        mock_db_session.execute.return_value = mock_result

        # Act
        updated_count = await dealer_service.bulk_update_option_availability(
            dealer_id=sample_dealer_id,
            option_ids=[],
            is_available=True,
        )

        # Assert
        assert updated_count == 0

    @pytest.mark.asyncio
    async def test_bulk_update_option_availability_error(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_dealer_id: uuid.UUID,
    ) -> None:
        """Test bulk option availability update with error."""
        # Arrange
        option_ids = [uuid.uuid4() for _ in range(3)]
        mock_db_session.execute.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(DealerManagementError) as exc_info:
            await dealer_service.bulk_update_option_availability(
                dealer_id=sample_dealer_id,
                option_ids=option_ids,
                is_available=False,
            )

        assert exc_info.value.code == "BULK_UPDATE_ERROR"
        mock_db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_update_package_availability_success(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_dealer_id: uuid.UUID,
    ) -> None:
        """Test successful bulk package availability update."""
        # Arrange
        package_ids = [uuid.uuid4() for _ in range(3)]
        mock_result = AsyncMock()
        mock_result.rowcount = 3
        mock_db_session.execute.return_value = mock_result

        # Act
        updated_count = await dealer_service.bulk_update_package_availability(
            dealer_id=sample_dealer_id,
            package_ids=package_ids,
            is_available=True,
        )

        # Assert
        assert updated_count == 3
        mock_db_session.execute.assert_called_once()
        mock_db_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_update_package_availability_error(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_dealer_id: uuid.UUID,
    ) -> None:
        """Test bulk package availability update with error."""
        # Arrange
        package_ids = [uuid.uuid4() for _ in range(2)]
        mock_db_session.execute.side_effect = SQLAlchemyError("DB error")

        # Act & Assert
        with pytest.raises(DealerManagementError) as exc_info:
            await dealer_service.bulk_update_package_availability(
                dealer_id=sample_dealer_id,
                package_ids=package_ids,
                is_available=False,
            )

        assert exc_info.value.code == "BULK_UPDATE_ERROR"
        mock_db_session.rollback.assert_called_once()


# ============================================================================
# Unit Tests - Delete Operations
# ============================================================================


class TestDeleteOperations:
    """Test suite for delete operations."""

    @pytest.mark.asyncio
    async def test_delete_option_config_success(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_config_id: uuid.UUID,
    ) -> None:
        """Test successful option configuration deletion."""
        # Arrange
        mock_result = AsyncMock()
        mock_result.rowcount = 1
        mock_db_session.execute.return_value = mock_result

        # Act
        await dealer_service.delete_option_config(config_id=sample_config_id)

        # Assert
        mock_db_session.execute.assert_called_once()
        mock_db_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_option_config_not_found(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_config_id: uuid.UUID,
    ) -> None:
        """Test option configuration deletion with non-existent config."""
        # Arrange
        mock_result = AsyncMock()
        mock_result.rowcount = 0
        mock_db_session.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(DealerConfigurationNotFoundError):
            await dealer_service.delete_option_config(config_id=sample_config_id)

        mock_db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_option_config_error(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_config_id: uuid.UUID,
    ) -> None:
        """Test option configuration deletion with error."""
        # Arrange
        mock_db_session.execute.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(DealerManagementError) as exc_info:
            await dealer_service.delete_option_config(config_id=sample_config_id)

        assert exc_info.value.code == "DELETE_ERROR"
        mock_db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_package_config_success(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_config_id: uuid.UUID,
    ) -> None:
        """Test successful package configuration deletion."""
        # Arrange
        mock_result = AsyncMock()
        mock_result.rowcount = 1
        mock_db_session.execute.return_value = mock_result

        # Act
        await dealer_service.delete_package_config(config_id=sample_config_id)

        # Assert
        mock_db_session.execute.assert_called_once()
        mock_db_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_package_config_not_found(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_config_id: uuid.UUID,
    ) -> None:
        """Test package configuration deletion with non-existent config."""
        # Arrange
        mock_result = AsyncMock()
        mock_result.rowcount = 0
        mock_db_session.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(DealerConfigurationNotFoundError):
            await dealer_service.delete_package_config(config_id=sample_config_id)

        mock_db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_package_config_error(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_config_id: uuid.UUID,
    ) -> None:
        """Test package configuration deletion with error."""
        # Arrange
        mock_db_session.execute.side_effect = SQLAlchemyError("DB error")

        # Act & Assert
        with pytest.raises(DealerManagementError) as exc_info:
            await dealer_service.delete_package_config(config_id=sample_config_id)

        assert exc_info.value.code == "DELETE_ERROR"
        mock_db_session.rollback.assert_called_once()


# ============================================================================
# Unit Tests - Exception Handling
# ============================================================================


class TestExceptionHandling:
    """Test suite for exception handling and error scenarios."""

    def test_dealer_management_error_initialization(self) -> None:
        """Test DealerManagementError initialization."""
        error = DealerManagementError(
            "Test error",
            code="TEST_ERROR",
            dealer_id="123",
            extra_info="test",
        )

        assert str(error) == "Test error"
        assert error.code == "TEST_ERROR"
        assert error.context["dealer_id"] == "123"
        assert error.context["extra_info"] == "test"

    def test_dealer_configuration_not_found_error(self) -> None:
        """Test DealerConfigurationNotFoundError initialization."""
        config_id = uuid.uuid4()
        error = DealerConfigurationNotFoundError(
            config_id,
            dealer_id="dealer-123",
        )

        assert str(config_id) in str(error)
        assert error.code == "CONFIG_NOT_FOUND"
        assert error.context["config_id"] == str(config_id)
        assert error.context["dealer_id"] == "dealer-123"

    def test_dealer_validation_error(self) -> None:
        """Test DealerValidationError initialization."""
        error = DealerValidationError(
            "Invalid price",
            price=-100,
            field="custom_price",
        )

        assert "Invalid price" in str(error)
        assert error.code == "VALIDATION_ERROR"
        assert error.context["price"] == -100
        assert error.context["field"] == "custom_price"


# ============================================================================
# Integration Tests - Complex Scenarios
# ============================================================================


class TestComplexScenarios:
    """Test suite for complex integration scenarios."""

    @pytest.mark.asyncio
    async def test_create_and_update_option_config_workflow(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_dealer_id: uuid.UUID,
        sample_option_id: uuid.UUID,
        mock_vehicle_option: VehicleOption,
    ) -> None:
        """Test complete workflow of creating and updating option config."""
        # Arrange - Create
        mock_result_create = AsyncMock()
        mock_result_create.scalar_one_or_none.return_value = mock_vehicle_option

        # Arrange - Update
        created_config = MagicMock(spec=DealerOptionConfig)
        created_config.id = uuid.uuid4()
        created_config.update_availability = MagicMock()
        mock_result_update = AsyncMock()
        mock_result_update.scalar_one_or_none.return_value = created_config

        mock_db_session.execute.side_effect = [
            mock_result_create,
            mock_result_update,
        ]

        # Act - Create
        config = await dealer_service.create_option_config(
            dealer_id=sample_dealer_id,
            option_id=sample_option_id,
            is_available=True,
        )

        # Act - Update
        updated_config = await dealer_service.update_option_availability(
            config_id=created_config.id,
            is_available=False,
        )

        # Assert
        assert config is not None
        assert updated_config is not None
        created_config.update_availability.assert_called_once_with(False)

    @pytest.mark.asyncio
    async def test_multiple_region_configurations(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_dealer_id: uuid.UUID,
        sample_option_id: uuid.UUID,
        mock_vehicle_option: VehicleOption,
    ) -> None:
        """Test creating configurations for multiple regions."""
        # Arrange
        regions = ["US-EAST", "US-WEST", "EU-CENTRAL"]
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_vehicle_option
        mock_db_session.execute.return_value = mock_result

        # Act
        configs = []
        for region in regions:
            config = await dealer_service.create_option_config(
                dealer_id=sample_dealer_id,
                option_id=sample_option_id,
                region=region,
            )
            configs.append(config)

        # Assert
        assert len(configs) == 3
        assert all(config.region in regions for config in configs)

    @pytest.mark.asyncio
    async def test_concurrent_bulk_updates(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_dealer_id: uuid.UUID,
    ) -> None:
        """Test multiple bulk updates in sequence."""
        # Arrange
        option_ids_batch1 = [uuid.uuid4() for _ in range(5)]
        option_ids_batch2 = [uuid.uuid4() for _ in range(3)]

        mock_result1 = AsyncMock()
        mock_result1.rowcount = 5
        mock_result2 = AsyncMock()
        mock_result2.rowcount = 3

        mock_db_session.execute.side_effect = [mock_result1, mock_result2]

        # Act
        count1 = await dealer_service.bulk_update_option_availability(
            dealer_id=sample_dealer_id,
            option_ids=option_ids_batch1,
            is_available=False,
        )

        count2 = await dealer_service.bulk_update_option_availability(
            dealer_id=sample_dealer_id,
            option_ids=option_ids_batch2,
            is_available=True,
        )

        # Assert
        assert count1 == 5
        assert count2 == 3
        assert mock_db_session.execute.call_count == 2


# ============================================================================
# Performance Tests
# ============================================================================


class TestPerformance:
    """Test suite for performance validation."""

    @pytest.mark.asyncio
    async def test_bulk_update_large_dataset_performance(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_dealer_id: uuid.UUID,
    ) -> None:
        """Test bulk update performance with large dataset."""
        # Arrange
        option_ids = [uuid.uuid4() for _ in range(1000)]
        mock_result = AsyncMock()
        mock_result.rowcount = 1000
        mock_db_session.execute.return_value = mock_result

        # Act
        import time

        start_time = time.time()
        updated_count = await dealer_service.bulk_update_option_availability(
            dealer_id=sample_dealer_id,
            option_ids=option_ids,
            is_available=True,
        )
        elapsed_time = time.time() - start_time

        # Assert
        assert updated_count == 1000
        assert elapsed_time < 1.0  # Should complete in under 1 second

    @pytest.mark.asyncio
    async def test_get_configs_response_time(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_dealer_id: uuid.UUID,
    ) -> None:
        """Test configuration retrieval response time."""
        # Arrange
        mock_configs = [MagicMock(spec=DealerOptionConfig) for _ in range(100)]
        mock_result = AsyncMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_configs
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute.return_value = mock_result

        # Act
        import time

        start_time = time.time()
        configs = await dealer_service.get_dealer_option_configs(
            dealer_id=sample_dealer_id,
        )
        elapsed_time = time.time() - start_time

        # Assert
        assert len(configs) == 100
        assert elapsed_time < 0.5  # Should complete in under 500ms


# ============================================================================
# Edge Cases and Boundary Tests
# ============================================================================


class TestEdgeCases:
    """Test suite for edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_create_config_with_zero_price(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_dealer_id: uuid.UUID,
        sample_option_id: uuid.UUID,
        mock_vehicle_option: VehicleOption,
    ) -> None:
        """Test creating configuration with zero price."""
        # Arrange
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_vehicle_option
        mock_db_session.execute.return_value = mock_result

        # Act
        config = await dealer_service.create_option_config(
            dealer_id=sample_dealer_id,
            option_id=sample_option_id,
            custom_price=Decimal("0.00"),
        )

        # Assert
        assert config.custom_price == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_create_config_with_max_price(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_dealer_id: uuid.UUID,
        sample_option_id: uuid.UUID,
        mock_vehicle_option: VehicleOption,
    ) -> None:
        """Test creating configuration with maximum allowed price."""
        # Arrange
        max_price = Decimal("100000.00")
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_vehicle_option
        mock_db_session.execute.return_value = mock_result

        # Act
        config = await dealer_service.create_option_config(
            dealer_id=sample_dealer_id,
            option_id=sample_option_id,
            custom_price=max_price,
        )

        # Assert
        assert config.custom_price == max_price

    @pytest.mark.asyncio
    async def test_create_config_with_same_start_end_date(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_dealer_id: uuid.UUID,
        sample_option_id: uuid.UUID,
        mock_vehicle_option: VehicleOption,
    ) -> None:
        """Test creating configuration with same start and end date."""
        # Arrange
        same_date = datetime.utcnow()
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_vehicle_option
        mock_db_session.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(DealerValidationError) as exc_info:
            await dealer_service.create_option_config(
                dealer_id=sample_dealer_id,
                option_id=sample_option_id,
                effective_from=same_date,
                effective_to=same_date,
            )

        assert "End date must be after start date" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_bulk_update_with_single_item(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_dealer_id: uuid.UUID,
    ) -> None:
        """Test bulk update with single item."""
        # Arrange
        option_ids = [uuid.uuid4()]
        mock_result = AsyncMock()
        mock_result.rowcount = 1
        mock_db_session.execute.return_value = mock_result

        # Act
        updated_count = await dealer_service.bulk_update_option_availability(
            dealer_id=sample_dealer_id,
            option_ids=option_ids,
            is_available=True,
        )

        # Assert
        assert updated_count == 1

    @pytest.mark.asyncio
    async def test_get_configs_with_none_region(
        self,
        dealer_service: DealerManagementService,
        mock_db_session: AsyncMock,
        sample_dealer_id: uuid.UUID,
    ) -> None:
        """Test getting configurations with None region filter."""
        # Arrange
        mock_result = AsyncMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute.return_value = mock_result

        # Act
        configs = await dealer_service.get_dealer_option_configs(
            dealer_id=sample_dealer_id,
            region=None,
        )

        # Assert
        assert len(configs) == 0
        mock_db_session.execute.assert_called_once()