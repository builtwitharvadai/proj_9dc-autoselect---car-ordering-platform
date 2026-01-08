"""
Comprehensive test suite for pricing calculation engine.

Tests cover pricing calculations including base price, option pricing,
package discounts, tax calculations, total pricing, caching behavior,
and regional pricing variations.
"""

import uuid
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.services.configuration.pricing_engine import (
    PricingEngine,
    PricingError,
    PricingValidationError,
    PricingCalculationError,
)
from src.database.models.vehicle import Vehicle
from src.database.models.vehicle_option import VehicleOption
from src.database.models.package import Package


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for caching tests."""
    mock_client = AsyncMock()
    mock_client.get_json = AsyncMock(return_value=None)
    mock_client.set_json = AsyncMock()
    mock_client.delete_pattern = AsyncMock(return_value=0)
    return mock_client


@pytest.fixture
def pricing_engine(mock_redis_client):
    """Create pricing engine instance with mocked Redis."""
    return PricingEngine(
        redis_client=mock_redis_client,
        enable_caching=True,
        default_region="US",
    )


@pytest.fixture
def pricing_engine_no_cache():
    """Create pricing engine instance without caching."""
    return PricingEngine(
        redis_client=None,
        enable_caching=False,
        default_region="US",
    )


@pytest.fixture
def sample_vehicle():
    """Create sample vehicle for testing."""
    vehicle = Mock(spec=Vehicle)
    vehicle.id = uuid.uuid4()
    vehicle.base_price = Decimal("35000.00")
    vehicle.destination_charge = Decimal("1200.00")
    return vehicle


@pytest.fixture
def sample_option():
    """Create sample vehicle option for testing."""
    option = Mock(spec=VehicleOption)
    option.id = uuid.uuid4()
    option.name = "Premium Sound System"
    option.price = Decimal("1500.00")
    return option


@pytest.fixture
def sample_options():
    """Create list of sample vehicle options."""
    options = []
    for i, (name, price) in enumerate(
        [
            ("Premium Sound System", "1500.00"),
            ("Leather Seats", "2000.00"),
            ("Sunroof", "1200.00"),
        ]
    ):
        option = Mock(spec=VehicleOption)
        option.id = uuid.uuid4()
        option.name = name
        option.price = Decimal(price)
        options.append(option)
    return options


@pytest.fixture
def sample_package():
    """Create sample package for testing."""
    package = Mock(spec=Package)
    package.id = uuid.uuid4()
    package.name = "Premium Package"
    package.discount_percentage = Decimal("10.00")
    return package


@pytest.fixture
def sample_package_with_options(sample_package, sample_options):
    """Create sample package with included options."""
    return (sample_package, sample_options[:2])


# ============================================================================
# Unit Tests - Initialization
# ============================================================================


class TestPricingEngineInitialization:
    """Test pricing engine initialization."""

    def test_initialization_with_defaults(self):
        """Test initialization with default parameters."""
        engine = PricingEngine()

        assert engine._redis_client is None
        assert engine._enable_caching is True
        assert engine._default_region == "US"

    def test_initialization_with_custom_params(self, mock_redis_client):
        """Test initialization with custom parameters."""
        engine = PricingEngine(
            redis_client=mock_redis_client,
            enable_caching=False,
            default_region="CA",
        )

        assert engine._redis_client == mock_redis_client
        assert engine._enable_caching is False
        assert engine._default_region == "CA"

    def test_initialization_logs_configuration(self, mock_redis_client):
        """Test that initialization logs configuration."""
        with patch("src.services.configuration.pricing_engine.logger") as mock_logger:
            PricingEngine(
                redis_client=mock_redis_client,
                enable_caching=True,
                default_region="NY",
            )

            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert "Pricing engine initialized" in call_args[0][0]


# ============================================================================
# Unit Tests - Cache Key Generation
# ============================================================================


class TestCacheKeyGeneration:
    """Test cache key generation."""

    def test_make_cache_key_single_part(self, pricing_engine):
        """Test cache key generation with single part."""
        key = pricing_engine._make_cache_key("vehicle_123")

        assert key == "pricing:vehicle_123"

    def test_make_cache_key_multiple_parts(self, pricing_engine):
        """Test cache key generation with multiple parts."""
        key = pricing_engine._make_cache_key("vehicle_123", "option_456", "CA")

        assert key == "pricing:vehicle_123:option_456:CA"

    def test_make_cache_key_with_none_values(self, pricing_engine):
        """Test cache key generation filters None values."""
        key = pricing_engine._make_cache_key("vehicle_123", None, "CA")

        assert key == "pricing:vehicle_123:CA"

    def test_make_cache_key_with_uuid(self, pricing_engine):
        """Test cache key generation with UUID."""
        vehicle_id = uuid.uuid4()
        key = pricing_engine._make_cache_key(str(vehicle_id))

        assert key == f"pricing:{str(vehicle_id)}"


# ============================================================================
# Unit Tests - Redis Client Management
# ============================================================================


class TestRedisClientManagement:
    """Test Redis client management."""

    @pytest.mark.asyncio
    async def test_get_redis_client_when_disabled(self, pricing_engine_no_cache):
        """Test getting Redis client when caching is disabled."""
        client = await pricing_engine_no_cache._get_redis_client()

        assert client is None

    @pytest.mark.asyncio
    async def test_get_redis_client_when_already_set(self, pricing_engine):
        """Test getting Redis client when already set."""
        client = await pricing_engine._get_redis_client()

        assert client == pricing_engine._redis_client

    @pytest.mark.asyncio
    async def test_get_redis_client_initialization_failure(self):
        """Test Redis client initialization failure."""
        engine = PricingEngine(redis_client=None, enable_caching=True)

        with patch(
            "src.services.configuration.pricing_engine.get_redis_client",
            side_effect=Exception("Connection failed"),
        ):
            with patch(
                "src.services.configuration.pricing_engine.logger"
            ) as mock_logger:
                client = await engine._get_redis_client()

                assert client is None
                mock_logger.warning.assert_called_once()


# ============================================================================
# Unit Tests - Cache Operations
# ============================================================================


class TestCacheOperations:
    """Test cache operations."""

    @pytest.mark.asyncio
    async def test_get_cached_price_hit(self, pricing_engine, mock_redis_client):
        """Test getting cached price with cache hit."""
        cached_data = {"total": 40000.0, "base_price": 35000.0}
        mock_redis_client.get_json.return_value = cached_data

        result = await pricing_engine._get_cached_price("test_key")

        assert result == cached_data
        mock_redis_client.get_json.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_get_cached_price_miss(self, pricing_engine, mock_redis_client):
        """Test getting cached price with cache miss."""
        mock_redis_client.get_json.return_value = None

        result = await pricing_engine._get_cached_price("test_key")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_cached_price_error(self, pricing_engine, mock_redis_client):
        """Test getting cached price with error."""
        mock_redis_client.get_json.side_effect = Exception("Redis error")

        with patch("src.services.configuration.pricing_engine.logger") as mock_logger:
            result = await pricing_engine._get_cached_price("test_key")

            assert result is None
            mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_cached_price_success(self, pricing_engine, mock_redis_client):
        """Test setting cached price successfully."""
        price_data = {"total": 40000.0}

        await pricing_engine._set_cached_price("test_key", price_data)

        mock_redis_client.set_json.assert_called_once_with(
            "test_key", price_data, ex=3600
        )

    @pytest.mark.asyncio
    async def test_set_cached_price_error(self, pricing_engine, mock_redis_client):
        """Test setting cached price with error."""
        mock_redis_client.set_json.side_effect = Exception("Redis error")

        with patch("src.services.configuration.pricing_engine.logger") as mock_logger:
            await pricing_engine._set_cached_price("test_key", {})

            mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_operations_when_disabled(self, pricing_engine_no_cache):
        """Test cache operations when caching is disabled."""
        result = await pricing_engine_no_cache._get_cached_price("test_key")
        assert result is None

        await pricing_engine_no_cache._set_cached_price("test_key", {})
        # Should not raise exception


# ============================================================================
# Unit Tests - Price Validation
# ============================================================================


class TestPriceValidation:
    """Test price validation."""

    def test_validate_price_valid(self, pricing_engine):
        """Test validation of valid price."""
        pricing_engine._validate_price(Decimal("1000.00"), "test_price")
        # Should not raise exception

    def test_validate_price_zero(self, pricing_engine):
        """Test validation of zero price."""
        pricing_engine._validate_price(Decimal("0.00"), "test_price")
        # Should not raise exception

    def test_validate_price_negative(self, pricing_engine):
        """Test validation of negative price."""
        with pytest.raises(PricingValidationError) as exc_info:
            pricing_engine._validate_price(Decimal("-100.00"), "test_price")

        assert "cannot be negative" in str(exc_info.value)
        assert exc_info.value.context["field"] == "test_price"
        assert exc_info.value.context["value"] == -100.0

    def test_validate_price_exceeds_maximum(self, pricing_engine):
        """Test validation of price exceeding maximum."""
        with pytest.raises(PricingValidationError) as exc_info:
            pricing_engine._validate_price(Decimal("20000000.00"), "test_price")

        assert "exceeds maximum" in str(exc_info.value)
        assert exc_info.value.context["field"] == "test_price"

    def test_validate_price_at_maximum(self, pricing_engine):
        """Test validation of price at maximum boundary."""
        pricing_engine._validate_price(Decimal("10000000.00"), "test_price")
        # Should not raise exception


# ============================================================================
# Unit Tests - Base Price Calculation
# ============================================================================


class TestBasePriceCalculation:
    """Test base price calculation."""

    def test_calculate_base_price_valid(self, pricing_engine, sample_vehicle):
        """Test calculating valid base price."""
        result = pricing_engine.calculate_base_price(sample_vehicle)

        assert result == Decimal("35000.00")

    def test_calculate_base_price_zero(self, pricing_engine):
        """Test calculating zero base price."""
        vehicle = Mock(spec=Vehicle)
        vehicle.id = uuid.uuid4()
        vehicle.base_price = Decimal("0.00")

        result = pricing_engine.calculate_base_price(vehicle)

        assert result == Decimal("0.00")

    def test_calculate_base_price_negative(self, pricing_engine):
        """Test calculating negative base price raises error."""
        vehicle = Mock(spec=Vehicle)
        vehicle.id = uuid.uuid4()
        vehicle.base_price = Decimal("-1000.00")

        with pytest.raises(PricingValidationError):
            pricing_engine.calculate_base_price(vehicle)

    def test_calculate_base_price_logs_calculation(self, pricing_engine, sample_vehicle):
        """Test that base price calculation is logged."""
        with patch("src.services.configuration.pricing_engine.logger") as mock_logger:
            pricing_engine.calculate_base_price(sample_vehicle)

            mock_logger.debug.assert_called_once()


# ============================================================================
# Unit Tests - Option Price Calculation
# ============================================================================


class TestOptionPriceCalculation:
    """Test option price calculation."""

    def test_calculate_option_price_valid(self, pricing_engine, sample_option):
        """Test calculating valid option price."""
        result = pricing_engine.calculate_option_price(sample_option)

        assert result == Decimal("1500.00")

    def test_calculate_option_price_zero(self, pricing_engine):
        """Test calculating zero option price."""
        option = Mock(spec=VehicleOption)
        option.id = uuid.uuid4()
        option.name = "Free Option"
        option.price = Decimal("0.00")

        result = pricing_engine.calculate_option_price(option)

        assert result == Decimal("0.00")

    def test_calculate_option_price_negative(self, pricing_engine):
        """Test calculating negative option price raises error."""
        option = Mock(spec=VehicleOption)
        option.id = uuid.uuid4()
        option.price = Decimal("-500.00")

        with pytest.raises(PricingValidationError):
            pricing_engine.calculate_option_price(option)

    def test_calculate_options_total_empty_list(self, pricing_engine):
        """Test calculating total for empty options list."""
        result = pricing_engine.calculate_options_total([])

        assert result == Decimal("0.00")

    def test_calculate_options_total_single_option(self, pricing_engine, sample_option):
        """Test calculating total for single option."""
        result = pricing_engine.calculate_options_total([sample_option])

        assert result == Decimal("1500.00")

    def test_calculate_options_total_multiple_options(
        self, pricing_engine, sample_options
    ):
        """Test calculating total for multiple options."""
        result = pricing_engine.calculate_options_total(sample_options)

        assert result == Decimal("4700.00")  # 1500 + 2000 + 1200

    def test_calculate_options_total_with_invalid_option(self, pricing_engine):
        """Test calculating total with invalid option raises error."""
        invalid_option = Mock(spec=VehicleOption)
        invalid_option.id = uuid.uuid4()
        invalid_option.price = Decimal("-100.00")

        with pytest.raises(PricingCalculationError):
            pricing_engine.calculate_options_total([invalid_option])


# ============================================================================
# Unit Tests - Package Discount Calculation
# ============================================================================


class TestPackageDiscountCalculation:
    """Test package discount calculation."""

    def test_calculate_package_discount_valid(self, pricing_engine, sample_package):
        """Test calculating valid package discount."""
        options_price = Decimal("5000.00")

        result = pricing_engine.calculate_package_discount(
            sample_package, options_price
        )

        assert result == Decimal("500.00")  # 10% of 5000

    def test_calculate_package_discount_zero_percentage(self, pricing_engine):
        """Test calculating discount with zero percentage."""
        package = Mock(spec=Package)
        package.id = uuid.uuid4()
        package.name = "No Discount Package"
        package.discount_percentage = Decimal("0.00")

        result = pricing_engine.calculate_package_discount(
            package, Decimal("5000.00")
        )

        assert result == Decimal("0.00")

    def test_calculate_package_discount_negative_percentage(self, pricing_engine):
        """Test calculating discount with negative percentage raises error."""
        package = Mock(spec=Package)
        package.id = uuid.uuid4()
        package.discount_percentage = Decimal("-10.00")

        with pytest.raises(PricingValidationError) as exc_info:
            pricing_engine.calculate_package_discount(package, Decimal("5000.00"))

        assert "cannot be negative" in str(exc_info.value)

    def test_calculate_package_discount_exceeds_maximum(self, pricing_engine):
        """Test calculating discount exceeding maximum raises error."""
        package = Mock(spec=Package)
        package.id = uuid.uuid4()
        package.discount_percentage = Decimal("150.00")

        with pytest.raises(PricingValidationError) as exc_info:
            pricing_engine.calculate_package_discount(package, Decimal("5000.00"))

        assert "exceeds maximum" in str(exc_info.value)

    def test_calculate_package_discount_at_maximum(self, pricing_engine):
        """Test calculating discount at maximum boundary."""
        package = Mock(spec=Package)
        package.id = uuid.uuid4()
        package.name = "Full Discount"
        package.discount_percentage = Decimal("100.00")

        result = pricing_engine.calculate_package_discount(
            package, Decimal("5000.00")
        )

        assert result == Decimal("5000.00")


# ============================================================================
# Unit Tests - Package Price Calculation
# ============================================================================


class TestPackagePriceCalculation:
    """Test package price calculation."""

    def test_calculate_package_price_valid(
        self, pricing_engine, sample_package, sample_options
    ):
        """Test calculating valid package price."""
        included_options = sample_options[:2]  # 1500 + 2000 = 3500

        result = pricing_engine.calculate_package_price(
            sample_package, included_options
        )

        # 3500 - (3500 * 0.10) = 3150
        assert result == Decimal("3150.00")

    def test_calculate_package_price_no_discount(self, pricing_engine, sample_options):
        """Test calculating package price with no discount."""
        package = Mock(spec=Package)
        package.id = uuid.uuid4()
        package.name = "No Discount Package"
        package.discount_percentage = Decimal("0.00")

        result = pricing_engine.calculate_package_price(package, sample_options[:2])

        assert result == Decimal("3500.00")

    def test_calculate_package_price_empty_options(self, pricing_engine, sample_package):
        """Test calculating package price with no options."""
        result = pricing_engine.calculate_package_price(sample_package, [])

        assert result == Decimal("0.00")

    def test_calculate_package_price_calculation_error(self, pricing_engine):
        """Test package price calculation error handling."""
        package = Mock(spec=Package)
        package.id = uuid.uuid4()
        package.discount_percentage = Decimal("-10.00")  # Invalid

        invalid_option = Mock(spec=VehicleOption)
        invalid_option.price = Decimal("1000.00")

        with pytest.raises(PricingCalculationError):
            pricing_engine.calculate_package_price(package, [invalid_option])


# ============================================================================
# Unit Tests - Tax Calculation
# ============================================================================


class TestTaxCalculation:
    """Test tax calculation."""

    def test_get_tax_rate_default(self, pricing_engine):
        """Test getting default tax rate."""
        rate = pricing_engine.get_tax_rate()

        assert rate == Decimal("0.08")

    def test_get_tax_rate_california(self, pricing_engine):
        """Test getting California tax rate."""
        rate = pricing_engine.get_tax_rate("CA")

        assert rate == Decimal("0.0725")

    def test_get_tax_rate_new_york(self, pricing_engine):
        """Test getting New York tax rate."""
        rate = pricing_engine.get_tax_rate("NY")

        assert rate == Decimal("0.08875")

    def test_get_tax_rate_texas(self, pricing_engine):
        """Test getting Texas tax rate."""
        rate = pricing_engine.get_tax_rate("TX")

        assert rate == Decimal("0.0625")

    def test_get_tax_rate_florida(self, pricing_engine):
        """Test getting Florida tax rate."""
        rate = pricing_engine.get_tax_rate("FL")

        assert rate == Decimal("0.06")

    def test_get_tax_rate_unknown_region(self, pricing_engine):
        """Test getting tax rate for unknown region returns default."""
        rate = pricing_engine.get_tax_rate("XX")

        assert rate == Decimal("0.08")

    def test_calculate_tax_default_region(self, pricing_engine):
        """Test calculating tax with default region."""
        subtotal = Decimal("40000.00")

        result = pricing_engine.calculate_tax(subtotal)

        assert result == Decimal("3200.00")  # 40000 * 0.08

    def test_calculate_tax_california(self, pricing_engine):
        """Test calculating tax for California."""
        subtotal = Decimal("40000.00")

        result = pricing_engine.calculate_tax(subtotal, "CA")

        assert result == Decimal("2900.00")  # 40000 * 0.0725

    def test_calculate_tax_zero_subtotal(self, pricing_engine):
        """Test calculating tax on zero subtotal."""
        result = pricing_engine.calculate_tax(Decimal("0.00"))

        assert result == Decimal("0.00")

    def test_calculate_tax_negative_subtotal(self, pricing_engine):
        """Test calculating tax on negative subtotal raises error."""
        with pytest.raises(PricingValidationError):
            pricing_engine.calculate_tax(Decimal("-1000.00"))


# ============================================================================
# Unit Tests - Destination Charge Calculation
# ============================================================================


class TestDestinationChargeCalculation:
    """Test destination charge calculation."""

    def test_calculate_destination_charge_valid(
        self, pricing_engine, sample_vehicle
    ):
        """Test calculating valid destination charge."""
        result = pricing_engine.calculate_destination_charge(sample_vehicle)

        assert result == Decimal("1200.00")

    def test_calculate_destination_charge_zero(self, pricing_engine):
        """Test calculating zero destination charge."""
        vehicle = Mock(spec=Vehicle)
        vehicle.id = uuid.uuid4()
        vehicle.destination_charge = Decimal("0.00")

        result = pricing_engine.calculate_destination_charge(vehicle)

        assert result == Decimal("0.00")

    def test_calculate_destination_charge_negative(self, pricing_engine):
        """Test calculating negative destination charge raises error."""
        vehicle = Mock(spec=Vehicle)
        vehicle.id = uuid.uuid4()
        vehicle.destination_charge = Decimal("-500.00")

        with pytest.raises(PricingValidationError):
            pricing_engine.calculate_destination_charge(vehicle)


# ============================================================================
# Integration Tests - Total Price Calculation
# ============================================================================


class TestTotalPriceCalculation:
    """Test total price calculation."""

    @pytest.mark.asyncio
    async def test_calculate_total_price_base_only(
        self, pricing_engine, sample_vehicle
    ):
        """Test calculating total price with base price only."""
        result = await pricing_engine.calculate_total_price(
            sample_vehicle,
            include_tax=False,
            include_destination=False,
        )

        assert result["base_price"] == 35000.0
        assert result["options_price"] == 0.0
        assert result["packages_price"] == 0.0
        assert result["subtotal"] == 35000.0
        assert result["destination_charge"] == 0.0
        assert result["tax_amount"] == 0.0
        assert result["total"] == 35000.0

    @pytest.mark.asyncio
    async def test_calculate_total_price_with_options(
        self, pricing_engine, sample_vehicle, sample_options
    ):
        """Test calculating total price with options."""
        result = await pricing_engine.calculate_total_price(
            sample_vehicle,
            options=sample_options,
            include_tax=False,
            include_destination=False,
        )

        assert result["base_price"] == 35000.0
        assert result["options_price"] == 4700.0  # 1500 + 2000 + 1200
        assert result["subtotal"] == 39700.0
        assert result["total"] == 39700.0

    @pytest.mark.asyncio
    async def test_calculate_total_price_with_package(
        self, pricing_engine, sample_vehicle, sample_package_with_options
    ):
        """Test calculating total price with package."""
        result = await pricing_engine.calculate_total_price(
            sample_vehicle,
            packages=[sample_package_with_options],
            include_tax=False,
            include_destination=False,
        )

        assert result["base_price"] == 35000.0
        assert result["packages_price"] == 3150.0  # (1500 + 2000) * 0.9
        assert result["packages_discount"] == 350.0  # 3500 * 0.1
        assert result["subtotal"] == 38150.0
        assert result["total"] == 38150.0

    @pytest.mark.asyncio
    async def test_calculate_total_price_with_destination(
        self, pricing_engine, sample_vehicle
    ):
        """Test calculating total price with destination charge."""
        result = await pricing_engine.calculate_total_price(
            sample_vehicle,
            include_tax=False,
            include_destination=True,
        )

        assert result["destination_charge"] == 1200.0
        assert result["total"] == 36200.0  # 35000 + 1200

    @pytest.mark.asyncio
    async def test_calculate_total_price_with_tax(
        self, pricing_engine, sample_vehicle
    ):
        """Test calculating total price with tax."""
        result = await pricing_engine.calculate_total_price(
            sample_vehicle,
            include_tax=True,
            include_destination=False,
        )

        assert result["tax_amount"] == 2800.0  # 35000 * 0.08
        assert result["tax_rate"] == 0.08
        assert result["total"] == 37800.0  # 35000 + 2800

    @pytest.mark.asyncio
    async def test_calculate_total_price_with_regional_tax(
        self, pricing_engine, sample_vehicle
    ):
        """Test calculating total price with regional tax."""
        result = await pricing_engine.calculate_total_price(
            sample_vehicle,
            region="CA",
            include_tax=True,
            include_destination=False,
        )

        assert result["tax_amount"] == 2537.5  # 35000 * 0.0725
        assert result["tax_rate"] == 0.0725
        assert result["region"] == "CA"

    @pytest.mark.asyncio
    async def test_calculate_total_price_complete(
        self,
        pricing_engine,
        sample_vehicle,
        sample_options,
        sample_package_with_options,
    ):
        """Test calculating complete total price with all components."""
        result = await pricing_engine.calculate_total_price(
            sample_vehicle,
            options=sample_options[2:],  # Just sunroof
            packages=[sample_package_with_options],
            region="NY",
            include_tax=True,
            include_destination=True,
        )

        # Base: 35000
        # Options: 1200 (sunroof)
        # Package: 3150 (1500 + 2000 with 10% discount)
        # Subtotal: 39350
        # Destination: 1200
        # Taxable: 40550
        # Tax (NY 8.875%): 3598.8125
        # Total: 44148.8125

        assert result["base_price"] == 35000.0
        assert result["options_price"] == 1200.0
        assert result["packages_price"] == 3150.0
        assert result["subtotal"] == 39350.0
        assert result["destination_charge"] == 1200.0
        assert result["tax_amount"] == 3598.8125
        assert result["total"] == 44148.8125
        assert result["region"] == "NY"

    @pytest.mark.asyncio
    async def test_calculate_total_price_breakdown(
        self, pricing_engine, sample_vehicle, sample_options
    ):
        """Test that price breakdown is included in result."""
        result = await pricing_engine.calculate_total_price(
            sample_vehicle,
            options=sample_options,
            include_tax=True,
            include_destination=True,
        )

        assert "breakdown" in result
        assert result["breakdown"]["base"] == 35000.0
        assert result["breakdown"]["options"] == 4700.0
        assert result["breakdown"]["packages"] == 0.0
        assert result["breakdown"]["destination"] == 1200.0
        assert result["breakdown"]["tax"] > 0

    @pytest.mark.asyncio
    async def test_calculate_total_price_metadata(
        self, pricing_engine, sample_vehicle
    ):
        """Test that metadata is included in result."""
        result = await pricing_engine.calculate_total_price(sample_vehicle)

        assert "vehicle_id" in result
        assert "calculated_at" in result
        assert "region" in result
        assert result["vehicle_id"] == str(sample_vehicle.id)

    @pytest.mark.asyncio
    async def test_calculate_total_price_validation_error(self, pricing_engine):
        """Test total price calculation with validation error."""
        vehicle = Mock(spec=Vehicle)
        vehicle.id = uuid.uuid4()
        vehicle.base_price = Decimal("-1000.00")  # Invalid

        with pytest.raises(PricingCalculationError):
            await pricing_engine.calculate_total_price(vehicle)

    @pytest.mark.asyncio
    async def test_calculate_total_price_unexpected_error(self, pricing_engine):
        """Test total price calculation with unexpected error."""
        vehicle = Mock(spec=Vehicle)
        vehicle.id = uuid.uuid4()
        vehicle.base_price = Mock(side_effect=Exception("Unexpected error"))

        with pytest.raises(PricingCalculationError):
            await pricing_engine.calculate_total_price(vehicle)


# ============================================================================
# Integration Tests - Caching Behavior
# ============================================================================


class TestCachingBehavior:
    """Test caching behavior."""

    @pytest.mark.asyncio
    async def test_calculate_total_price_caches_result(
        self, pricing_engine, sample_vehicle, mock_redis_client
    ):
        """Test that total price calculation caches result."""
        await pricing_engine.calculate_total_price(
            sample_vehicle,
            include_tax=False,
            include_destination=False,
        )

        mock_redis_client.set_json.assert_called_once()
        call_args = mock_redis_client.set_json.call_args
        assert call_args[1]["ex"] == 3600

    @pytest.mark.asyncio
    async def test_calculate_total_price_uses_cache(
        self, pricing_engine, sample_vehicle, mock_redis_client
    ):
        """Test that total price calculation uses cached result."""
        cached_result = {
            "vehicle_id": str(sample_vehicle.id),
            "total": 40000.0,
            "base_price": 35000.0,
        }
        mock_redis_client.get_json.return_value = cached_result

        result = await pricing_engine.calculate_total_price(sample_vehicle)

        assert result == cached_result
        mock_redis_client.get_json.assert_called_once()
        mock_redis_client.set_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_calculate_total_price_cache_key_includes_params(
        self, pricing_engine, sample_vehicle, mock_redis_client, sample_options
    ):
        """Test that cache key includes all parameters."""
        await pricing_engine.calculate_total_price(
            sample_vehicle,
            options=sample_options,
            region="CA",
            include_tax=True,
            include_destination=True,
        )

        cache_key = mock_redis_client.set_json.call_args[0][0]
        assert str(sample_vehicle.id) in cache_key
        assert "CA" in cache_key
        assert "True" in cache_key

    @pytest.mark.asyncio
    async def test_calculate_total_price_no_cache_when_disabled(
        self, pricing_engine_no_cache, sample_vehicle
    ):
        """Test that caching is skipped when disabled."""
        result = await pricing_engine_no_cache.calculate_total_price(sample_vehicle)

        assert "total" in result
        # No cache operations should occur


# ============================================================================
# Integration Tests - Cache Invalidation
# ============================================================================


class TestCacheInvalidation:
    """Test cache invalidation."""

    @pytest.mark.asyncio
    async def test_invalidate_cache_specific_vehicle(
        self, pricing_engine, mock_redis_client
    ):
        """Test invalidating cache for specific vehicle."""
        vehicle_id = uuid.uuid4()
        mock_redis_client.delete_pattern.return_value = 5

        count = await pricing_engine.invalidate_cache(vehicle_id)

        assert count == 5
        mock_redis_client.delete_pattern.assert_called_once()
        pattern = mock_redis_client.delete_pattern.call_args[0][0]
        assert str(vehicle_id) in pattern

    @pytest.mark.asyncio
    async def test_invalidate_cache_all_vehicles(
        self, pricing_engine, mock_redis_client
    ):
        """Test invalidating cache for all vehicles."""
        mock_redis_client.delete_pattern.return_value = 100

        count = await pricing_engine.invalidate_cache()

        assert count == 100
        mock_redis_client.delete_pattern.assert_called_once()
        pattern = mock_redis_client.delete_pattern.call_args[0][0]
        assert "*" in pattern

    @pytest.mark.asyncio
    async def test_invalidate_cache_error_handling(
        self, pricing_engine, mock_redis_client
    ):
        """Test cache invalidation error handling."""
        mock_redis_client.delete_pattern.side_effect = Exception("Redis error")

        with patch("src.services.configuration.pricing_engine.logger") as mock_logger:
            count = await pricing_engine.invalidate_cache()

            assert count == 0
            mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalidate_cache_when_disabled(self, pricing_engine_no_cache):
        """Test cache invalidation when caching is disabled."""
        count = await pricing_engine_no_cache.invalidate_cache()

        assert count == 0


# ============================================================================
# Edge Cases and Boundary Tests
# ============================================================================


class TestEdgeCasesAndBoundaries:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_calculate_total_price_maximum_values(self, pricing_engine):
        """Test calculation with maximum allowed values."""
        vehicle = Mock(spec=Vehicle)
        vehicle.id = uuid.uuid4()
        vehicle.base_price = Decimal("9999999.00")
        vehicle.destination_charge = Decimal("1.00")

        result = await pricing_engine.calculate_total_price(
            vehicle,
            include_tax=False,
            include_destination=True,
        )

        assert result["total"] == 10000000.0

    @pytest.mark.asyncio
    async def test_calculate_total_price_minimum_values(self, pricing_engine):
        """Test calculation with minimum allowed values."""
        vehicle = Mock(spec=Vehicle)
        vehicle.id = uuid.uuid4()
        vehicle.base_price = Decimal("0.00")
        vehicle.destination_charge = Decimal("0.00")

        result = await pricing_engine.calculate_total_price(vehicle)

        assert result["total"] == 0.0

    def test_calculate_package_discount_precision(self, pricing_engine):
        """Test package discount calculation precision."""
        package = Mock(spec=Package)
        package.id = uuid.uuid4()
        package.name = "Test Package"
        package.discount_percentage = Decimal("15.75")

        result = pricing_engine.calculate_package_discount(
            package, Decimal("1234.56")
        )

        # 1234.56 * 0.1575 = 194.44320
        assert result == Decimal("194.44320")

    def test_calculate_tax_precision(self, pricing_engine):
        """Test tax calculation precision."""
        result = pricing_engine.calculate_tax(Decimal("12345.67"), "NY")

        # 12345.67 * 0.08875 = 1095.678
        assert result == Decimal("1095.678")

    @pytest.mark.asyncio
    async def test_calculate_total_price_many_options(self, pricing_engine):
        """Test calculation with many options."""
        vehicle = Mock(spec=Vehicle)
        vehicle.id = uuid.uuid4()
        vehicle.base_price = Decimal("30000.00")
        vehicle.destination_charge = Decimal("1000.00")

        # Create 50 options
        options = []
        for i in range(50):
            option = Mock(spec=VehicleOption)
            option.id = uuid.uuid4()
            option.name = f"Option {i}"
            option.price = Decimal("100.00")
            options.append(option)

        result = await pricing_engine.calculate_total_price(
            vehicle,
            options=options,
            include_tax=False,
            include_destination=False,
        )

        assert result["options_price"] == 5000.0  # 50 * 100
        assert result["total"] == 35000.0

    @pytest.mark.asyncio
    async def test_calculate_total_price_multiple_packages(self, pricing_engine):
        """Test calculation with multiple packages."""
        vehicle = Mock(spec=Vehicle)
        vehicle.id = uuid.uuid4()
        vehicle.base_price = Decimal("30000.00")
        vehicle.destination_charge = Decimal("1000.00")

        # Create two packages
        packages = []
        for i in range(2):
            package = Mock(spec=Package)
            package.id = uuid.uuid4()
            package.name = f"Package {i}"
            package.discount_percentage = Decimal("10.00")

            options = []
            for j in range(2):
                option = Mock(spec=VehicleOption)
                option.id = uuid.uuid4()
                option.name = f"Option {i}-{j}"
                option.price = Decimal("1000.00")
                options.append(option)

            packages.append((package, options))

        result = await pricing_engine.calculate_total_price(
            vehicle,
            packages=packages,
            include_tax=False,
            include_destination=False,
        )

        # Each package: 2000 - 200 = 1800
        # Total packages: 3600
        assert result["packages_price"] == 3600.0
        assert result["packages_discount"] == 400.0


# ============================================================================
# Performance Tests
# ============================================================================


class TestPerformance:
    """Test performance characteristics."""

    @pytest.mark.asyncio
    async def test_calculate_total_price_performance(
        self, pricing_engine, sample_vehicle, sample_options
    ):
        """Test total price calculation performance."""
        import time

        start_time = time.time()

        for _ in range(100):
            await pricing_engine.calculate_total_price(
                sample_vehicle,
                options=sample_options,
                include_tax=True,
                include_destination=True,
            )

        elapsed_time = time.time() - start_time

        # Should complete 100 calculations in under 1 second
        assert elapsed_time < 1.0

    @pytest.mark.asyncio
    async def test_cache_improves_performance(
        self, pricing_engine, sample_vehicle, mock_redis_client
    ):
        """Test that caching improves performance."""
        import time

        # First call (no cache)
        start_time = time.time()
        await pricing_engine.calculate_total_price(sample_vehicle)
        first_call_time = time.time() - start_time

        # Setup cache hit
        cached_result = {
            "vehicle_id": str(sample_vehicle.id),
            "total": 40000.0,
        }
        mock_redis_client.get_json.return_value = cached_result

        # Second call (with cache)
        start_time = time.time()
        await pricing_engine.calculate_total_price(sample_vehicle)
        cached_call_time = time.time() - start_time

        # Cached call should be faster (or at least not slower)
        assert cached_call_time <= first_call_time * 1.5


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Test error handling."""

    def test_pricing_error_with_context(self):
        """Test PricingError stores context."""
        error = PricingError("Test error", field="test", value=123)

        assert str(error) == "Test error"
        assert error.context["field"] == "test"
        assert error.context["value"] == 123

    def test_pricing_validation_error_inheritance(self):
        """Test PricingValidationError inherits from PricingError."""
        error = PricingValidationError("Validation failed", field="price")

        assert isinstance(error, PricingError)
        assert error.context["field"] == "price"

    def test_pricing_calculation_error_inheritance(self):
        """Test PricingCalculationError inherits from PricingError."""
        error = PricingCalculationError("Calculation failed", vehicle_id="123")

        assert isinstance(error, PricingError)
        assert error.context["vehicle_id"] == "123"

    @pytest.mark.asyncio
    async def test_calculate_total_price_logs_errors(self, pricing_engine):
        """Test that calculation errors are logged."""
        vehicle = Mock(spec=Vehicle)
        vehicle.id = uuid.uuid4()
        vehicle.base_price = Mock(side_effect=Exception("Test error"))

        with patch("src.services.configuration.pricing_engine.logger") as mock_logger:
            with pytest.raises(PricingCalculationError):
                await pricing_engine.calculate_total_price(vehicle)

            mock_logger.error.assert_called_once()


# ============================================================================
# Regional Pricing Tests
# ============================================================================


class TestRegionalPricing:
    """Test regional pricing variations."""

    @pytest.mark.parametrize(
        "region,expected_rate",
        [
            ("CA", Decimal("0.0725")),
            ("NY", Decimal("0.08875")),
            ("TX", Decimal("0.0625")),
            ("FL", Decimal("0.06")),
            ("US", Decimal("0.08")),
            ("XX", Decimal("0.08")),  # Unknown region
        ],
    )
    def test_regional_tax_rates(self, pricing_engine, region, expected_rate):
        """Test tax rates for different regions."""
        rate = pricing_engine.get_tax_rate(region)

        assert rate == expected_rate

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "region,expected_tax",
        [
            ("CA", 2537.5),  # 35000 * 0.0725
            ("NY", 3106.25),  # 35000 * 0.08875
            ("TX", 2187.5),  # 35000 * 0.0625
            ("FL", 2100.0),  # 35000 * 0.06
        ],
    )
    async def test_regional_total_price(
        self, pricing_engine, sample_vehicle, region, expected_tax
    ):
        """Test total price calculation for different regions."""
        result = await pricing_engine.calculate_total_price(
            sample_vehicle,
            region=region,
            include_tax=True,
            include_destination=False,
        )

        assert result["region"] == region
        assert result["tax_amount"] == expected_tax
        assert result["total"] == 35000.0 + expected_tax


# ============================================================================
# Logging Tests
# ============================================================================


class TestLogging:
    """Test logging behavior."""

    def test_initialization_logs_configuration(self):
        """Test that initialization logs configuration."""
        with patch("src.services.configuration.pricing_engine.logger") as mock_logger:
            PricingEngine(enable_caching=True, default_region="CA")

            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert call_args[1]["enable_caching"] is True
            assert call_args[1]["default_region"] == "CA"

    def test_calculate_base_price_logs_debug(self, pricing_engine, sample_vehicle):
        """Test that base price calculation logs debug info."""
        with patch("src.services.configuration.pricing_engine.logger") as mock_logger:
            pricing_engine.calculate_base_price(sample_vehicle)

            mock_logger.debug.assert_called_once()
            call_args = mock_logger.debug.call_args
            assert "Calculated base price" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_calculate_total_price_logs_info(
        self, pricing_engine, sample_vehicle
    ):
        """Test that total price calculation logs info."""
        with patch("src.services.configuration.pricing_engine.logger") as mock_logger:
            await pricing_engine.calculate_total_price(sample_vehicle)

            # Should have info log for final calculation
            info_calls = [
                call for call in mock_logger.info.call_args_list
                if "Calculated total price" in str(call)
            ]
            assert len(info_calls) > 0


# ============================================================================
# Constants and Configuration Tests
# ============================================================================


class TestConstantsAndConfiguration:
    """Test constants and configuration values."""

    def test_cache_ttl_constant(self):
        """Test cache TTL constant value."""
        assert PricingEngine.CACHE_TTL_SECONDS == 3600

    def test_cache_key_prefix_constant(self):
        """Test cache key prefix constant."""
        assert PricingEngine.CACHE_KEY_PREFIX == "pricing"

    def test_default_tax_rate_constant(self):
        """Test default tax rate constant."""
        assert PricingEngine.DEFAULT_TAX_RATE == Decimal("0.08")

    def test_regional_tax_rates_constant(self):
        """Test regional tax rates constant."""
        rates = PricingEngine.REGIONAL_TAX_RATES

        assert "CA" in rates
        assert "NY" in rates
        assert "TX" in rates
        assert "FL" in rates
        assert len(rates) == 4

    def test_price_limits_constants(self):
        """Test price limit constants."""
        assert PricingEngine.MIN_PRICE == Decimal("0.00")
        assert PricingEngine.MAX_PRICE == Decimal("10000000.00")
        assert PricingEngine.MAX_DISCOUNT_PERCENTAGE == Decimal("100.00")